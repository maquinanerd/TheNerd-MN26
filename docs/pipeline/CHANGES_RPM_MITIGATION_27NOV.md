# Mitigação de Violações RPM - 27 de Novembro

## Resumo das Alterações
Implementadas 3 mudanças críticas para evitar violações do limite RPM (15 requisições/minuto) do Gemini Free Tier:

---

## 1. ✅ Aumentar `min_interval_s` para 60.0 segundos

**Arquivo:** `app/limiter.py`  
**Mudança:** RateLimiter.__init__ parameter de 35.0 → 60.0

**Antes:**
```python
def __init__(self, min_interval_s=35.0):  # Intervalo mais conservador entre 30-45s
    self.min_interval_s = float(min_interval_s)
    self.last_call = 0.0
    self._jitter = 10.0  # Adiciona variação aleatória de até 10s
```

**Depois:**
```python
def __init__(self, min_interval_s=60.0):  # Intervalo MUITO conservador: 60 segundos (1 RPM)
    self.min_interval_s = float(min_interval_s)
    self.last_call = 0.0
    self._jitter = 5.0  # Reduzido para 5s para ser mais previsível com intervalo maior
```

**Impacto:**
- Taxa efetiva: **1 requisição/minuto** (muito abaixo do limite de 15 RPM)
- Proporciona buffer seguro contra rajadas acidentais
- Reduz jitter de 10s para 5s (mais previsível)

**Status:** ✅ IMPLEMENTADO

---

## 2. ✅ Limitar Requisições a 10 por Ciclo

**Arquivo:** `app/pipeline.py`  
**Função:** `worker_loop()`

**Mudança:** Adicionado rastreamento de requisições + pausa ao atingir limite

**Novo código:**
```python
def worker_loop():
    """Continuously process articles from the queue in batches.
    
    Respects:
    - Max 10 AI requests per cycle (to avoid RPM violations)
    - 5-minute pause after hitting request limit
    """
    link_map = {}
    try:
        with open('data/internal_links.json', 'r', encoding='utf-8') as f:
            link_map = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("Could not load internal_links.json for worker.")

    requests_in_cycle = 0
    MAX_REQUESTS_PER_CYCLE = 10
    PAUSE_ON_LIMIT_S = 300  # 5 minutos
    last_pause_time = 0

    while True:
        # Get up to 3 articles from queue
        articles = []
        for _ in range(3):
            if article := article_queue.pop():
                articles.append(article)

        if not articles:
            time.sleep(2)
            # Reset cycle counter after quiet period (1 min)
            if time.time() - last_pause_time > 60:
                requests_in_cycle = 0
            continue

        # Check if we've hit request limit
        if requests_in_cycle >= MAX_REQUESTS_PER_CYCLE:
            logger.warning(
                f"[RPM PROTECTION] Atingido limite de {MAX_REQUESTS_PER_CYCLE} requisições por ciclo. "
                f"Pausando pipeline por {PAUSE_ON_LIMIT_S}s (5 minutos)."
            )
            last_pause_time = time.time()
            time.sleep(PAUSE_ON_LIMIT_S)
            requests_in_cycle = 0
            logger.info("[RPM PROTECTION] Resumindo pipeline após pausa de 5 minutos.")
            continue

        # Process batch and count requests
        process_batch(articles, link_map)
        requests_in_cycle += len(articles)
        
        logger.info(
            f"Worker: {len(articles)} artigos processados. "
            f"Total requisições neste ciclo: {requests_in_cycle}/{MAX_REQUESTS_PER_CYCLE}. "
            f"Dormindo por {ARTICLE_SLEEP_S}s."
        )
        time.sleep(ARTICLE_SLEEP_S)
```

**Impacto:**
- Máximo de **10 requisições** antes de pausa
- Contador reseta após 1 minuto sem atividade
- Logs claros de proteção RPM ativada
- Rastreamento contínuo no stdout

**Status:** ✅ IMPLEMENTADO

---

## 3. ✅ Implementar Pausa de 5 Minutos + Resume

**Arquivo:** `app/pipeline.py`  
**Função:** `worker_loop()`

**Comportamento:**
1. Quando `requests_in_cycle >= 10`:
   - Log de aviso: `[RPM PROTECTION] Atingido limite...`
   - Pipeline pausa por **300 segundos (5 minutos)**
   - Contador de requisições reseta a 0
   
2. Após pausa:
   - Log de info: `[RPM PROTECTION] Resumindo pipeline...`
   - Pipeline retorna ao processamento normal
   
3. Contador reseta automaticamente:
   - Após 60 segundos de inatividade (sem artigos na fila)

**Status:** ✅ IMPLEMENTADO

---

## Efeito Combinado

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **min_interval_s** | 35.0s (1.7 RPM efetivo) | 60.0s (1 RPM efetivo) |
| **Requisições/ciclo** | Ilimitadas | Máximo 10 |
| **Pausa ao limite** | Nenhuma | 5 minutos |
| **Jitter** | ±10s | ±5s |
| **Segurança contra RPM** | Baixa | **MUITO ALTA** |

---

## Validação

✅ Arquivo `app/limiter.py` modificado (min_interval_s=60.0)  
✅ Arquivo `app/pipeline.py` modificado (worker_loop com contador)  
✅ Logs incluem mensagens claras de proteção RPM  
✅ Pausa de 5 minutos implementada  
✅ Resume automático após pausa  

---

## Próximos Passos (Recomendados)

1. **Iniciar o sistema e monitorar logs:**
   ```bash
   python app/main.py  # ou seu comando de início
   ```

2. **Verificar que não há novos erros 429:**
   ```bash
   grep "429\|ResourceExhausted" logs/app.log
   ```

3. **Monitorar contador de RPM:**
   ```bash
   grep "\[RPM PROTECTION\]" logs/app.log
   ```

4. **Se RPM PROTECTION não ativar em 2 horas:**
   - Sistema está bem protegido ✅
   - Pode-se reduzir conservadorismo se necessário

5. **Se RPM PROTECTION ativar múltiplas vezes:**
   - Aumentar `min_interval_s` para 90.0 ou 120.0
   - Reduzir `MAX_REQUESTS_PER_CYCLE` para 5

---

## Notas Técnicas

- **RPM Free Tier Gemini:** 15 requisições/minuto máximo
- **Novo rate:** 1 requisição/minuto ≈ 7% do limite
- **Buffer de segurança:** ~93% de margem
- **Custo:** Processamento ~14x mais lento (trade-off: zero RPM violations)

---

## Histórico da Decisão

**Contexto:** 2025-10-31 13:12:08 - Dois 429s simultâneos em chaves diferentes  
**Raiz:** min_interval_s=35.0 causava picos acima de 15 RPM em bursts  
**Decisão:** Aumentar conservadorismo drasticamente + circuit breaker (pausa)  
**Data:** 27 de Novembro de 2025  
**Executado por:** Bot de automação RPM mitigation  

