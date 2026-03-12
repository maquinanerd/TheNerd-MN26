# app/ai_processor.py
import os
import json
import logging
import re
from urllib.parse import urlparse
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, ClassVar

from .config import (
    AI_API_KEYS,
    PROMPT_FILE_PATH,
)
from .exceptions import AIProcessorError
from .ai_client_gemini import AIClient
from .token_tracker import log_tokens
from .token_guarantee import log_guaranteed, TokenGuarantee  # Double-layer token protection

# Get rate limit configs from environment or use defaults from the user's plan
AI_MIN_INTERVAL_S = float(os.getenv('AI_MIN_INTERVAL_S', 6))
BACKOFF_BASE_S = int(os.getenv('BACKOFF_BASE_S', 20))
BACKOFF_MAX_S = int(os.getenv('BACKOFF_MAX_S', 300))

logger = logging.getLogger(__name__)

AI_SYSTEM_RULES = """
[REGRAS OBRIGATÓRIAS — CUMPRIR 100%]

**1. OUTPUT OBRIGATÓRIO: JSON VÁLIDO**
DEVOLVE EXCLUSIVAMENTE JSON VÁLIDO.
ESTRUTURA FIXA DO TOPO:
{
  "resultados": [ /* 1 ou N objetos, um por artigo, na mesma ordem da entrada */ ]
}
NUNCA devolva texto fora do JSON. NUNCA inclua comentários. NUNCA mude os nomes de chaves.
Cada artigo DEVE conter: "titulo_final", "conteudo_final", "meta_description", "focus_keyphrase", "related_keyphrases", "slug", "categorias", "tags_sugeridas", "yoast_meta".

**2. VALIDAÇÃO DE TÍTULO (titulo_final)**
✅ OBRIGATÓRIO: Cada título DEVE passar no CHECKLIST:
  - Entre 55–65 caracteres
  - Começa com ENTIDADE (ator/franquia/plataforma)
  - Verbo NO PRESENTE (não infinitivo)
  - Afirmação direta, SEM pergunta
  - Concordância e regência perfeitas
  - Plataforma NO FIM se relevante
  - SEM sensacionalismo (bomba, explode, nerfado, morto, surpreendente)
  - Maiúsculas APENAS em nomes próprios
  - SEM múltiplos dois-pontos ou pontuação excessiva
SE ALGUM CRITÉRIO FALHAR, REFAZER O TÍTULO COMPLETAMENTE.

**3. VALIDAÇÃO DE CONTEÚDO (conteudo_final)**
  - SEM menção a concorrentes (Omelete, IGN, Jovem Nerd, AdoroCinema)
  - SEM hashtags (#)
  - SEM frases fracas ("veja", "entenda", "clique aqui", "saiba mais")
  - SEM termos em inglês (exceto nomes próprios internacionais)
  - SEM CTAs ou calls-to-action ("Thank you for reading", "Subscribe", etc.)
  - Links internos COM https:// completo: <a href="https://{domain}/tag/{tag}">Texto</a>
  - Parágrafos com máx 3–4 frases
  - MÍNIMO 3 subtítulos <h2>
  - Palavra-chave no primeiro parágrafo
  - Imagens em <figure> com <figcaption>

**4. META DESCRIPTION (meta_description)**
  - 140–155 caracteres
  - Contém palavra-chave principal
  - SEM call-to-action

**5. 🚨 REMOVER ABSOLUTAMENTE (CTAs/JUNK/GARBAGE)**
É PROIBIDO incluir no conteudo_final:
- "Thank you for reading" / "Thanks for reading" / "Thanks for visiting"
- "Don't forget to subscribe" / "Please subscribe" / "Subscribe now"
- "Click here" / "Read more" / "Sign up"
- "Stay tuned" / "Follow us" / "Keep up to date"
- Newsletter signup / Author boxes / Promotional content
SE ESSES TEXTOS APARECEREM NA FONTE, REMOVA-OS COMPLETAMENTE.

**6. LIMPEZA OBRIGATÓRIA**
NÃO incluir e REMOVER de forma explícita:
- Qualquer texto de interface/comentários dos sites (ex.: "Your comment has not been saved").
- Caixas/infobox de ficha técnica com rótulos como: "Release Date", "Runtime", "Director", "Writers", "Producers", "Cast".
- Elementos de comentários, "trending", "related", "read more", "newsletter", "author box", "ratings/review box".

[MODO PROCESSAMENTO EM LOTE]
- Recebe múltiplos artigos para processar
- Retorna um objeto JSON com um array "resultados" contendo a saída de cada artigo
- Cada resultado segue o mesmo formato de saída de artigo único
- Preserva a ordem dos artigos na resposta

Somente produzir o conteúdo jornalístico reescrito do artigo principal.
Se algum desses itens aparecer no texto de origem, exclua-os do resultado.
"""

class AIProcessor:
    _prompt_template: ClassVar[Optional[str]] = None
    _ai_client: ClassVar[Optional[AIClient]] = None

    def __init__(self):
        if not AI_API_KEYS:
            raise AIProcessorError("No GEMINI_ API keys found in the environment.")
        
        # Initialize the AI client singleton
        if AIProcessor._ai_client is None:
            logger.info(f"Initializing AIClient with {len(AI_API_KEYS)} keys.")
            AIProcessor._ai_client = AIClient(
                keys=AI_API_KEYS,
                min_interval_s=AI_MIN_INTERVAL_S,
                backoff_base=BACKOFF_BASE_S,
                backoff_max=BACKOFF_MAX_S,
            )

    @classmethod
    def _load_prompt_template(cls) -> str:
        if cls._prompt_template is None:
            try:
                prompt_path = Path(PROMPT_FILE_PATH)
                if not prompt_path.exists():
                    raise FileNotFoundError(f"Prompt file not found at {PROMPT_FILE_PATH}")
                
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    base_template = f.read()
                cls._prompt_template = f"{AI_SYSTEM_RULES}\n\n{base_template}"
            except FileNotFoundError as e:
                logger.critical(e)
                raise AIProcessorError("Prompt template file not found.") from e
        return cls._prompt_template

    @staticmethod
    def _safe_format_prompt(template: str, fields: Dict[str, Any]) -> str:
        class _SafeDict(dict):
            def __missing__(self, key: str) -> str:
                return ""
        
        s = template.replace('{', '{{').replace('}', '}}')
        for key in fields:
            s = s.replace('{{' + key + '}}', '{' + key + '}')
        
        return s.format_map(_SafeDict(fields))

    def rewrite_batch(
        self,
        batch_data: List[Dict[str, Any]]
    ) -> List[Tuple[Optional[Dict[str, Any]], Optional[str]]]:
        """Process multiple articles in a single batch."""
        prompt_template = self._load_prompt_template()
        
        batch_fields = []
        for data in batch_data:
            title = data.get('title')
            content_html = data.get('content_html')
            source_url = data.get('source_url')
            
            fonte = data.get("source_name", "")
            if not fonte and source_url:
                try:
                    fonte = urlparse(source_url).netloc.replace("www.", "")
                except Exception:
                    fonte = ""

            fields = {
                "titulo_original": title or "",
                "url_original": source_url or "",
                "content": content_html or "",
                "domain": data.get("domain", ""),
                "fonte_nome": fonte,
                "categoria": data.get("category", ""),
                "schema_original": json.dumps(data.get("schema_original"), indent=2, ensure_ascii=False) if data.get("schema_original") else "Nenhum",
                "videos_list": "\n".join([v.get("embed_url", "") for v in data.get("videos", []) if isinstance(v, dict) and v.get("embed_url")]) or "Nenhum",
                "imagens_list": "\n".join(data.get("images", [])) or "Nenhuma",
            }
            batch_fields.append(fields)

        batch_prompt = "Processe os seguintes artigos em lote:\n\n"
        for i, fields in enumerate(batch_fields, 1):
            batch_prompt += f"=== ARTIGO {i} ===\n"
            batch_prompt += self._safe_format_prompt(prompt_template, fields)
            batch_prompt += "\n\n"

        try:
            logger.info(f"Sending batch of {len(batch_data)} articles to AI.")

            # Be more deterministic for structured output
            generation_config = {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "top_p": 0.9,
                "max_output_tokens": 32000,  # 32K máximo para garantir resposta completa (batch size 1)
            }
            response_data = self._ai_client.generate_text(batch_prompt, generation_config=generation_config)
            
            # Desempacotar resposta: (texto, tokens_info)
            if isinstance(response_data, tuple):
                response_text, tokens_info = response_data
            else:
                # Fallback para compatibilidade se ainda retornar apenas string
                response_text = response_data
                tokens_info = {}
            
            # Log tokens - OBRIGATÓRIO (sempre registrar)
            prompt_tokens = tokens_info.get('prompt_tokens', 0) if tokens_info else 0
            completion_tokens = tokens_info.get('completion_tokens', 0) if tokens_info else 0
            
            for idx, batch_item in enumerate(batch_data):
                source_url = batch_item.get('source_url', 'N/A')
                article_title = batch_item.get('title', 'N/A')
                
                success = log_tokens(
                    prompt_tokens=int(prompt_tokens),
                    completion_tokens=int(completion_tokens),
                    api_type="gemini",
                    model=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite"),
                    api_key_suffix=used_key if 'used_key' in locals() else "unknown",
                    metadata={
                        "batch_size": len(batch_data),
                        "operation": "batch_rewrite",
                        "batch_index": idx,
                        "total_tokens": int(prompt_tokens + completion_tokens)
                    },
                    source_url=source_url,
                    article_title=article_title,
                    success=True
                )
                if not success:
                    logger.error(f"❌ ERRO: Falha ao registrar tokens para {article_title}")
            
            # Log qual chave foi usada para processar este batch
            used_key = self._ai_client.get_last_used_key()
            logger.info(f"BATCH OK: Processado com chave de API: {used_key}")

            parsed_data = self._parse_batch_response(response_text, len(batch_data))
            if parsed_data is None:  # Batch parsing failed
                logger.error(f"Batch JSON parse failed for {len(batch_data)} articles. NOT falling back to per-article to save quota.")
                logger.debug(f"Failed batch response (first 500 chars): {response_text[:500]}")
                # Return error for all items - they'll be retried in next cycle
                error_msg = "Batch JSON parsing failed (insufficient quota budget to retry individually)"
                return [(None, error_msg)] * len(batch_data)

            logger.info(f"Successfully processed batch of {len(batch_data)} articles with API key {used_key}.")
            return [(result, None) if result else (None, "Article data missing or invalid in batch response") 
                   for result in parsed_data]

        except RuntimeError as e:
            logger.critical(f"AI batch processing failed after all retries: {e}")
            return [(None, str(e))] * len(batch_data)
        except Exception as e:
            logger.critical(f"An unexpected error occurred during AI batch processing: {e}", exc_info=True)
            return [(None, str(e))] * len(batch_data)

    def rewrite_content(
        self,
        title: Optional[str] = None,
        content_html: Optional[str] = None,
        source_url: Optional[str] = None,
        **kwargs: Any,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        
        prompt_template = self._load_prompt_template()

        fonte = kwargs.get("source_name", "")
        if not fonte and source_url:
            try:
                fonte = urlparse(source_url).netloc.replace("www.", "")
            except Exception:
                fonte = ""

        fields = {
            "titulo_original": title or "",
            "url_original": source_url or "",
            "content": content_html or "",
            "domain": kwargs.get("domain", ""),
            "fonte_nome": fonte,
            "categoria": kwargs.get("category", ""),
            "schema_original": json.dumps(kwargs.get("schema_original"), indent=2, ensure_ascii=False) if kwargs.get("schema_original") else "Nenhum",
            "videos_list": "\n".join([v.get("embed_url", "") for v in kwargs.get("videos", []) if isinstance(v, dict) and v.get("embed_url")]) or "Nenhum",
            "imagens_list": "\n".join(kwargs.get("images", [])) or "Nenhuma",
        }
        prompt = self._safe_format_prompt(prompt_template, fields)

        try:
            logger.info(f"Sending content from {source_url} to AI.")
            
            generation_config = {
                "response_mime_type": "application/json",
                "max_output_tokens": 32000,  # 32K máximo para garantir resposta completa
            }
            response_data = self._ai_client.generate_text(prompt, generation_config=generation_config)
            
            # Desempacotar resposta: (texto, tokens_info)
            if isinstance(response_data, tuple):
                response_text, tokens_info = response_data
            else:
                # Fallback para compatibilidade
                response_text = response_data
                tokens_info = {}
            
            # Log tokens - OBRIGATÓRIO (sempre registrar)
            prompt_tokens = tokens_info.get('prompt_tokens', 0) if tokens_info else 0
            completion_tokens = tokens_info.get('completion_tokens', 0) if tokens_info else 0
            
            success = log_tokens(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                api_type="gemini",
                model=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite"),
                api_key_suffix=self._ai_client.get_last_used_key(),
                metadata={
                    "operation": "single_rewrite",
                    "source_url": source_url,
                    "total_tokens": int(prompt_tokens + completion_tokens)
                },
                source_url=source_url,
                article_title=title,
                success=True
            )
            if not success:
                logger.error(f"❌ ERRO: Falha ao registrar tokens para {title}")
            
            parsed_data = self._parse_response(response_text)

            if not parsed_data:
                return None, "Failed to parse or validate AI response."

            if "erro" in parsed_data:
                logger.warning(f"AI returned a handled error: {parsed_data['erro']}")
                return None, parsed_data["erro"]

            logger.info(f"Successfully processed content from {source_url}.")
            return parsed_data, None

        except RuntimeError as e:
            logger.critical(f"AI processing failed for {source_url} after all retries: {e}")
            return None, str(e)
        except Exception as e:
            logger.critical(f"An unexpected error occurred during AI processing for {source_url}: {e}", exc_info=True)
            return None, str(e)

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Tenta extrair um bloco JSON válido de um texto possivelmente misto/formatado."""
        # 0) Remover cercas de código Markdown ```json ... ``` ou ``` ... ```
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fenced:
            text = fenced.group(1)

        # 1) Se não, pegar do primeiro '{' ao último '}' (heurística ampla)
        # Isso funciona melhor para estruturas aninhadas
        first = text.find('{')
        last = text.rfind('}')
        if first != -1 and last != -1 and last > first:
            return text[first:last + 1]

        # 2) Como alternativa, tentar array
        first = text.find('[')
        last = text.rfind(']')
        if first != -1 and last != -1 and last > first:
            return text[first:last + 1]

        return text

    @staticmethod
    def _auto_fix_common_issues(s: str) -> str:
        """
        Clean up common JSON issues from AI responses.
        IMPORTANT: Must preserve the JSON structure!
        """
        # Remove BOM
        s = s.replace('\ufeff', '')
        
        # PASSO 0: Handle escaped newlines inside "conteudo_final" more carefully
        # Make sure actual newlines inside the content are properly escaped
        def fix_newlines_in_field(text: str) -> str:
            """Fix unescaped newlines inside JSON string fields."""
            result = []
            i = 0
            in_conteudo_final = False
            in_string = False
            escape_next = False
            
            while i < len(text):
                char = text[i]
                
                # Track escape sequences
                if escape_next:
                    result.append(char)
                    escape_next = False
                    i += 1
                    continue
                
                # Check if we're entering a backslash escape
                if char == '\\' and in_string:
                    result.append(char)
                    escape_next = True
                    i += 1
                    continue
                
                # Track if we're in the conteudo_final field
                if text[i:].startswith('"conteudo_final"'):
                    in_conteudo_final = True
                    result.append(text[i:i+16])
                    i += 16
                    continue
                
                # Track string state (quotes that aren't escaped)
                if char == '"':
                    result.append(char)
                    in_string = not in_string
                    
                    # If we just closed conteudo_final, reset the flag
                    if in_conteudo_final and not in_string:
                        in_conteudo_final = False
                    
                    i += 1
                    continue
                
                # Fix literal newlines inside strings (they must be escaped)
                if in_string and char in ('\n', '\r'):
                    if char == '\n':
                        result.append('\\n')
                    elif char == '\r':
                        result.append('\\r')
                    i += 1
                    continue
                
                result.append(char)
                i += 1
            
            return ''.join(result)
        
        s = fix_newlines_in_field(s)
        
        # PASSO 1: Remove truly invalid control characters (not tab/newline/CR)
        def remove_truly_invalid_control_chars(text: str) -> str:
            """Remove invalid control characters while preserving valid JSON escapes"""
            result = []
            i = 0
            while i < len(text):
                char = text[i]
                code = ord(char)
                
                # If it's a backslash, check if it's escaping the next character
                if char == '\\' and i + 1 < len(text):
                    result.append(char)
                    i += 1
                    # Append the next character (it's being escaped)
                    result.append(text[i])
                    i += 1
                    continue
                
                # Valid whitespace that can appear in JSON
                if code in (9, 10, 13):  # tab, LF, CR
                    result.append(char)
                    i += 1
                    continue
                
                # Remove problematic control characters
                if code < 32 or code == 127 or (128 <= code <= 159):
                    i += 1
                    continue
                
                result.append(char)
                i += 1
            
            return ''.join(result)
        
        s = remove_truly_invalid_control_chars(s)
        
        # PASSO 2: Escapar newlines que apareçam dentro de strings JSON (que devem estar escapados)
        def escape_unescaped_newlines_in_strings(text: str) -> str:
            """Escape literal newlines that appear inside JSON strings"""
            result = []
            in_string = False
            escape_next = False
            i = 0
            
            while i < len(text):
                char = text[i]
                
                # Track if we're in an escape sequence
                if escape_next:
                    result.append(char)
                    escape_next = False
                    i += 1
                    continue
                
                # Check for escape character
                if char == '\\' and in_string:
                    result.append(char)
                    escape_next = True
                    i += 1
                    continue
                
                # Toggle string state on quotes
                if char == '"':
                    result.append(char)
                    in_string = not in_string
                    i += 1
                    continue
                
                # If we're inside a string and we hit a literal newline, escape it
                if in_string and char == '\n':
                    result.append('\\n')
                    i += 1
                    continue
                
                # If we're inside a string and we hit a carriage return, escape it
                if in_string and char == '\r':
                    result.append('\\r')
                    i += 1
                    continue
                
                result.append(char)
                i += 1
            
            return ''.join(result)
        
        s = escape_unescaped_newlines_in_strings(s)
        
        # PASSO 3: Limpar espaço após \\n e chaves
        s = re.sub(r'\\n\s+("[\w_]+"\s*:)', r'\\n\1', s)
        
        # PASSO 4: Remover comentários JSON
        # NOTA: Remover isso porque pode quebrar URLs como //www.example.com dentro de strings
        # s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
        # s = re.sub(r"/\*[\s\S]*?\*/", "", s)
        
        # PASSO 5: Fixar estrutura JSON
        s = re.sub(r'\}\s*\{', r'}, {', s)
        s = re.sub(r',\s*([\]\}])', r'\1', s)
        s = re.sub(r"^```(?:json)?|```$", "", s.strip(), flags=re.IGNORECASE)
        
        return s

    @staticmethod
    def _escape_unescaped_quotes_in_html(text: str) -> str:
        """Escape unescaped quotes that appear inside HTML content within JSON strings.
        
        Uses a character-by-character approach to properly handle quotes in HTML.
        """
        result = []
        i = 0
        
        # Find "conteudo_final": " and then process the content until the closing quote
        while i < len(text):
            # Look for "conteudo_final": "
            if text[i:].startswith('"conteudo_final"'):
                # Found conteudo_final field, copy up to and including the opening quote
                j = i + 16  # Length of "conteudo_final"
                result.append(text[i:j])
                i = j
                
                # Skip whitespace and colon
                while i < len(text) and text[i] in (' ', ':', '\t'):
                    result.append(text[i])
                    i += 1
                
                # Must have opening quote
                if i < len(text) and text[i] == '"':
                    result.append('"')
                    i += 1
                    
                    # Now we need to find the actual closing quote
                    # We need to process character by character, properly handling escapes
                    # Escape any unescaped quotes we encounter
                    while i < len(text):
                        char = text[i]
                        
                        if char == '\\' and i + 1 < len(text):
                            # This is an escape sequence - keep both characters as-is
                            result.append(char)
                            result.append(text[i + 1])
                            i += 2
                        elif char == '"':
                            # This is an unescaped quote - check if it's the closing quote
                            # by looking ahead to see if we find a comma or bracket next
                            next_idx = i + 1
                            while next_idx < len(text) and text[next_idx] in (' ', '\t', '\n', '\r'):
                                next_idx += 1
                            
                            # If next non-whitespace is comma, bracket, or brace, this is the closing quote
                            if next_idx < len(text) and text[next_idx] in (',', '}', ']'):
                                # This is the closing quote
                                result.append('"')
                                i += 1
                                break
                            else:
                                # This is an unescaped quote in the middle of content - escape it
                                result.append('\\')
                                result.append('"')
                                i += 1
                        else:
                            result.append(char)
                            i += 1
                else:
                    # Malformed JSON, just continue
                    pass
            else:
                result.append(text[i])
                i += 1
        
        return ''.join(result)
    
    @classmethod
    def _parse_and_normalize_ai_response(cls, raw_text: str) -> Dict[str, Any]:
        """Extracts, cleans, and normalizes the AI's JSON response."""
        # PRIMEIRO: Extrair o bloco JSON das cercas e ruído
        s = cls._extract_json_block(raw_text).strip()
        
        # PRÉ-PROCESSAMENTO: Escapar aspas não escapadas no conteúdo HTML
        s = cls._escape_unescaped_quotes_in_html(s)
        
        # SEGUNDO: Aplicar limpeza agressiva DEPOIS de extrair
        s = cls._auto_fix_common_issues(s)
        
        # TERCEIRO: Fazer uma limpeza adicional de caracteres de controle estendidos
        # Isso é importante antes de tentar o json.loads
        def final_control_char_cleanup(text: str) -> str:
            """Remove any remaining control characters"""
            result = []
            for char in text:
                code = ord(char)
                # Remove qualquer caractere de controle (< 32 ou == 127) exceto tab, newline, CR
                if code < 32 and code not in (9, 10, 13):
                    continue
                if code == 127:
                    continue
                if 128 <= code <= 159:  # Extended control characters
                    continue
                result.append(char)
            return ''.join(result)
        
        s = final_control_char_cleanup(s)
        
        try:
            # Try direct parsing first
            data = json.loads(s)
        except json.JSONDecodeError as e:
            logger.error(f"Initial JSON decoding failed: {e}. Trying with secondary fixes.")
            logger.debug(f"JSON Error at line {e.lineno}, col {e.colno}: {e.msg}")
            logger.debug(f"Context (chars {max(0, e.pos-100)}-{min(len(s), e.pos+100)}): ...{s[max(0, e.pos-100):min(len(s), e.pos+100)]}...")
            
            # More aggressive cleaning on second attempt
            s2 = cls._auto_fix_common_issues(s)
            s2 = final_control_char_cleanup(s2)
            s2 = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', s2)
            
            try:
                data = json.loads(s2)
            except json.JSONDecodeError as second_e:
                logger.error(f"Secondary JSON decoding failed: {second_e}. Trying aggressive escape.")
                logger.debug(f"JSON Error at line {second_e.lineno}, col {second_e.colno}: {second_e.msg}")
                
                # Last resort: Try to escape any remaining problematic sequences
                try:
                    s3 = s2.encode('utf-8', 'ignore').decode('utf-8')
                    data = json.loads(s3)
                except json.JSONDecodeError as final_e:
                    debug_dir = Path("debug")
                    debug_dir.mkdir(exist_ok=True)
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    
                    # Save raw response with detailed error info
                    failed_path = debug_dir / f"failed_ai_{timestamp}.json.txt"
                    with open(failed_path, "w", encoding="utf-8") as f:
                        f.write(raw_text)
                    
                    # Save cleaned version for comparison
                    cleaned_path = debug_dir / f"failed_ai_{timestamp}_cleaned.txt"
                    with open(cleaned_path, "w", encoding="utf-8") as f:
                        f.write(s3)
                    
                    # Save error details
                    error_path = debug_dir / f"failed_ai_{timestamp}_error.txt"
                    with open(error_path, "w", encoding="utf-8") as f:
                        f.write(f"Error: {final_e}\n")
                        f.write(f"Line: {final_e.lineno}, Col: {final_e.colno}\n")
                        f.write(f"Message: {final_e.msg}\n")
                        if final_e.pos is not None:
                            start = max(0, final_e.pos - 200)
                            end = min(len(s3), final_e.pos + 200)
                            f.write(f"\nContext ({start}-{end}):\n")
                            f.write(s3[start:end])
                    
                    logger.critical(f"JSON decoding failed permanently. Saved to {failed_path}")
                    logger.critical(f"Cleaned version saved to {cleaned_path}")
                    logger.critical(f"Error details saved to {error_path}")
                    raise ValueError("Failed to decode JSON from AI response after multiple attempts.") from final_e

        # Normalize the structure if the model returns a single object or a list
        if isinstance(data, dict) and "resultados" not in data:
            # If data looks like a single result, wrap it
            data = {"resultados": [data]}
        elif isinstance(data, list):
            data = {"resultados": data}

        if not isinstance(data, dict) or "resultados" not in data or not isinstance(data["resultados"], list):
            raise ValueError("AI batch response is missing 'resultados' list after normalization")
            
        return data

    @classmethod
    def _parse_response(cls, text: str) -> Optional[Dict[str, Any]]:
        """Parse the AI response for a single article using the robust parser."""
        try:
            data = cls._parse_and_normalize_ai_response(text)
            results = data.get("resultados")

            if not results:
                logger.error("AI response is empty after parsing.")
                return None
            
            result = results[0] # For single response, take the first item

            if not isinstance(result, dict):
                logger.error(f"AI response item is not a dictionary. Received type: {type(result)}")
                return None

            if "erro" in result:
                logger.warning(f"AI returned a rejection error: {result['erro']}")
                return result

            required_keys = [
                "titulo_final", "conteudo_final", "meta_description",
                "focus_keyphrase", "tags_sugeridas", "yoast_meta"
            ]
            missing_keys = [key for key in required_keys if key not in result]

            if missing_keys:
                logger.error(f"AI response is missing required keys: {', '.join(missing_keys)}")
                return None

            return result

        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing or normalizing AI response: {e}")
            logger.debug(f"Received text: {text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing AI response: {e}")
            return None

    @classmethod
    def _parse_batch_response(cls, text: str, expected_count: int) -> Optional[List[Optional[Dict[str, Any]]]]:
        """Parse the AI response for a batch of articles using the robust parser."""
        try:
            data = cls._parse_and_normalize_ai_response(text)
            results = data["resultados"]

            if len(results) != expected_count:
                logger.error(f"AI batch response count mismatch. Expected {expected_count}, got {len(results)}")
                # We can still try to process what we got, but it's a partial failure.
                # For now, returning None as the original logic did.
                return None

            required_keys = [
                "titulo_final", "conteudo_final", "meta_description",
                "focus_keyphrase", "tags_sugeridas", "yoast_meta"
            ]

            valid_results: List[Optional[Dict[str, Any]]] = []
            for i, result in enumerate(results):
                if not isinstance(result, dict):
                    logger.error(f"AI batch result {i} is not a dictionary")
                    valid_results.append(None)
                    continue

                if "erro" in result:
                    logger.warning(f"AI returned a rejection error for batch item {i}: {result['erro']}")
                    valid_results.append(None)
                    continue

                missing_keys = [key for key in required_keys if key not in result]
                if missing_keys:
                    logger.error(f"AI batch result {i} is missing required keys: {', '.join(missing_keys)}")
                    valid_results.append(None)
                    continue

                valid_results.append(result)

            return valid_results

        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing or normalizing AI batch response: {e}")
            logger.debug(f"Received text: {text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing AI batch response: {e}")
            return None