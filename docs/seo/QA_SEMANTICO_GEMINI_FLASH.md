# 17 — QA Semântico · Camada 2 via Gemini 2.5 Flash

**Implementado em:** 12/03/2026  
**Arquivo alterado:** `app/pipeline.py`  
**Função adicionada:** `semantic_qa_flash(title, content_html)`  
**Custo adicional:** ~$0,24/mês

---

## 1. Por que isso foi necessário

A Camada 1 (Python puro) avalia estrutura: conta palavras, verifica H3, conta links internos.  
Ela **não consegue detectar**:

- CTA residual da fonte (frases promocionais que sobrevivem à limpeza por estarem "camufladas")
- Se o texto tem valor informacional único ou é repasse genérico
- Tipo do conteúdo: notícia quente vs. análise vs. guia atemporal (evergreen)
- Erros de tradução ou incoerência editorial

Para artigos com score borderline (35–50) — que a Camada 1 manda para NOINDEX mas que **poderiam** ser indexados — a avaliação semântica decide com mais precisão.

---

## 2. Custo real

| Métrica | Valor |
|---|---|
| Modelo | `gemini-2.5-flash` |
| Preço por 1M tokens (input) | ~$0,15 |
| Tokens por avaliação | ~800 (prompt + trecho) |
| Custo por artigo avaliado | ~$0,0001 |
| Artigos borderline/dia | ~3–5 (estimado) |
| **Custo mensal** | **~$0,24** |
| Latência extra | +0,5–1,5s (apenas nos borderline) |

A Camada 2 **não roda para todos os artigos** — apenas para score 35–50. Artigos com score >= 50 já vão para INDEX pela Camada 1. Artigos com score < 35 vão direto para NOINDEX sem custo adicional.

---

## 3. Quando cada camada é usada

| Camada | Ferramenta | Custo | Quando roda | O que avalia |
|---|---|---|---|---|
| 1 (sempre) | Python puro | $0 | Todo artigo | Palavras, H3, links, "Nossa Análise" |
| 2 (opcional) | Gemini 2.5 Flash | ~$0,24/mês | Score 35–50 | CTA residual, valor semântico, tipo |

---

## 4. Função `semantic_qa_flash()`

**Localização:** `app/pipeline.py`, imediatamente antes de `_get_article_url()`.

### Input

```python
semantic_qa_flash(title: str, content_html: str) -> dict
```

- `title`: título final do artigo
- `content_html`: HTML completo do conteúdo (extrai os primeiros 2.000 chars de texto)

### Output

```python
{
    "has_original_value": True,        # texto tem informação factual única
    "has_cta_residual": False,         # nenhum CTA residual detectado
    "content_type": "analysis",        # "news" | "analysis" | "evergreen"
    "quality_note": "análise aprofundada sobre Frank Castle no MCU"
}
```

### Comportamento em caso de erro

Se a chamada ao Gemini falhar (timeout, JSON inválido, quota), retorna fallback seguro:
```python
{"has_original_value": True, "has_cta_residual": False,
 "content_type": "news", "quality_note": "erro_avaliação"}
```
O artigo **não é bloqueado** — continua com a decisão da Camada 1.

---

## 5. Lógica de decisão no pipeline

```python
# Camada 1 — sempre
quality = assess_content_quality(content_html)
noindex_value = "0" if quality["should_index"] else "1"

# Camada 2 — apenas borderline
if 35 <= quality["score"] < 50:
    qa2 = semantic_qa_flash(title, content_html)

    if qa2["has_cta_residual"]:
        # log warning — CTA não removido pela limpeza automática
        logger.warning(f"[QA-LLM] CTA residual: {title[:50]}")

    if qa2["content_type"] == "evergreen" and qa2["has_original_value"]:
        noindex_value = "0"   # forçar INDEX para evergreen com valor

    elif not qa2["has_original_value"]:
        noindex_value = "1"   # confirmar NOINDEX para texto sem valor original
```

### Tabela de decisão final

| Score Camada 1 | Resultado Camada 1 | Condição Camada 2 | Resultado Final |
|---|---|---|---|
| >= 50 | INDEX | não roda | INDEX |
| 35–49 | NOINDEX | evergreen + original | **INDEX** |
| 35–49 | NOINDEX | sem valor original | NOINDEX |
| 35–49 | NOINDEX | news/analysis com valor | NOINDEX (mantém) |
| < 35 | NOINDEX | não roda | NOINDEX |

---

## 6. Integração técnica

A função usa `AI_API_KEYS[0]` (primeira chave do pool carregado pelo `config.py`) com `genai.configure()` direto — sem passar pelo `RateLimiter` ou `KeyPool` do pipeline principal, pois é uma chamada pontual e isolada.

O modelo chamado é `gemini-2.5-flash` (não o `gemini-2.5-flash-lite` do pipeline) — a diferença semântica justifica o modelo mais capaz para esta avaliação qualitativa.

> **Nota (429):** Por não passar pelo `RateLimiter`/`KeyPool`, se o pipeline estiver no limite de RPM no momento da chamada, ela pode retornar erro 429. O `try/except` existente na função já captura isso e aciona o fallback seguro — nenhuma ação adicional é necessária. Se o problema for recorrente, basta mover a chamada para dentro do `KeyPool` existente.

---

## 7. Logs esperados

**Artigo score=40 que é evergreen:**
```
[QA] Punisher: Personagem tem futuro no MCU...  | score=40 | 802w | h3=não | links_int=0 → NOINDEX
[QA-LLM] type=evergreen | original=True | cta=False | guia sobre o futuro do personagem no MCU
[QA-LLM] Forçando INDEX por tipo evergreen: Punisher: Personagem tem futuro no MCU
```

**Artigo score=35 com CTA residual:**
```
[QA] Série X ganha trailer...  | score=35 | 450w | h3=não | links_int=0 → NOINDEX
[QA-LLM] type=news | original=True | cta=True | texto contém "don't forget to subscribe"
[QA-LLM] CTA residual detectado: Série X ganha trailer...
```

**Artigo score=40 sem valor original:**
```
[QA] Lista genérica de séries...  | score=40 | 820w | h3=não | links_int=0 → NOINDEX
[QA-LLM] type=news | original=False | cta=False | repasse genérico sem dado exclusivo
[QA-LLM] Confirmando NOINDEX sem valor original: Lista genérica de séries...
```

---

## 8. Verificação após restart

```powershell
Get-Content logs\app.log | Where-Object { $_ -match "\[QA-LLM\]" }
```

---

## 9. Personalização futura

- **Ampliar faixa borderline:** mudar `35 <= quality["score"] < 50` para `30 <= quality["score"] < 55`
- **Desativar temporariamente:** comentar o bloco `if 35 <= quality["score"] < 50:` — sem impacto no restante do pipeline
- **Adicionar critérios:** editar o prompt dentro de `semantic_qa_flash()` — o JSON de saída pode ser estendido com novos campos
- **Trocar modelo:** substituir `"gemini-2.5-flash"` por `"gemini-2.5-flash-lite"` para reduzir custo pela metade (menor precisão semântica)
