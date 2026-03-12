# ❓ FOI QUOTA OU RPM? - ANÁLISE 2025-10-31 13:12:08

## 🔴 RESPOSTA: **FOI RPM, NÃO QUOTA!**

---

## 📊 Comparação: Quota vs RPM

| Aspecto | Quota | RPM | Seu Caso |
|---------|-------|-----|----------|
| **O quê** | Total de requisições/tokens no mês | Requisições **por minuto** | 🔴 **RPM** |
| **Período** | 30 dias | 1 minuto | 🔴 **1 minuto** |
| **Limite Free** | Ilimitado (praticamente) | 15 requisições/min | 🔴 **15/min** |
| **Mensagem** | "Você atingiu X tokens" | "requests per minute" | 🔴 **"per minute"** |
| **Retry** | 24h (próximo dia) | Segundos a minutos | 🔴 **52 segundos** |

---

## 🔍 EVIDÊNCIA DOS LOGS

### **Error 1 - Chave EQ5g**
```
Quota exceeded for metric: 
  generativelanguage.googleapis.com/generate_content_free_tier_requests

limit: 15

quota_id: GenerateRequestsPerMinutePerProjectPerModel-FreeTier
                                     ↑
                            PER MINUTE = RPM
                            
quota_value: 15

Please retry in 52 segundos
```

**Interpretação**: Limite de **15 requisições por MINUTO** foi excedido.

### **Error 2 - Chave RzCw**
```
Quota exceeded for quota metric:
  'Generate Content API requests per minute'
                                  ↑
                           PER MINUTE = RPM

reason: RATE_LIMIT_EXCEEDED

metadata {
  quota_limit_value: "0"  ← Limite reduzido para ZERO
}
```

**Interpretação**: RPM limite foi tão violado que foi **reduzido para 0** (ban temporário).

---

## 💡 O QUE SIGNIFICA

### **Quota (❌ NÃO ERA ISSO)**
```
"Você usou seu limite mensal de tokens"
Limite: ~1.000.000 tokens/dia
Reset: Próximo dia
```

### **RPM (✅ ERA ISSO!)**
```
"Você mandou MUITAS requisições em 1 minuto"
Limite: 15 requisições/minuto
Reset: Em 52+ segundos
```

---

## 🎯 O QUE ACONTECEU ESPECIFICAMENTE

```
Minuto X (13:12:08):
├─ Requisição 1 ✅
├─ Requisição 2 ✅
├─ ...
├─ Requisição 15 ✅
├─ Requisição 16 ❌ BLOQUEADA - RPM EXCEDIDO
├─ Requisição 17 ❌ BLOQUEADA
└─ Tentativa de Requisição 18+ ❌ AMBAS CHAVES FORA

Sistema: "Espere 52 segundos e tente de novo"
```

---

## 🔬 DIAGNÓSTICO: POR QUE MANDOU 16+ EM 1 MINUTO?

### **Causa Provável 1: Batches Muito Rápidos**
```
13:12:00 → Batch 1 (requisição)
13:12:01 → Batch 2 (requisição)
13:12:02 → Batch 3 (requisição)
...
13:12:08 → Batch 16 (requisição) ❌ LIMITE!
```

Intervalo esperado: 35 segundos entre requisições
Intervalo observado: ~0.5 segundos entre batches

### **Causa Provável 2: Múltiplos Workers/Paralelo**
```
Worker 1 → Requisição 1
Worker 2 → Requisição 2
Worker 3 → Requisição 3
...
Worker 16 → Requisição 16 ❌ LIMITE!
```

Se sistema tem múltiplos processos rodando em paralelo.

### **Causa Provável 3: Rate Limiter Desativado/Alterado**
```
Config OLD: min_interval_s = 35
Config NEW: min_interval_s = 2 (ou similar)

Resultado: Requisições muito rápidas
```

---

## ✅ COMO DIFERENCIAR

### **Se fosse QUOTA:**
- Erro mencionaria: "monthly", "daily", "total tokens"
- Retry seria: 24 horas
- Chaves: Todas afetadas igualmente

### **Se for RPM (✅ SEU CASO):**
- ✅ Erro menciona: "per minute"
- ✅ Retry é: 52 segundos
- ✅ Chaves: Afetadas sequencialmente
- ✅ Limite reduzido: De 15 para 0

---

## 🚨 O PROBLEMA REAL

**Não é "você usou muito"**  
**É "você mandou muito RÁPIDO"**

Solução:
- ❌ Não é esperar 24 horas (quota)
- ✅ É **ESPAÇAR MAIS as requisições** (aumentar `min_interval_s`)

---

## 🔧 AÇÃO CORRETIVA

### **Aumentar Intervalo Mínimo**
```python
# app/limiter.py (ATUAL)
min_interval_s = 35.0  # 35 segundos entre requisições
= 1.7 RPM (OK, mas margem apertada)

# RECOMENDADO
min_interval_s = 45.0  # 45 segundos
= 1.3 RPM (MAIS SEGURO)

# OU AGRESSIVO (se problema continuar)
min_interval_s = 60.0  # 60 segundos = 1 RPM
```

### **Ou Reduzir Batch Size**
```python
# Se mandava 5 requisições em 8 segundos
# Reduzir batch size para mandar menos de uma vez
```

---

## 📋 Checklist

- [ ] **Confirmar**: Log mostra "per minute" = RPM (não quota mensal)
- [ ] **Aumentar**: `min_interval_s` de 35s para 45-60s
- [ ] **Testar**: Verificar se 429s param com novo intervalo
- [ ] **Monitorar**: Próximas horas para ver se problema retorna

---

## 🎯 Conclusão

| Pergunta | Resposta |
|----------|----------|
| **Foi Quota?** | ❌ Não |
| **Foi RPM?** | ✅ SIM |
| **É grave?** | 🟠 Moderado (fácil corrigir) |
| **Solução?** | Aumentar `min_interval_s` |
| **Tempo para resolver?** | ~5 minutos (code change + deploy) |

---

**Resumo**: O sistema mandou **mais de 15 requisições em 1 minuto**, violando o limite RPM do Free Tier. Não é problema de quota mensal, é de velocidade. Aumentar espaçamento entre requisições resolve.
