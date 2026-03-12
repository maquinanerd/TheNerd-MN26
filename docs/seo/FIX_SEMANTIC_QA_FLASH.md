# FIX — semantic_qa_flash: AI_API_KEYS not defined

**Data:** 12/03/2026  
**Arquivo:** `app/pipeline.py`  
**Erro original:** `WARNING - pipeline - [QA-LLM] Falha na avaliação semântica: name 'AI_API_KEYS' is not defined`

---

## Causa Raiz

A função `semantic_qa_flash()` tentava usar `AI_API_KEYS[0]` para obter a chave da API, mas essa variável — apesar de estar definida em `app/config.py` — **não estava importada** no topo de `pipeline.py`.

Além disso, a função usava `google.generativeai`, biblioteca **deprecated** (FutureWarning no log), em vez de chamar a API REST do Gemini via `requests` como o restante do projeto.

---

## Alterações Aplicadas

### 1. Import em `pipeline.py` — bloco `from .config import ...`

**Adicionado:**
```python
AI_API_KEYS,
```

```python
# Antes
from .config import (
    PIPELINE_ORDER,
    RSS_FEEDS,
    WORDPRESS_CONFIG,
    WORDPRESS_CATEGORIES,
    CATEGORY_ALIASES,
    PIPELINE_CONFIG,
    SOURCE_CATEGORY_MAP,
)

# Depois
from .config import (
    PIPELINE_ORDER,
    RSS_FEEDS,
    WORDPRESS_CONFIG,
    WORDPRESS_CATEGORIES,
    CATEGORY_ALIASES,
    PIPELINE_CONFIG,
    SOURCE_CATEGORY_MAP,
    AI_API_KEYS,
)
```

---

### 2. Reescrita de `semantic_qa_flash()` — `app/pipeline.py`

| | Antes | Depois |
|---|---|---|
| Biblioteca | `google.generativeai` (deprecated) | `requests` (já no projeto) |
| Chave de API | `AI_API_KEYS[0]` (não importado → crash) | `AI_API_KEYS[0]` (importado de `.config`) |
| Modelo | `gemini-2.5-flash` | `gemini-2.5-flash-lite` (padrão do projeto via `AI_MODEL`) |
| Fallback seguro | mantido | mantido idêntico |
| Logs | mantidos | mantidos idênticos |

**Código corrigido:**
```python
def semantic_qa_flash(title: str, content_html: str) -> dict:
    import json as _json
    import requests as _requests

    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)[:2000]

    prompt = f"""Avalie em 4 critérios. Responda APENAS em JSON, sem explicação.
Título: {title}
Texto: {text}
Retorne exatamente:
{{
  "has_original_value": true,
  "has_cta_residual": false,
  "content_type": "news",
  "quality_note": "observação em uma linha"
}}
..."""

    try:
        if not AI_API_KEYS:
            raise ValueError("Nenhuma chave de API disponível")
        api_key = AI_API_KEYS[0]
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256},
        }
        resp = _requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return _json.loads(raw)
    except Exception as exc:
        logger.warning(f"[QA-LLM] Falha na avaliação semântica: {exc}")
        return {"has_original_value": True, "has_cta_residual": False,
                "content_type": "news", "quality_note": "erro_avaliação"}
```

---

## Comportamento esperado após o fix

```
[QA] Apple TV+ Imperfect Women estreia com 67% no Rotte | score=40 | 570w | h3=não | links_int=0 → NOINDEX (borderline)
[QA-LLM] type=news | original=True | cta=False | <quality_note>
```

Artigos borderline (score 35–49) agora passam corretamente pela Camada 2 sem lançar exceção.

---

## Notas operacionais

- `AI_API_KEYS[0]` utiliza sempre a **primeira chave** do pool (índice 0), sem passar pelo `RateLimiter`/`KeyPool`. Em pipelines com alto volume de RPM, o `try/except` interno captura um eventual 429 e aciona o fallback seguro — o artigo nunca é bloqueado.
- O modelo `gemini-2.5-flash-lite` corresponde ao `AI_MODEL` padrão definido em `config.py`.
