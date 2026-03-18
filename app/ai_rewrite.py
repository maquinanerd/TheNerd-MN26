# app/ai_rewrite.py
"""
Phase 2 of the 3-phase AI pipeline: editorial rewrite.

Transforms sanitized HTML into an original Máquina Nerd article written
in journalistic Português-Brasil, injecting internal links and videos.
"""
import logging
import os
import re
from typing import TYPE_CHECKING, Dict, Any, List

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .ai_client_gemini import AIClient

logger = logging.getLogger(__name__)

# Portais concorrentes — apenas log de aviso (Phase 1 deve remover, mas checamos)
_COMPETITORS = ("omelete", "jovem nerd", "ign brasil", "adorocinema", "cineclick")

# Frases genéricas de padding que o prompt proíbe — usadas só para log de debug
_PADDING_PHRASES = (
    "isso pode indicar",
    "isso sugere",
    "isso reforça",
    "os fãs podem esperar",
    "a série tem potencial",
)

_PROMPT_TEMPLATE = """\
Você é um jornalista sênior especializado em entretenimento, escrevendo para um site brasileiro de notícias de cultura pop (Máquina Nerd).

Sua tarefa é reescrever o artigo fornecido em um texto jornalístico original, em português do Brasil.

O objetivo NÃO é apenas reescrever — é criar uma matéria que pareça produzida por uma redação profissional.

━━━━━━━━━━━━━━━━━━━━━━━
REGRAS CRÍTICAS
━━━━━━━━━━━━━━━━━━━━━━━

1. NÃO siga a mesma estrutura do artigo original.
2. NÃO mantenha a mesma ordem dos fatos.
3. NÃO traduza frases diretamente.
4. NÃO reutilize construções ou frases da fonte.
5. O texto deve parecer uma matéria independente da fonte.
6. Mantenha em inglês apenas termos sem tradução natural (showrunner, spin-off, season finale).
7. Verbos no presente: "chega", "confirma", "revela" — NUNCA infinitivo.
8. NUNCA use <h1>. Máximo 6 <h2> (exceto listicles).
9. Não mencione outros portais de notícias.
10. Não incluir linha "Fonte:" no texto.

━━━━━━━━━━━━━━━━━━━━━━━
ESTRUTURA OBRIGATÓRIA
━━━━━━━━━━━━━━━━━━━━━━━

- Lead forte com a principal informação da notícia
- Corpo do texto reorganizado com fluidez narrativa
- Pelo menos 1 BLOCO EDITORIAL ORIGINAL explicando:
  - por que essa notícia importa
  - conexão com a franquia/universo
  - possíveis impactos futuros
- Conclusão natural

━━━━━━━━━━━━━━━━━━━━━━━
BLOCO EDITORIAL (CRÍTICO)
━━━━━━━━━━━━━━━━━━━━━━━

Inclua um parágrafo analítico que NÃO exista na fonte original.

Esse trecho deve:
- adicionar contexto
- interpretar a informação
- conectar com eventos, obras ou personagens relacionados

Se esse bloco não existir, o texto está incorreto.

━━━━━━━━━━━━━━━━━━━━━━━
FORMATAÇÃO
━━━━━━━━━━━━━━━━━━━━━━━

- Use HTML limpo
- <h2> para subtítulos
- <p> para parágrafos
- Parágrafos com no máximo 4 frases

Use <strong> APENAS na primeira ocorrência de:
- nomes de filmes
- nomes de séries
- personagens
- franquias (Marvel, DC, MCU, etc.)

Não repita o negrito desnecessariamente.

Imagens em <figure> com <figcaption> descritivo. Nunca duas imagens seguidas sem <p> entre elas.

━━━━━━━━━━━━━━━━━━━━━━━
ESTILO
━━━━━━━━━━━━━━━━━━━━━━━

- Escreva como jornalista experiente
- Evite frases genéricas como:
  "isso pode indicar"
  "isso sugere"
  "isso reforça"
  "os fãs podem esperar"
  "a série tem potencial"
- Evite repetição de estrutura
- Varie o ritmo das frases
- Use linguagem natural e fluida

━━━━━━━━━━━━━━━━━━━━━━━
SEO
━━━━━━━━━━━━━━━━━━━━━━━

- Preserve entidades importantes (nomes, obras, estúdios)
- Não faça keyword stuffing
- Priorize clareza e legibilidade
- Links internos (use 1 a 3 contextualmente): <a href="https://{domain}/tag/tag-aqui">Texto âncora</a>
  Âncora = nome de franquia, série, filme ou ator. NUNCA "clique aqui" ou "saiba mais".

━━━━━━━━━━━━━━━━━━━━━━━
SAÍDA
━━━━━━━━━━━━━━━━━━━━━━━

Retorne apenas o artigo final em HTML.
Não inclua explicações, comentários ou observações.
Não use blocos de código ou marcadores markdown.

━━━━━━━━━━━━━━━━━━━━━━━
DADOS PARA PROCESSAMENTO
━━━━━━━━━━━━━━━━━━━━━━━

LINKS INTERNOS DISPONÍVEIS:
{link_block}

VÍDEOS DISPONÍVEIS (incorpore no máximo 2, no formato abaixo):
<figure class="video-container"><iframe src="URL_AQUI" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></figure>
{videos_list}

DOMÍNIO PARA LINKS: {domain}

CONTEÚDO FONTE:
{content}"""


def _post_process(html: str) -> str:
    """
    Minimal post-processing of rewritten HTML:
    - Downgrade <h1> → <h2>
    - Remove paragraphs that start with "Fonte:"
    - Log warnings for competitor mentions or padding phrases
    """
    soup = BeautifulSoup(html, "html.parser")

    # Downgrade h1 → h2 (the prompt forbids h1, but we enforce it)
    for h1 in soup.find_all("h1"):
        h1.name = "h2"
        logger.debug("[REWRITE] <h1> downgraded to <h2>")

    # Remove any "Fonte:" paragraph the model may have added
    for p in soup.find_all("p"):
        if p.get_text(strip=True).lower().startswith("fonte:"):
            p.decompose()
            logger.debug("[REWRITE] Removed 'Fonte:' paragraph")

    result = str(soup)

    # Warn if competitor names leaked through (Phase 1 should have caught these)
    lowered = result.lower()
    for comp in _COMPETITORS:
        if comp in lowered:
            logger.warning(f"[REWRITE] Competitor '{comp}' detected in output — Phase 1 may have missed it")

    # Debug-log padding phrases (informational only — not blocking)
    for phrase in _PADDING_PHRASES:
        if phrase in lowered:
            logger.debug(f"[REWRITE] Padding phrase detected: '{phrase}'")

    return result


def rewrite(html_clean: str, meta: Dict[str, Any], client: "AIClient") -> str:
    """
    Phase 2: transform clean HTML into original Máquina Nerd journalism.

    Args:
        html_clean: Sanitized HTML from phase 1.
        meta:       Dict with keys: domain, link_block, videos (list of dicts with embed_url).
        client:     Shared AIClient instance.

    Returns:
        Rewritten HTML string. Falls back to html_clean on AI failure.
    """
    if not html_clean or not html_clean.strip():
        return html_clean

    domain = meta.get("domain", "")
    link_block = meta.get("link_block", "Nenhum")
    videos: List[Dict[str, Any]] = meta.get("videos", [])
    videos_list = "\n".join(
        v.get("embed_url", "") for v in videos if isinstance(v, dict) and v.get("embed_url")
    ) or "Nenhum"

    prompt = _PROMPT_TEMPLATE.format(
        domain=domain,
        link_block=link_block,
        videos_list=videos_list,
        content=html_clean,
    )

    generation_config = {
        "temperature": 0.55,
        "max_output_tokens": 16000,
    }

    try:
        response_data = client.generate_text(prompt, generation_config=generation_config)

        if isinstance(response_data, tuple):
            response_text, tokens_info = response_data
        else:
            response_text = response_data
            tokens_info = {}

        _log_phase_tokens(tokens_info, phase="rewrite")

        if not response_text or not response_text.strip():
            logger.warning("[REWRITE] AI returned empty response — using sanitized HTML")
            return html_clean

        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]).rstrip("`").strip()

        # Post-processing: enforce structural rules regardless of AI compliance
        text = _post_process(text)

        logger.info(f"[REWRITE] OK — {len(html_clean)} → {len(text)} chars")
        return text

    except Exception as exc:
        logger.error(f"[REWRITE] AI call failed: {exc} — using sanitized HTML", exc_info=True)
        return html_clean


def _log_phase_tokens(tokens_info: dict, phase: str) -> None:
    try:
        from .token_tracker import log_tokens
        prompt_tokens = int(tokens_info.get("prompt_tokens", 0))
        completion_tokens = int(tokens_info.get("completion_tokens", 0))
        if prompt_tokens + completion_tokens > 0:
            log_tokens(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                api_type="gemini",
                model=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite"),
                metadata={"operation": f"3phase_{phase}"},
            )
    except Exception as exc:
        logger.debug(f"[REWRITE] token logging skipped: {exc}")
