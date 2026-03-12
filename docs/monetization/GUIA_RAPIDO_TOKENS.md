# 🎯 GUIA RÁPIDO - SISTEMA DE LOG DE TOKENS

## 📌 O que foi criado?

Um sistema **completo** para rastrear tokens de entrada e saída em suas APIs.

### ✅ Arquivos criados:

```
✅ app/token_tracker.py              - Rastreador principal
✅ token_logs_viewer.py              - Dashboard em terminal  
✅ example_token_tracker.py          - Exemplos básicos
✅ test_token_tracker.py             - Suite de testes
✅ IMPLEMENTACAO_TOKEN_TRACKER.py    - Guia técnico
✅ README_TOKEN_TRACKER.md           - Documentação completa
✅ RESUMO_SISTEMA_TOKENS.md          - Resumo executivo
✅ GUIA_RAPIDO_TOKENS.md             - Este arquivo
```

### 📂 Diretórios criados:

```
logs/tokens/
├── tokens_2025-02-05.jsonl         - Logs do dia
├── token_stats.json                - Estatísticas
└── token_debug.log                 - Debug
```

---

## 🚀 COMEÇAR AGORA (3 passos)

### 1️⃣ Testar que tudo funciona

```bash
python example_token_tracker.py
```

✅ Resultado esperado:
```
✅ Log registrado: 150 tokens entrada + 320 tokens saída
✅ Log registrado: 200 tokens entrada + 450 tokens saída
📊 Total de Tokens: 1.970
```

### 2️⃣ Visualizar no dashboard

```bash
python token_logs_viewer.py
```

Escolha opção **1** para ver resumo.

### 3️⃣ Integrar ao seu código

Adicione 4 linhas:

```python
from app.token_tracker import log_tokens

log_tokens(
    prompt_tokens=150,
    completion_tokens=320,
    api_type="gemini",
    model="gemini-2.5-flash"
)
```

---

## 📊 ENTENDER O BÁSICO

### 🔢 Os 4 números que importam

```
📥 ENTRADA (Prompts)     = Tokens que você mandou
📤 SAÍDA (Respostas)     = Tokens que a API devolveu  
✅ TOTAL                 = Entrada + Saída
📋 REQUISIÇÕES           = Quantas vezes chamou a API
```

### 📈 Exemplo prático

```
Você escreve: "Resuma este artigo em 3 linhas"
             ↓
        API Gemini processa
             ↓
API retorna: "Este artigo fala sobre..."

Resultado:
  📥 Entrada: 15 tokens (seu texto)
  📤 Saída:   45 tokens (resposta)
  ✅ Total:   60 tokens
  💰 Custo aprox: $0.0135 (Gemini Flash)
```

---

## 🎓 EXEMPLOS SIMPLES

### Exemplo 1: Básico

```python
from app.token_tracker import log_tokens

log_tokens(100, 200)  # 100 entrada, 200 saída
```

### Exemplo 2: Com modelo

```python
log_tokens(
    prompt_tokens=100,
    completion_tokens=200,
    model="gemini-2.5-flash"
)
```

### Exemplo 3: Com sucesso/falha

```python
# Sucesso
log_tokens(100, 200, success=True)

# Falha
log_tokens(0, 0, success=False, error_message="429 Quota excedida")
```

### Exemplo 4: Integrado na API

```python
def generate_text(prompt):
    from app.token_tracker import log_tokens
    
    # Sua chamada da API
    response = gemini_api.call(prompt)
    
    # Registre os tokens!
    log_tokens(
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.output_tokens,
        api_type="gemini",
        model="gemini-2.5-flash"
    )
    
    return response.text
```

---

## 🔍 VISUALIZAR DADOS

### Option 1: Dashboard interativo

```bash
python token_logs_viewer.py
```

Menu:
```
1. Ver totais gerais
2. Ver por tipo de API
3. Ver logs recentes
4. Ver comparação diária
5. Exportar CSV
```

### Option 2: Python direto

```python
from app.token_tracker import get_tracker

tracker = get_tracker()
tracker.print_summary()

# Ou programaticamente
stats = tracker.get_summary()
print(f"Total: {stats['total_tokens']:,} tokens")
```

### Option 3: Arquivo JSON

```bash
# Ver stats consolidadas
cat logs/tokens/token_stats.json

# Ver últimas 10 requisições
tail -10 logs/tokens/tokens_2025-02-05.jsonl
```

---

## 🔧 INTEGRAÇÃO PASSO A PASSO

Se você quer integrar no código de produção:

### Passo 1: Adicionar import

```python
# Em seu arquivo de API (ex: app/ai_client_gemini.py)
from .token_tracker import log_tokens
```

### Passo 2: Após chamar API

```python
def generate_text(self, prompt):
    # ... seu código ...
    response = genai.GenerativeModel(MODEL).generate_content(prompt)
    
    # AQUI: Registre os tokens
    if hasattr(response, 'usage_metadata'):
        log_tokens(
            prompt_tokens=response.usage_metadata.prompt_token_count,
            completion_tokens=response.usage_metadata.candidate_token_count,
            api_type="gemini",
            model=MODEL,
            success=True
        )
    
    return response.text
```

### Passo 3: Registrar erros também

```python
except Exception as e:
    log_tokens(
        prompt_tokens=0,
        completion_tokens=0,
        api_type="gemini",
        model=MODEL,
        success=False,
        error_message=str(e)
    )
    raise
```

### Pronto! ✅

Agora toda vez que chamar a API, os tokens serão registrados automaticamente.

---

## 📊 EXEMPLOS DE SAÍDA

### Resumo Geral

```
📥 TOKENS DE ENTRADA (PROMPTS):
   700 tokens

📤 TOKENS DE SAÍDA (RESPOSTAS):
   1.270 tokens

✅ TOTAL DE TOKENS:
   1.970 tokens

📋 REQUISIÇÕES:
   Total:        4
   Sucesso:      3 ✔️
   Falhas:       1 ❌
   Taxa Sucesso: 75.0%
```

### Por Modelo

```
Modelo                │ Entrada    │ Saída     │ Total
──────────────────────┼────────────┼───────────┼─────────
gemini-2.5-flash      │ 450        │ 770       │ 1.220
gemini-2.5-flash-lite │ 250        │ 500       │ 750
```

---

## 🐛 PROBLEMAS? SOLUÇÕES!

### ❌ Erro: "ModuleNotFoundError"

```bash
# Verifique se arquivo existe
ls app/token_tracker.py

# Se não existir, recrie:
python example_token_tracker.py
```

### ❌ Nenhum log aparece

```bash
# Verifique se diretório tem permissão
ls -la logs/

# Verifique erros
cat logs/tokens/token_debug.log
```

### ❌ Stats.json não atualiza

```bash
# Delete e deixe recriar
rm logs/tokens/token_stats.json

# Registre novos tokens
python example_token_tracker.py
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

- [ ] 1. Executou `python example_token_tracker.py`?
- [ ] 2. Viu os logs em `logs/tokens/`?
- [ ] 3. Rodou `python token_logs_viewer.py`?
- [ ] 4. Explorou o dashboard (5 menus)?
- [ ] 5. Entendeu os 4 números básicos?
- [ ] 6. Adicionou import `log_tokens` no seu código?
- [ ] 7. Adicionou chamada `log_tokens()` após API call?
- [ ] 8. Testou com dados reais?
- [ ] 9. Monitora via dashboard regularmente?
- [ ] 10. Documentou integrações com comentários?

---

## 🎯 PRÓXIMAS ETAPAS

### Curto prazo (hoje)
1. ✅ Executar exemplos
2. ✅ Explorar dashboard
3. ✅ Entender estrutura

### Médio prazo (esta semana)
4. 🔄 Integrar no código
5. 🔄 Testar com dados reais
6. 🔄 Verificar logs

### Longo prazo (contínuo)
7. 📊 Monitorar diariamente
8. 💡 Otimizar baseado em dados
9. 📈 Comparar modelos
10. 💰 Analisar custos

---

## 📚 DOCUMENTAÇÃO

| Arquivo | Para quê |
|---------|----------|
| `app/token_tracker.py` | Usar o rastreador |
| `token_logs_viewer.py` | Ver logs interativamente |
| `example_token_tracker.py` | Aprender com exemplos |
| `test_token_tracker.py` | Testar a integração |
| `README_TOKEN_TRACKER.md` | Documentação completa |
| `IMPLEMENTACAO_TOKEN_TRACKER.py` | Guia técnico |
| `RESUMO_SISTEMA_TOKENS.md` | Visão geral |
| `GUIA_RAPIDO_TOKENS.md` | Este arquivo 👈 |

---

## 🎓 REFERÊNCIA RÁPIDA

```python
# Importar
from app.token_tracker import log_tokens, get_tracker

# Registrar tokens simples
log_tokens(100, 200)

# Registrar com detalhes
log_tokens(100, 200, api_type="gemini", model="flash", success=True)

# Registrar falha
log_tokens(0, 0, success=False, error_message="429 Quota")

# Obter resumo
tracker = get_tracker()
tracker.print_summary()

# Obter stats programaticamente
stats = tracker.get_summary()
print(stats['total_tokens'])
```

---

## ✨ RESUMO

| O quê | Como |
|-------|------|
| Começar | `python example_token_tracker.py` |
| Ver logs | `python token_logs_viewer.py` |
| Testar | `python test_token_tracker.py` |
| Integrar | Adicione 4 linhas no seu código |
| Monitorar | Dashboard menu opção 1 |
| Exportar | Dashboard menu opção 5 |

---

## 💡 DICAS

1. **Registre sempre**, mesmo erros
2. **Use metadados** para contexto (article_id, etc)
3. **Compare modelos** para otimizar custos
4. **Exporte CSV** para análises externas
5. **Monitore diário** para detectar anomalias

---

## 🚀 VAMOS LÁ!

Execute agora:

```bash
python example_token_tracker.py
```

Depois:

```bash
python token_logs_viewer.py
```

Escolha **Opção 1** para ver seu primeiro resumo!

---

**Criado em:** 5 de Fevereiro de 2026  
**Status:** ✅ Pronto para usar  
**Tempo para começar:** ⏱️ 5 minutos  

Qualquer dúvida, veja `README_TOKEN_TRACKER.md` para documentação completa.
