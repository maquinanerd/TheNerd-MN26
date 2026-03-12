# 🎯 COMO USAR O SISTEMA DE TOKENS AGORA

## ✅ O Sistema Está Integrado

Todos os posts que forem processados **automaticamente registrarão seus tokens REAIS**.

Você não precisa fazer nada - a captura ocorre transparentemente.

## 📊 Ver os Dados de Tokens

### Opção 1: Dashboard Interativo (RECOMENDADO)
```bash
python token_logs_viewer.py
```

Oferece 5 opções:
1. **Resumo de Hoje** - tokens entrada/saída de hoje
2. **Por API/Modelo** - dados agrupados por modelo Gemini
3. **Logs Recentes** - últimos 10 registros detalhados
4. **Comparação** - compara períodos (hoje vs semana passada, etc)
5. **Exportar CSV** - salva em arquivo Excel/Calc

### Opção 2: Ver arquivos raw
```bash
# Ver o log de hoje (JSONL - uma entrada por linha)
cat logs/tokens/tokens_2026-02-05.jsonl

# Ver estatísticas consolidadas
cat logs/tokens/stats.json
```

## 📈 Entender os Dados

### Arquivo JSONL Diário: `logs/tokens/tokens_YYYY-MM-DD.jsonl`

Cada linha é um registro JSON:
```json
{
  "timestamp": "2026-02-05T12:01:47.125481",
  "prompt_tokens": 150,
  "completion_tokens": 320,
  "total_tokens": 470,
  "api": "gemini",
  "model": "gemini-2.5-flash-lite",
  "metadata": {
    "batch_size": 1,
    "operation": "batch_rewrite"
  },
  "status": "success"
}
```

**O que significa:**
- `prompt_tokens` = Tokens de ENTRADA (seu prompt para a IA)
- `completion_tokens` = Tokens de SAÍDA (resposta da IA)
- `total_tokens` = Soma dos dois
- `operation` = Tipo: `batch_rewrite` (vários posts) ou `single_rewrite` (um post)

### Arquivo Stats: `logs/tokens/stats.json`

Consolidação dos últimos 7 dias:
```json
{
  "date_range": "2026-01-30 to 2026-02-05",
  "total_requests": 8,
  "successful_requests": 8,
  "failed_requests": 0,
  "total_prompt_tokens": 1200,
  "total_completion_tokens": 2540,
  "total_tokens": 3740,
  "average_tokens_per_request": 468,
  "by_model": {
    "gemini-2.5-flash-lite": {
      "requests": 8,
      "prompt_tokens": 1200,
      "completion_tokens": 2540
    }
  }
}
```

## 💰 Calcular Custo

### Precificação Gemini (Confira valores atuais no console Google Cloud)

Exemplo (valores 2026):
- **gemini-2.5-flash**: $0.075 por 1M entrada | $0.30 por 1M saída
- **gemini-2.5-flash-lite**: $0.0375 por 1M entrada | $0.15 por 1M saída

**Cálculo:**
```
Entrada: 1.200 tokens × ($0.0375 / 1.000.000) = $0.000045
Saída: 2.540 tokens × ($0.15 / 1.000.000) = $0.000381
Total: $0.000426 para processar ~2 posts
```

Por mês (assumindo 60 posts):
```
60 posts × $0.000426 ≈ $0.026 USD/mês
```

## 🔄 Fluxo Completo

```
1. Post processado pelo pipeline
   ↓
2. ai_processor.py chama ai_client_gemini.py
   ↓
3. API Gemini retorna resposta + usage_metadata
   ↓
4. tokens_info extraído: {prompt_tokens: 150, completion_tokens: 320}
   ↓
5. log_tokens() chamado automaticamente
   ↓
6. Dados salvos em:
   - logs/tokens/tokens_2026-02-05.jsonl (entrada diária)
   - logs/tokens/stats.json (consolidação)
```

## 🔍 Troubleshooting

### "Não vejo dados novos em logs/tokens/"

1. Verifique se há posts sendo processados:
```bash
# Se há arquivos novos em debug/ai_response_batch_*.json
Get-ChildItem debug/ai_response_batch*.json -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

2. Confirme integração está ok:
```bash
python test_token_integration.py
```

3. Verifique logs da aplicação principal:
```bash
tail -f app.log  # ou o arquivo de log que sua app usa
```

### Stats.json não atualiza

- Só atualiza quando há dados novos
- Se houver apenas 1 entrada de log, ainda não cria stats
- Execute vários posts para gerar dados agregados

## 📝 Exemplo Real

Processando um post sobre filme:
```
Entrada: 312 tokens (seu prompt completo)
Saída: 645 tokens (resposta HTML + metadata)
Total: 957 tokens

Custo: 957 tokens × taxa média ≈ $0.00024
```

Para 5 posts similares/dia:
```
5 × 957 = 4.785 tokens/dia
≈ $0.0012/dia
≈ $0.036/mês
```

## 🎯 Próximos Passos Recomendados

1. **Processe alguns posts** com o pipeline normal
2. **Execute o dashboard**: `python token_logs_viewer.py`
3. **Exporte dados**: Escolha opção 5 para CSV
4. **Analise padrões**: Qual tipo de post usa mais tokens?
5. **Otimize se necessário**: Instruções mais concisas reduzem tokens

---

**Tudo automático agora! ✅**

Toda vez que um post é processado, seus tokens são registrados.
