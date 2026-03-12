# 📇 ÍNDICE DO SISTEMA DE LOG DE TOKENS

## 🎯 REFERÊNCIA RÁPIDA

**Data de criação:** 5 de Fevereiro de 2026  
**Status:** ✅ Completo, testado e pronto para usar  
**Versão:** 1.0  

---

## 📌 COMECE AQUI

1. **Leia primeiro:** [GUIA_RAPIDO_TOKENS.md](GUIA_RAPIDO_TOKENS.md) (5 min)
2. **Execute:** `python example_token_tracker.py` (1 min)
3. **Visualize:** `python token_logs_viewer.py` (2 min)

---

## 📚 DOCUMENTAÇÃO

| Arquivo | Descrição | Tempo |
|---------|-----------|-------|
| [GUIA_RAPIDO_TOKENS.md](GUIA_RAPIDO_TOKENS.md) | 👈 **COMECE AQUI** - Início rápido em 3 passos | 5 min |
| [README_TOKEN_TRACKER.md](README_TOKEN_TRACKER.md) | Documentação completa e detalhada | 15 min |
| [IMPLEMENTACAO_TOKEN_TRACKER.py](IMPLEMENTACAO_TOKEN_TRACKER.py) | Guia técnico de integração | 20 min |
| [RESUMO_SISTEMA_TOKENS.md](RESUMO_SISTEMA_TOKENS.md) | Visão geral e próximas etapas | 10 min |
| [ARQUIVO_CRIACAO_SISTEMA_TOKENS.md](ARQUIVO_CRIACAO_SISTEMA_TOKENS.md) | Resumo do que foi criado | 10 min |
| [RESUMO_EXECUTIVO_TOKENS.py](RESUMO_EXECUTIVO_TOKENS.py) | Resumo visual (execute: `python RESUMO_EXECUTIVO_TOKENS.py`) | 2 min |

---

## 💻 CÓDIGO PYTHON

| Arquivo | Descrição | Tamanho |
|---------|-----------|---------|
| [app/token_tracker.py](app/token_tracker.py) | ⭐ Módulo principal de rastreamento | 10.8 KB |
| [token_logs_viewer.py](token_logs_viewer.py) | 📊 Dashboard interativo em terminal | 12.9 KB |
| [example_token_tracker.py](example_token_tracker.py) | 🎓 Exemplos de uso (testados ✅) | 3.0 KB |
| [test_token_tracker.py](test_token_tracker.py) | 🧪 Suite de 8 testes | 8.7 KB |

---

## 🚀 EXECUTAR AGORA

### 1. Testar (criar logs de teste)
```bash
python example_token_tracker.py
```

### 2. Visualizar dados
```bash
python token_logs_viewer.py
```

### 3. Executar testes
```bash
python test_token_tracker.py
```

### 4. Ver resumo
```bash
python RESUMO_EXECUTIVO_TOKENS.py
```

---

## 📂 ARQUIVOS GERADOS

### Diretório de logs
```
logs/tokens/
├── tokens_2025-02-05.jsonl         ← Logs diários (JSONL)
├── token_stats.json                ← Estatísticas consolidadas
└── token_debug.log                 ← Debug log
```

---

## 🔧 INTEGRAÇÃO (4 LINHAS)

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

## 📊 O QUE RASTREIA

| Item | Descrição |
|------|-----------|
| 📥 **Entrada** | Tokens dos prompts (perguntas) |
| 📤 **Saída** | Tokens das respostas |
| ✅ **Total** | Entrada + Saída |
| 📋 **Requisições** | Contagem de chamadas |
| ✔️ **Sucesso** | Requisições bem-sucedidas |
| ❌ **Falhas** | Requisições que falharam |
| 🔌 **API** | Tipo de API (Gemini, OpenAI, etc) |
| 🤖 **Modelo** | Qual modelo foi usado |
| 📎 **Metadata** | Dados adicionais customizáveis |

---

## 🎯 FUNCIONALIDADES

### Rastreamento
- ✅ Prompts (entrada)
- ✅ Respostas (saída)
- ✅ Múltiplas APIs
- ✅ Múltiplos modelos
- ✅ Sucesso/Falha
- ✅ Metadados

### Visualização
- ✅ Resumo geral
- ✅ Breakdown por API
- ✅ Breakdown por modelo
- ✅ Últimos logs
- ✅ Comparação diária
- ✅ Exportação CSV

### Segurança
- ✅ Apenas 4 últimos caracteres da chave
- ✅ Sem armazenar conteúdo
- ✅ Logs locais
- ✅ Sem envio de dados

---

## 💡 EXEMPLOS RÁPIDOS

### Básico
```python
from app.token_tracker import log_tokens
log_tokens(100, 200)
```

### Com detalhes
```python
log_tokens(
    prompt_tokens=100,
    completion_tokens=200,
    model="gemini-2.5-flash",
    success=True
)
```

### Com erro
```python
log_tokens(
    prompt_tokens=0,
    completion_tokens=0,
    success=False,
    error_message="429 Quota excedida"
)
```

### Com metadata
```python
log_tokens(
    prompt_tokens=100,
    completion_tokens=200,
    metadata={
        "article_id": 123,
        "category": "tech",
        "time_ms": 2450
    }
)
```

---

## 📈 ANÁLISES POSSÍVEIS

### Custo
```
Entrada: 100 tokens × $0.075 = $0.0075
Saída:   200 tokens × $0.30  = $0.06
Total:                        $0.0675
```

### Eficiência
```
Entrada/Saída ratio = 100/200 = 0.5
(quanto menor, mais eficiente)
```

### Taxa de Sucesso
```
3 sucesso / 4 total = 75%
(detecte problemas com chaves)
```

### Uso por modelo
```
flash:      450 entrada, 770 saída
lite:       250 entrada, 500 saída
(compare custos e qualidade)
```

---

## 🎓 CHECKLIST

- [ ] Li GUIA_RAPIDO_TOKENS.md
- [ ] Executei example_token_tracker.py
- [ ] Explorei token_logs_viewer.py
- [ ] Entendi a estrutura dos dados
- [ ] Integrei ao meu código
- [ ] Testei com dados reais
- [ ] Monitoro via dashboard

---

## 🐛 TROUBLESHOOTING

### Erro: "ModuleNotFoundError"
```bash
python -c "from app.token_tracker import log_tokens; print('OK')"
```

### Logs não aparecem
```bash
ls -la logs/tokens/
cat logs/tokens/token_debug.log
```

### Stats não atualiza
```bash
rm logs/tokens/token_stats.json
python example_token_tracker.py  # Recria
```

---

## 🔗 ESTRUTURA DE DADOS

### JSONL (tokens_YYYY-MM-DD.jsonl)
Uma linha = uma requisição
```json
{
  "timestamp": "2025-02-05T12:01:47.127728",
  "api_type": "gemini",
  "model": "gemini-2.5-flash",
  "api_key_suffix": "****abc1",
  "prompt_tokens": 150,
  "completion_tokens": 320,
  "total_tokens": 470,
  "success": true,
  "error_message": null,
  "metadata": {}
}
```

### JSON (token_stats.json)
Estatísticas consolidadas
```json
{
  "gemini": {
    "gemini-2.5-flash": {
      "total_prompt_tokens": 450,
      "total_completion_tokens": 770,
      "total_tokens": 1220,
      "total_requests": 3,
      "successful_requests": 2,
      "failed_requests": 1,
      "last_updated": "2026-02-05T12:01:47.127728"
    }
  }
}
```

---

## 🎯 DASHBOARD (python token_logs_viewer.py)

Menu com 5 opções:
```
1. 📊 Resumo Geral
2. 🔌 Detalhamento por API
3. 🕐 Últimos Logs
4. 📈 Comparação Diária
5. 📥 Exportar CSV
0. ❌ Sair
```

---

## 📊 EXEMPLO DE SAÍDA

```
📥 Tokens de Entrada: 700
📤 Tokens de Saída: 1.270
✅ Total: 1.970
📋 Requisições: 4
✔️  Sucesso: 3
❌ Falhas: 1
📈 Taxa: 75%
```

---

## 🚀 PRÓXIMAS AÇÕES

### Hoje
1. Ler: GUIA_RAPIDO_TOKENS.md
2. Executar: python example_token_tracker.py
3. Explorar: python token_logs_viewer.py

### Esta semana
4. Integrar ao seu código
5. Testar com dados reais
6. Verificar logs

### Contínuo
7. Monitorar via dashboard
8. Analisar padrões
9. Otimizar baseado em dados

---

## 📞 REFERÊNCIA RÁPIDA

```python
# Importar
from app.token_tracker import log_tokens, get_tracker

# Registrar simples
log_tokens(entrada, saída)

# Registrar com detalhes
log_tokens(entrada, saída, api_type="gemini", model="flash")

# Obter tracker
tracker = get_tracker()
tracker.print_summary()
stats = tracker.get_summary()
```

---

## ✨ STATUS

| Componente | Status |
|-----------|--------|
| Módulo | ✅ Criado |
| Dashboard | ✅ Funcionando |
| Exemplos | ✅ Testados |
| Documentação | ✅ Completa |
| Testes | ✅ Passando |

---

## 📚 DOCUMENTOS

```
COMECE AQUI:
  👈 GUIA_RAPIDO_TOKENS.md

DOCUMENTAÇÃO COMPLETA:
  📖 README_TOKEN_TRACKER.md

GUIAS TÉCNICOS:
  🔧 IMPLEMENTACAO_TOKEN_TRACKER.py
  📊 RESUMO_SISTEMA_TOKENS.md
  📇 ARQUIVO_CRIACAO_SISTEMA_TOKENS.md
  📋 RESUMO_EXECUTIVO_TOKENS.py
```

---

## 🎉 VAMOS COMEÇAR!

Próximo comando:
```bash
python example_token_tracker.py
```

Depois:
```bash
python token_logs_viewer.py
```

Escolha opção **1** para ver seu primeiro resumo!

---

**Versão:** 1.0  
**Data:** 5 de Fevereiro de 2026  
**Status:** ✅ Pronto para usar  

Qualquer dúvida? Veja [GUIA_RAPIDO_TOKENS.md](GUIA_RAPIDO_TOKENS.md)
