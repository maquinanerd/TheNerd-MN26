# 📊 Sistema de Rastreamento de Tokens

Um sistema completo para rastrear, registrar e visualizar o uso de tokens em suas chamadas de API (Gemini, OpenAI, etc).

## 🎯 O que foi criado

### Arquivos principais:

1. **`app/token_tracker.py`** - Módulo de rastreamento
2. **`token_logs_viewer.py`** - Dashboard interativo em terminal
3. **`example_token_tracker.py`** - Exemplos de uso
4. **`IMPLEMENTACAO_TOKEN_TRACKER.py`** - Guia completo de implementação

## 📁 Estrutura de diretórios gerados

```
logs/tokens/
├── tokens_2025-02-05.jsonl      # Logs do dia (JSONL - uma linha por requisição)
├── tokens_2025-02-04.jsonl      # Logs de dias anteriores
├── token_stats.json             # Estatísticas consolidadas (atualizado em tempo real)
└── token_debug.log              # Log de debug do rastreador
```

## 🚀 Início rápido

### 1. Testar o sistema

```bash
# Executar exemplos (cria alguns logs de teste)
python example_token_tracker.py

# Visualizar dashboard
python token_logs_viewer.py
```

### 2. Integração básica (4 linhas)

```python
from app.token_tracker import log_tokens

# Após cada chamada à API:
log_tokens(
    prompt_tokens=150,
    completion_tokens=320,
    api_type="gemini",
    model="gemini-2.5-flash",
    api_key_suffix="abc123"
)
```

### 3. Visualização

Escolha uma opção no menu:
```
1. 📊 Resumo Geral - Total de tokens entrada/saída
2. 🔌 Detalhamento por API - Breakdown por tipo de API
3. 🕐 Últimos Logs - Ver registros recentes
4. 📈 Comparação Diária - Tokens por dia
5. 📥 Exportar para CSV - Exportar para análise
```

## 📊 Exemplos de saída

### Resumo Geral
```
📥 TOKENS DE ENTRADA (PROMPTS):
   1.250.000 tokens

📤 TOKENS DE SAÍDA (RESPOSTAS):
   2.800.000 tokens

✅ TOTAL DE TOKENS:
   4.050.000 tokens

📋 REQUISIÇÕES:
   Total:        500
   Sucesso:      485 ✔️
   Falhas:       15 ❌
   Taxa Sucesso: 97.0%
```

### Detalhamento por modelo
```
Modelo         │ Entrada   │ Saída     │ Total     │ Req.  │ Sucesso │ Falhas │ Taxa
───────────────┼───────────┼───────────┼───────────┼───────┼─────────┼────────┼─────
gemini-2.5-fl  │ 750.000   │ 1.800.000 │ 2.550.000 │ 300   │ 295     │ 5      │ 98.3%
gemini-lite    │ 500.000   │ 1.000.000 │ 1.500.000 │ 200   │ 190     │ 10     │ 95.0%
```

## 🔧 Integração com ai_client_gemini.py

Edite `app/ai_client_gemini.py`:

```python
from .token_tracker import log_tokens  # ← Adicione import

def generate_text(self, prompt: str, **kwargs) -> str:
    # ... seu código existente ...
    
    try:
        genai.configure(api_key=slot.key)
        m = genai.GenerativeModel(MODEL)
        resp = m.generate_content(prompt, **kwargs)
        
        # ← ADICIONE ESTE BLOCO
        if hasattr(resp, 'usage_metadata'):
            log_tokens(
                prompt_tokens=resp.usage_metadata.prompt_token_count,
                completion_tokens=resp.usage_metadata.candidate_token_count,
                api_type="gemini",
                model=MODEL,
                api_key_suffix=f"****{slot.key[-4:]}",
                success=True
            )
        
        return (resp.text or "").strip()
    
    except Exception as e:
        # Registrar falhas também
        log_tokens(
            prompt_tokens=0,
            completion_tokens=0,
            api_type="gemini",
            model=MODEL,
            api_key_suffix=f"****{slot.key[-4:]}",
            success=False,
            error_message=str(e)
        )
        raise
```

## 📝 Formato dos logs (JSONL)

Cada linha é um JSON:

```json
{
  "timestamp": "2025-02-05T10:30:45.123456",
  "api_type": "gemini",
  "model": "gemini-2.5-flash",
  "api_key_suffix": "****abc1",
  "prompt_tokens": 150,
  "completion_tokens": 320,
  "total_tokens": 470,
  "success": true,
  "error_message": null,
  "metadata": {
    "article_title": "Exemplo de Artigo",
    "processing_time_ms": 2450
  }
}
```

## 📈 Estatísticas (token_stats.json)

```json
{
  "gemini": {
    "gemini-2.5-flash": {
      "total_prompt_tokens": 1500000,
      "total_completion_tokens": 2800000,
      "total_tokens": 4300000,
      "total_requests": 500,
      "successful_requests": 485,
      "failed_requests": 15,
      "last_updated": "2025-02-05T10:45:30.123456"
    }
  }
}
```

## 🎓 Exemplos de uso

### Exemplo 1: Registro simples

```python
from app.token_tracker import log_tokens

log_tokens(
    prompt_tokens=200,
    completion_tokens=450,
    api_type="gemini",
    model="gemini-2.5-flash"
)
```

### Exemplo 2: Com identificação de chave

```python
log_tokens(
    prompt_tokens=200,
    completion_tokens=450,
    api_type="gemini",
    model="gemini-2.5-flash",
    api_key_suffix="****xyz9"  # Últimas 4 caracteres
)
```

### Exemplo 3: Registrando falhas

```python
log_tokens(
    prompt_tokens=0,
    completion_tokens=0,
    api_type="gemini",
    model="gemini-2.5-flash",
    success=False,
    error_message="Quota excedida (429)"
)
```

### Exemplo 4: Com metadados

```python
log_tokens(
    prompt_tokens=150,
    completion_tokens=320,
    api_type="gemini",
    model="gemini-2.5-flash",
    success=True,
    metadata={
        "article_title": "Título do Artigo",
        "processing_time_ms": 2450,
        "category": "tech"
    }
)
```

### Exemplo 5: Usar diretamente no código

```python
from app.token_tracker import get_tracker

tracker = get_tracker()
tracker.print_summary()  # Imprime resumo formatado

# Obter estatísticas programaticamente
stats = tracker.get_summary()
print(f"Total de tokens: {stats['total_tokens']:,}")
```

## 🔍 Analisando os logs

### Via Python

```python
import json
from pathlib import Path

log_file = Path('logs/tokens/tokens_2025-02-05.jsonl')
for line in log_file.read_text().split('\n'):
    if line.strip():
        log = json.loads(line)
        print(f"{log['timestamp']} - {log['api_type']}: "
              f"{log['prompt_tokens']} entrada / {log['completion_tokens']} saída")
```

### Via terminal

```bash
# Ver últimas 20 linhas
tail -20 logs/tokens/tokens_2025-02-05.jsonl | jq .

# Contar requisições
wc -l logs/tokens/tokens_2025-02-05.jsonl

# Extrair apenas bem-sucedidas
grep '"success": true' logs/tokens/tokens_2025-02-05.jsonl | wc -l
```

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'app.token_tracker'"

```bash
# Verifique se o arquivo existe
ls app/token_tracker.py

# Certifique-se que __init__.py existe
ls app/__init__.py

# Teste a importação
python -c "from app.token_tracker import log_tokens; print('OK')"
```

### Logs não estão sendo criados

1. Verifique permissões:
```bash
ls -la logs/
chmod 755 logs/tokens/
```

2. Verifique erros em debug:
```bash
cat logs/tokens/token_debug.log
```

### Stats.json não atualiza

- Verifique se há espaço em disco
- Verifique permissões de escrita
- Revise `token_debug.log` para erros

## 📊 Casos de uso

### 1. Monitorar custos
- Entrada vs Saída mostra eficiência dos prompts
- Identifique modelos mais caros
- Detecte picos de uso

### 2. Detectar problemas
- Taxa de sucesso baixa = problema com chaves
- Muitos zeros = erro na integração
- Padrões de falha = throttling/rate limiting

### 3. Otimização
- Compare tokens entrada/saída por modelo
- Identifique modelos mais eficientes
- Rastreie melhorias após ajustes

### 4. Auditoria
- Log completo de cada requisição
- Timestamps precisos
- Metadados customizáveis
- Exportação em CSV

## 🔐 Privacidade & Segurança

- ✅ Apenas últimos 4 caracteres da chave são armazenados
- ✅ Nenhum conteúdo de prompts ou respostas é registrado
- ✅ Logs armazenados localmente
- ✅ Arquivo permissions padrão (644 para logs)

## 📋 Próximas etapas sugeridas

1. ✅ Executar `example_token_tracker.py` para testar
2. ✅ Executar `token_logs_viewer.py` para visualizar
3. 🔄 Integrar `log_tokens()` ao seu código
4. 📊 Monitorar padrões de uso
5. 🎯 Otimizar baseado em insights

## 📚 Referência rápida

```python
# Importar
from app.token_tracker import log_tokens, get_tracker

# Registrar um token
log_tokens(
    prompt_tokens=int,          # Tokens de entrada (obrigatório)
    completion_tokens=int,       # Tokens de saída (obrigatório)
    api_type="gemini",           # Tipo de API (padrão: gemini)
    model="gemini-2.5-flash",    # Nome do modelo (padrão: unknown)
    api_key_suffix="****abc1",   # Sufixo da chave (padrão: unknown)
    success=True,                # Sucesso da requisição (padrão: True)
    error_message=None,          # Mensagem de erro (padrão: None)
    metadata={}                  # Dados adicionais (padrão: {})
)

# Obter tracker
tracker = get_tracker()
tracker.print_summary()
stats = tracker.get_summary()
```

## 📞 Suporte

Se encontrar problemas:
1. Verifique `logs/tokens/token_debug.log`
2. Consulte o guia `IMPLEMENTACAO_TOKEN_TRACKER.py`
3. Execute `example_token_tracker.py` para validar
4. Verifique permissões de diretório

---

**Criado em:** 5 de Fevereiro de 2026  
**Versão:** 1.0  
**Status:** ✅ Pronto para uso
