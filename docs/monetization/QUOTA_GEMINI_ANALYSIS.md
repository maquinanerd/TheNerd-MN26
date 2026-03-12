# 📊 Status de Quotas Gemini Free Tier - Análise Completa

## 🚨 Alerta Crítico
**QUOTA DO FREE TIER FOI ULTRAPASSADA MÚLTIPLAS VEZES** — Sistema tem tratamento de 429 implementado e funciona, mas há histórico extenso de esgotamento.

---

## 📈 Histórico de Erros 429 (Quota Excedida)

### **Total Acumulado (Log Completo)**
- **Total de mensagens "You exceeded your current quota"**: 4.305 ocorrências
- **Período afetado**: 2025-08-14 até 2025-10-11

### **Distribuição por Data**
| Data | Erros 429 | Status | Notas |
|------|-----------|--------|-------|
| **2025-09-02** | 366 | 🔴 Crítico | Pior dia da história |
| **2025-09-11** | 479 | 🔴 Crítico | Recorde de erros |
| **2025-09-17** | 456 | 🔴 Crítico | 3º pior dia |
| **2025-09-09** | 333 | 🔴 Severo | Padrão de quota |
| **2025-09-10** | 219 | 🟠 Alto | Continuação |
| **2025-09-23** | 254 | 🟠 Alto | Retorno de problema |
| **2025-09-16** | 275 | 🟠 Alto | Persistente |
| **2025-10-30** | ✅ 0 | 🟢 Nenhum | **DIA ANALISADO** |
| **2025-10-31** | ? | 📊 TBD | Data atual |

### **Resumo por Período**
```
AGOSTO 2025:    752 erros (semana 1 inteira comprometida)
SETEMBRO 2025: 3.384 erros (mês CRÍTICO - 45 dias de quota)
OUTUBRO 2025:    169 erros (melhorando, mas ainda presente)
```

---

## 🎯 Status em 2025-10-30 (Dia Analisado)

| Métrica | Valor | Status |
|---------|-------|--------|
| **Erros 429 em 2025-10-30** | 0 | ✅ Perfeito |
| **Mensagens "You exceeded your current quota"** | 0 | ✅ Nenhuma |
| **Falhas de requisição relacionadas a quota** | 0 | ✅ Nenhuma |
| **Batches processados com sucesso** | 80/92 (87%) | ✅ Ótimo |
| **Artigos publicados** | ~344 | ✅ Completo |

**Conclusão**: **2025-10-30 foi um dia SEM problemas de quota** 🎉

---

## 🔍 Limites de Quota do Gemini Free Tier

### **Limites Atuais (Conforme Google Docs)**
```
Modelo: gemini-2.5-flash-lite (GRATUITO)

Taxa de Requisições:
├─ RPM (Requests Per Minute): 15 RPM
├─ Por dia: ~21.600 requisições
└─ Por mês: ~648.000 requisições

Tokens:
├─ TPM (Tokens Per Minute): 1.000.000 TPM
├─ RPD (Requests Per Day): 1.500 RPM
└─ Por dia: ~2.160.000.000 tokens

Limite de Entrada Simultânea:
└─ 1 requisição por vez (não suporta batch)
```

---

## 🛡️ Estratégia Implementada no Sistema

### **Rate Limiter (app/limiter.py)**
```python
# Intervalo MÍNIMO entre requisições
min_interval_s = 35.0 segundos

# = 1 requisição a cada 35 segundos
# = ~1.7 requisições por minuto
# = 103 requisições por hora
# = ~2.472 requisições por dia

# CONCLUSÃO: Está MUITO ABAIXO do limite de 15 RPM ✅
```

### **Estratégia de Fallback (app/ai_client_gemini.py)**
```python
# Quando 429 é detectado:
1. KeyPool rotaciona para próxima chave API
2. Penalidade de 30 segundos (+ jitter aleatório)
3. Retry automático com backoff exponencial
4. Máximo de 300 segundos de espera

# Múltiplas chaves:
GEMINI_ECONOMIA_*
GEMINI_POLITICA_*
GEMINI_CULTURA_*
GEMINI_DIVERSAO_*
... (TBD quantas exactas)
```

---

## 📉 Análise: Por Que Tivemos 429s em Setembro?

### **Hipóteses**
1. **Limite de Requisições Atingido**: 
   - Se sistema estava enviando >15 RPM = violação de quota
   
2. **Limite de Tokens Atingido**:
   - Se artigos eram muito longos = ultrapasse de TPM
   
3. **Limite de Requisições por Dia**:
   - Se >1.500 requisições/dia foram enviadas em batch

4. **Múltiplas Chaves Esgotadas Simultaneamente**:
   - Todas as chaves API atingiram limite no mesmo dia

### **Evidência do Sistema**
```
min_interval_s = 35.0
= 1 requisição / 35 segundos
= ~2.5 requisições / minuto (DENTRO do limite de 15 RPM)

MAS: Se o sistema tivesse 10+ chaves e rodava em paralelo,
     poderia ter atingido 25+ requisições/minuto = VIOLAÇÃO ✅
```

---

## ✅ Por Que 2025-10-30 Funcionou Bem?

1. **Sistema de Rate Limiting**: 35 segundos entre requisições
2. **Limite de 1.7 RPM**: Bem abaixo dos 15 RPM permitidos
3. **Múltiplas Chaves**: Distribuiu carga entre chaves temáticas
4. **Sem Picos**: Distribuição uniforme durante o dia
5. **Recovery Automático**: Quando 12 batches falharam (JSON), sistema não repetiu imediatamente

---

## 🔧 Configuração Atual de Quotas

### **Rate Limiter**
```python
# app/ai_processor.py (inferido do código)
min_interval_s = 35.0  # segundos entre requisições
```

### **Chaves Configuradas (Potencial)**
```
Número de chaves: DESCONHECIDO (necessário verificar .env)
Distribuição: Por tema (ECONOMIA, POLITICA, CULTURA, etc.)
Estratégia: Round-robin com rotação
```

### **Comportamento em 429**
```
- Detecta: ResourceExhausted exception
- Aguarda: 30 segundos (+ jitter)
- Tenta: Próxima chave do pool
- Máx backoff: 300 segundos
```

---

## ⚠️ Problemas Potenciais

### **1. Múltiplas Chaves Esgotadas Simultaneamente**
Se todas as chaves atingirem quota no mesmo dia:
```
Resultado: Sistema inteiro paralisa
Tempo para recuperação: ~24 horas (reset diário de quota)
```

### **2. Sem Limite Explícito de Tentativas**
```python
while True:  # Loop infinito!
    try:
        # requisição
    except 429:
        # retry forever
```
Risco: Se quota esgotada, sistema fica em loop de retry

### **3. Crescimento de Requisições Esperado**
Se em SETEMBRO tínhamos 3.384 erros/mês e agora está baixo:
- Possível: Redução de artigos processados
- Possível: Melhoria no rate limiter
- Possível: Sistema ficou sem fazer nada por período

---

## 📊 Recomendações

### **Imediato (Hoje)**
1. ✅ Verificar `.env` para contar exatamente quantas chaves GEMINI_* existem
2. ✅ Implementar logging de tentativas de retry (quantas vezes 429 ocorreu)
3. ✅ Adicionar circuit breaker: se 429 acontecer 5+ vezes em 1 hora, pausar por 1 hora

### **Curto Prazo (1 Semana)**
4. 🔑 **Upgrade para Paid Plan** (recomendado):
   - Free Tier: 15 RPM (~22K req/dia)
   - Paid Tier: 100 RPM (~144K req/dia)
   - Custo: $0.05/1K tokens input + $0.15/1K tokens output (Gemini 2.5 Flash)
   
5. 🔐 **Implementar Monitoramento**:
   - Dashboard de consumo de quota
   - Alertas quando atingir 80% do limite diário
   - Tracking de 429s em tempo real

### **Médio Prazo (2-4 Semanas)**
6. 🤖 **IA Secundária de Fallback**:
   - Adicionar OpenAI (GPT-4o mini — mais barato)
   - Ou Claude (Anthropic) com modelo pequeno
   - Estratégia: Quando Gemini quota = usar OpenAI
   
7. 🎯 **Rate Limiter Adaptativo**:
   - Começar com 1.7 RPM
   - Se 429 não ocorre por 24h → aumentar para 5 RPM
   - Se 429 ocorre → reduzir para 0.5 RPM

---

## 💡 Estimativa de Custo (Paid Plan)

### **Cenário: 344 artigos/dia (como em 2025-10-30)**

**Estimativa de Tokens por Artigo**:
- Input: 2.000 tokens (prompt + context)
- Output: 1.000 tokens (resposta)
- **Total: 3.000 tokens/artigo**

**Cálculo Diário**:
```
344 artigos/dia × 3.000 tokens/artigo = 1.032.000 tokens/dia

Input (2/3): 688.000 × $0.05/1K = $34.40/dia
Output (1/3): 344.000 × $0.15/1K = $51.60/dia
TOTAL: ~$86/dia (Paid Plan Gemini 2.5 Flash)

Free Tier: $0 (limite 1.500 req/dia ou ~450 artigos)
```

**Recomendação**: Upgrade para $86/dia economiza headaches de 429s

---

## 🎯 Conclusão: Status de Quotas

| Aspecto | Status | Detalhes |
|---------|--------|----------|
| **Quota em 2025-10-30** | ✅ Excelente | 0 erros 429 |
| **Histórico de Setembro** | 🔴 Crítico | 3.384 erros |
| **Taxa Atual** | ✅ Segura | 1.7 RPM << 15 RPM limite |
| **Proteção Implementada** | ✅ Sim | Rate limiter + retry automático |
| **Risco Futuro** | 🟡 Moderado | Crescimento pode exceder quota |
| **Recomendação** | 💰 Upgrade | Free tier é limitado para produção |

---

## 📋 Checklist para Ação

- [ ] Contar exatamente quantas chaves GEMINI_* estão configuradas
- [ ] Implementar logging de retry count por dia
- [ ] Adicionar circuit breaker para pausar após 5+ 429s
- [ ] Avaliar upgrade para Paid Plan ($86/dia)
- [ ] Adicionar IA de fallback (OpenAI/Claude)
- [ ] Implementar dashboard de monitoramento de quota
- [ ] Testar com 1.000+ requisições/dia para validar limite

---

**Data do Relatório**: 31 de outubro de 2025  
**Período Analisado**: 2025-08-14 até 2025-10-31  
**Recomendação**: Continue monitorando; considere upgrade para produção escalável
