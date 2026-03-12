#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIA DE IMPLEMENTAÇÃO - TOKEN TRACKER
=====================================

Este documento explica como integrar o sistema de rastreamento de tokens
ao seu projeto existente.
"""

# ============================================================================
# 1. ESTRUTURA CRIADA
# ============================================================================

"""
Foram criados 3 arquivos:

1. app/token_tracker.py
   - Módulo principal de rastreamento
   - Salva logs em: logs/tokens/tokens_YYYY-MM-DD.jsonl
   - Atualiza estatísticas em: logs/tokens/token_stats.json
   
2. token_logs_viewer.py
   - Dashboard em terminal para visualizar logs
   - Menu interativo com 5 opções
   - Exportação para CSV
   
3. example_token_tracker.py
   - Exemplos de uso do tracker
   - Execute para testar

4. IMPLEMENTACAO_TOKEN_TRACKER.py (este arquivo)
   - Guia de implementação
"""

# ============================================================================
# 2. ESTRUTURA DE ARQUIVOS GERADOS
# ============================================================================

"""
logs/tokens/
├── tokens_2025-02-05.jsonl          # Logs do dia (JSON Lines)
├── tokens_2025-02-04.jsonl          # Logs de dias anteriores
├── token_stats.json                 # Estatísticas consolidadas
└── token_debug.log                  # Debug do rastreador
"""

# ============================================================================
# 3. INTEGRAÇÃO RÁPIDA (4 linhas)
# ============================================================================

"""
# No início do seu arquivo:
from app.token_tracker import log_tokens

# Após cada chamada à API Gemini:
log_tokens(
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    api_type="gemini",
    model="gemini-2.5-flash",
    api_key_suffix="abc123"
)
"""

# ============================================================================
# 4. INTEGRAÇÃO COM app/ai_client_gemini.py
# ============================================================================

"""
Modifique o método generate_text() em ai_client_gemini.py:

    def generate_text(self, prompt: str, **kwargs) -> str:
        from .token_tracker import log_tokens
        
        # ... seu código existente ...
        
        try:
            # ... chamada à API ...
            resp = m.generate_content(prompt, **kwargs)
            
            # ADICIONE ESTAS LINHAS:
            if hasattr(resp, 'usage_metadata'):
                log_tokens(
                    prompt_tokens=resp.usage_metadata.prompt_token_count,
                    completion_tokens=resp.usage_metadata.candidate_token_count,
                    api_type="gemini",
                    model=MODEL,
                    api_key_suffix=self.last_used_key,
                    success=True
                )
            
            return (resp.text or "").strip()
        
        except Exception as e:
            # Registrar falha também
            log_tokens(
                prompt_tokens=0,
                completion_tokens=0,
                api_type="gemini",
                model=MODEL,
                api_key_suffix=self.last_used_key,
                success=False,
                error_message=str(e)
            )
            raise
"""

# ============================================================================
# 5. VERIFICAR RESPOSTA DO GEMINI
# ============================================================================

"""
Para verificar quais campos a API Gemini retorna, adicione este código:

import google.generativeai as genai

genai.configure(api_key="sua_chave")
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Teste")

print("Campos disponíveis:")
print(f"  response.text: {response.text[:50]}...")
print(f"  dir(response): {[x for x in dir(response) if not x.startswith('_')]}")

if hasattr(response, 'usage_metadata'):
    print(f"\nTokens:")
    print(f"  prompt_token_count: {response.usage_metadata.prompt_token_count}")
    print(f"  candidate_token_count: {response.usage_metadata.candidate_token_count}")
"""

# ============================================================================
# 6. USO DO TRACKER
# ============================================================================

"""
Exemplo completo de registro de tokens:

from app.token_tracker import log_tokens

log_tokens(
    prompt_tokens=150,                  # Tokens no input/pergunta
    completion_tokens=320,              # Tokens na output/resposta
    api_type="gemini",                  # Tipo de API (gemini, openai, etc)
    model="gemini-2.5-flash",           # Nome do modelo usado
    api_key_suffix="abc123",            # Últimas 4 caracteres da chave
    success=True,                       # Se a chamada foi bem-sucedida
    error_message=None,                 # Mensagem de erro (se houver)
    metadata={                          # Dados adicionais (opcionais)
        "article_title": "Título do Artigo",
        "processing_time_ms": 2450,
        "request_type": "article_generation"
    }
)
"""

# ============================================================================
# 7. VISUALIZAR LOGS
# ============================================================================

"""
Execute no terminal:

    python token_logs_viewer.py

Opções do dashboard:
  1. 📊 Resumo Geral - Total de tokens entrada/saída
  2. 🔌 Detalhamento por API - Breakdown por tipo de API
  3. 🕐 Últimos Logs - Ver logs recentes
  4. 📈 Comparação Diária - Tokens por dia
  5. 📥 Exportar para CSV - Exportar estatísticas
"""

# ============================================================================
# 8. ESTRUTURA DOS LOGS (JSONL)
# ============================================================================

"""
Cada linha em logs/tokens/tokens_YYYY-MM-DD.jsonl é um JSON:

{
  "timestamp": "2025-02-05T10:30:45.123456",
  "api_type": "gemini",
  "model": "gemini-2.5-flash",
  "api_key_suffix": "abc123",
  "prompt_tokens": 150,
  "completion_tokens": 320,
  "total_tokens": 470,
  "success": true,
  "error_message": null,
  "metadata": {
    "article_title": "Exemplo",
    "processing_time_ms": 2450
  }
}

Exemplo de falha:

{
  "timestamp": "2025-02-05T10:31:45.123456",
  "api_type": "gemini",
  "model": "gemini-2.5-flash",
  "api_key_suffix": "def456",
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "total_tokens": 0,
  "success": false,
  "error_message": "Quota excedida (429)",
  "metadata": {}
}
"""

# ============================================================================
# 9. ESTRUTURA DAS ESTATÍSTICAS (JSON)
# ============================================================================

"""
Arquivo: logs/tokens/token_stats.json

{
  "gemini": {
    "gemini-2.5-flash": {
      "total_prompt_tokens": 15000,
      "total_completion_tokens": 32000,
      "total_tokens": 47000,
      "total_requests": 50,
      "successful_requests": 48,
      "failed_requests": 2,
      "last_updated": "2025-02-05T10:45:30.123456"
    },
    "gemini-2.5-flash-lite": {
      "total_prompt_tokens": 5000,
      "total_completion_tokens": 8000,
      "total_tokens": 13000,
      "total_requests": 20,
      "successful_requests": 20,
      "failed_requests": 0,
      "last_updated": "2025-02-05T10:40:15.123456"
    }
  }
}
"""

# ============================================================================
# 10. EXEMPLO PRÁTICO - INTEGRAÇÃO COMPLETA
# ============================================================================

"""
Arquivo: app/ai_client_gemini.py (MODIFICADO)

import os
import logging
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from http import HTTPStatus
from .token_tracker import log_tokens  # ← ADICIONAR IMPORT

MODEL = os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite")

class AIClient:
    def __init__(self, keys, min_interval_s, backoff_base=20, backoff_max=300):
        self.pool = KeyPool(keys)
        self.rl = RateLimiter(min_interval_s)
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.last_used_key = None
        logging.info(f"AI CLIENT: Inicializado com {len(keys)} chaves de API")

    def generate_text(self, prompt: str, **kwargs) -> str:
        backoff = self.backoff_base
        attempt = 0
        while True:
            attempt += 1
            slot = self.pool.next_ready()
            self.rl.wait()
            
            self.last_used_key = slot.key
            
            try:
                logging.info(f"IA TENTATIVA {attempt}: Chave ****{slot.key[-4:]}")
                genai.configure(api_key=slot.key)
                m = genai.GenerativeModel(MODEL)
                resp = m.generate_content(prompt, **kwargs)
                
                # ← ADICIONAR ESTE BLOCO
                if hasattr(resp, 'usage_metadata'):
                    log_tokens(
                        prompt_tokens=resp.usage_metadata.prompt_token_count,
                        completion_tokens=resp.usage_metadata.candidate_token_count,
                        api_type="gemini",
                        model=MODEL,
                        api_key_suffix=f"****{slot.key[-4:]}",
                        success=True
                    )
                
                logging.info(f"IA OK: Tentativa {attempt} sucesso")
                return (resp.text or "").strip()

            except google_exceptions.ResourceExhausted as e:
                log_tokens(  # ← REGISTRAR FALHA
                    prompt_tokens=0,
                    completion_tokens=0,
                    api_type="gemini",
                    model=MODEL,
                    api_key_suffix=f"****{slot.key[-4:]}",
                    success=False,
                    error_message="429 - Quota excedida"
                )
                self.pool.penalize(slot, retry_after=30)
                backoff = min(backoff * 2, self.backoff_max)
                logging.warning(f"IA RETRY: Aguardando {backoff}s...")
                continue
            
            except Exception as e:
                log_tokens(  # ← REGISTRAR OUTRAS FALHAS
                    prompt_tokens=0,
                    completion_tokens=0,
                    api_type="gemini",
                    model=MODEL,
                    api_key_suffix=f"****{slot.key[-4:]}",
                    success=False,
                    error_message=str(e)
                )
                logging.error(f"IA ERRO: {e}", exc_info=True)
                raise RuntimeError(f"Erro: {e}") from e
"""

# ============================================================================
# 11. TESTAR A INTEGRAÇÃO
# ============================================================================

"""
1. Execute o exemplo:
   python example_token_tracker.py

2. Verifique os logs criados:
   ls -la logs/tokens/

3. Visualize no dashboard:
   python token_logs_viewer.py

4. Verificar arquivo de estadísticas:
   cat logs/tokens/token_stats.json
"""

# ============================================================================
# 12. DICAS & TROUBLESHOOTING
# ============================================================================

"""
❓ "ModuleNotFoundError: No module named 'app.token_tracker'"
  → Certifique-se de que o arquivo está em app/token_tracker.py
  → Verifique se __init__.py existe em app/

❓ Logs não estão sendo criados
  → Verifique permissões de escrita em logs/tokens/
  → Verifique em logs/tokens/token_debug.log por erros

❓ Como resetar os logs?
  → Delete logs/tokens/token_stats.json (estatísticas serão recalculadas)
  → Delete logs/tokens/tokens_*.jsonl (para remover logs diários)

❓ Como extrair dados em Python?
  → from app.token_tracker import get_tracker
  → stats = get_tracker().get_summary()

❓ Integrar com banco de dados?
  → Modifique token_tracker.py para salvar também em SQLite
  → Use get_summary() para popular tabelas no DB
"""

# ============================================================================
# 13. PRÓXIMAS ETAPAS
# ============================================================================

"""
✅ Arquivos criados:
  - app/token_tracker.py
  - token_logs_viewer.py
  - example_token_tracker.py
  - IMPLEMENTACAO_TOKEN_TRACKER.py (este)

🔧 Para completar:
  1. Edite app/ai_client_gemini.py e adicione o rastreamento
  2. Execute python example_token_tracker.py para testar
  3. Execute python token_logs_viewer.py para visualizar
  4. Integre ao seu pipeline de produção

📊 Monitorar:
  - Entrada vs Saída (para detectar qualidade de respostas)
  - Taxa de sucesso (para detectar problemas com chaves)
  - Tokens por modelo (para otimizar custos)
  - Comparação diária (para identificar picos)
"""

print(__doc__)
