# Crawl Budget — Quality Score & Lógica noindex

**Implementado em:** 12/03/2026  
**Arquivos alterados:** `app/pipeline.py`, `app/wordpress.py`  
**Commits relacionados:** Quality Score + noindex automático via Yoast SEO

---

## 1. Por que isso existe

### O problema real: Crawl Budget

O Google não indexa tudo. Todo site tem um **crawl budget** — um número limitado de páginas que o Googlebot visita e indexa por dia. Para o maquinanerd.com.br isso importa porque:

- O pipeline publica múltiplos artigos por dia automaticamente.
- Artigos curtos, sem estrutura, sem links internos **desperdiçam crawl budget**.
- Quando o bot gasta tempo em conteúdo ruim, ele visita menos as páginas boas.
- O resultado: páginas evergreen importantes (Batman Timeline, reviews aprofundados) levam mais tempo para aparecer no Google.

### A solução: triagem antes de publicar

Em vez de publicar tudo e deixar o Google decidir, o pipeline agora **avalia a qualidade do conteúdo** antes de enviar para o WordPress e instrui o Yoast a marcar artigos fracos como `noindex`.

**Artigos `noindex` ainda são publicados no site** — os leitores acessam normalmente. A diferença é que o Google não os indexa, preservando o crawl budget para o conteúdo que realmente importa.

---

## 2. Por que NÃO usar só contagem de palavras

O Google não usa contagem de palavras para definir qualidade. Uma notícia de 400 palavras bem estruturada com H3, links internos e análise editorial é **melhor** para o Google do que 800 palavras de texto bruto sem estrutura.

| Só palavra | Score multifatorial |
|---|---|
| 500 palavras = INDEX | Analisa estrutura H2/H3 |
| 499 palavras = NOINDEX | Analisa links internos que distribuem PageRank |
| Ignora formatação | Detecta bloco "Nossa Análise" |
| Ignora links | Threshold ajustável |

O threshold de 500 palavras é uma regra de bolso pragmática, não uma diretriz do Google. O score multifatorial reflete melhor o que o Google considera conteúdo de qualidade.

---

## 3. A função `assess_content_quality`

**Localização:** `app/pipeline.py` — linha ~64 (após o dicionário `CLEANER_FUNCTIONS`, antes de `_get_article_url`)

```python
def assess_content_quality(content_html: str) -> dict:
    """
    Score multifatorial de qualidade — decide indexação.
    Fatores: palavras, estrutura H2/H3, links internos, bloco editorial.
    Score >= 45 → indexar.  Score < 45 → noindex.
    """
    soup  = BeautifulSoup(content_html, "html.parser")
    text  = soup.get_text(separator=" ", strip=True)
    words = len(text.split())

    score = 0
    # 1. Volume de palavras
    if   words >= 600: score += 30
    elif words >= 400: score += 15

    # 2. Estrutura hierárquica (H3 dentro de H2 = profundidade real)
    if soup.find("h3"): score += 20
    if soup.find("h2"): score += 10

    # 3. Links internos (distribuem PageRank, ajudam cluster)
    int_links = [a for a in soup.find_all("a", href=True)
                 if "maquinanerd.com.br" in a["href"]]
    if   len(int_links) >= 2: score += 20
    elif len(int_links) >= 1: score += 10

    # 4. Bloco editorial "Nossa Análise" (do novo prompt)
    if "nossa análise" in text.lower(): score += 15

    should_index = score >= 45
    reason = (
        f"score={score} | {words}w | h3={'sim' if soup.find('h3') else 'não'}"
        f" | links_int={len(int_links)} → {'INDEX' if should_index else 'NOINDEX'}"
    )
    return {"should_index": should_index, "word_count": words,
            "score": score, "reason": reason}
```

### Tabela de pontuação

| Fator | Condição | Pontos |
|---|---|---|
| **Palavras** | >= 600 palavras | +30 |
| **Palavras** | >= 400 palavras (mas < 600) | +15 |
| **Estrutura** | Tem `<h3>` | +20 |
| **Estrutura** | Tem `<h2>` | +10 |
| **Links internos** | >= 2 links para maquinanerd.com.br | +20 |
| **Links internos** | 1 link para maquinanerd.com.br | +10 |
| **Editorial** | Contém "nossa análise" (case-insensitive) | +15 |

**Threshold:** `score >= 45` → INDEX. `score < 45` → NOINDEX.

### Pontuação máxima possível: 95 pontos

Um artigo perfeito teria: 600+ palavras (+30) + H3 (+20) + H2 (+10) + 2+ links internos (+20) + "Nossa Análise" (+15) = **95 pontos**.

### Exemplos práticos

| Conteúdo | Pontos | Decisão |
|---|---|---|
| 650w + H2 + H3 + 2 links + "Nossa Análise" | 30+10+20+20+15 = **95** | INDEX ✅ |
| 620w + H2 + H3 + 1 link | 30+10+20+10 = **70** | INDEX ✅ |
| 450w + H3 + 2 links | 15+20+20 = **55** | INDEX ✅ |
| 420w + H2 | 15+10 = **25** | NOINDEX ❌ |
| 300w sem estrutura | 0 = **0** | NOINDEX ❌ |
| 300w + 2 links + "Nossa Análise" | 0+20+15 = **35** | NOINDEX ❌ |
| 400w + 2 links + "Nossa Análise" | 15+20+15 = **50** | INDEX ✅ |

### Por que o threshold é 45 e não 50?

45 foi escolhido porque permite que artigos menores mas **bem estruturados** (links internos + bloco editorial) sejam indexados. Um artigo de notícia rápida de 400 palavras com 2 links internos e "Nossa Análise" marca 50 pontos — suficiente para passar. Isso é filosoficamente correto: o artigo está **conectado à rede interna do site** e tem análise própria.

---

## 4. O que muda no pipeline — 3 linhas no loop principal

**Localização:** `app/pipeline.py` — após o bloco de SEO meta (Yoast keyphrases), antes da verificação final de CTA.

```python
# ─── QA Score — decide indexação ─────────────────────────────────────
quality = assess_content_quality(content_html)
logger.info(f"[QA] {title[:50]} | {quality['reason']}")
noindex_value = "0" if quality["should_index"] else "1"
```

### Por que neste ponto exato?

O posicionamento é deliberado:

```
RSS ingestion
    ↓
AI rewrite (Gemini)
    ↓
CTA removal (camadas 1-4)
    ↓
Title validation
    ↓
Internal links injection        ← add_internal_links() roda aqui
    ↓
Yoast meta (keyphrases)
    ↓
>>> QUALITY SCORE <<<           ← assess_content_quality() roda AQUI
    ↓
CTA final check
    ↓
Gutenberg conversion
    ↓
create_post()
    ↓
update_post_yoast_seo()         ← noindex_value chega aqui
```

**Motivo:** O score é calculado **depois** que `add_internal_links()` já injetou os links internos. Se fosse calculado antes, o contador de links internos seria 0 para todos os artigos — o fator que vale +20 pontos nunca seria aplicado.

### O que a função retorna

```python
{
    "should_index": True,          # bool — True = INDEX, False = NOINDEX
    "word_count": 742,             # int — número de palavras no texto extraído
    "score": 65,                   # int — pontuação bruta
    "reason": "score=65 | 742w | h3=sim | links_int=2 → INDEX"
}
```

### Formato do log

```
2026-03-12 12:13:49 - INFO - pipeline - [QA] Steven Spielberg anuncia trailer de Disclosu | score=65 | 742w | h3=sim | links_int=2 → INDEX
```

O log usa `title[:50]` — os primeiros 50 caracteres do título, para caber numa linha de log legível.

---

## 5. Como o `noindex_value` chega no WordPress

Este é o ponto mais técnico e importante de entender.

### O problema: `create_post()` descarta `meta`

Em `app/wordpress.py`, a função `create_post()` tem um filtro explícito:

```python
safe_fields = ['title', 'slug', 'content', 'excerpt', 'categories', 'tags', 'featured_media', 'status']
clean_payload = {k: v for k, v in payload.items() if k in safe_fields}
```

O campo `meta` **não está em `safe_fields`**. Isso significa que qualquer coisa enviada em `post_payload['meta']` no pipeline é silenciosamente descartada antes de chegar no WordPress. Esse filtro existe para evitar erros 500 causados por campos desconhecidos da REST API.

### A solução: `update_post_yoast_seo()`

Após `create_post()` retornar o ID do post criado, o pipeline faz uma segunda chamada:

```python
yoast_ok = wp_client.update_post_yoast_seo(wp_post_id, featured_media_id, seo_meta)
```

Essa função **não usa `safe_fields`** — ela envia diretamente `{'meta': yoast_fields}` para a REST API, que aceita campos Yoast prefixados com `_yoast_wpseo_`.

### O fluxo completo do `noindex_value`

```
assess_content_quality(content_html)
    → noindex_value = "0" ou "1"
        ↓
seo_meta = {
    ...,
    'noindex': noindex_value,    # string "0" ou "1"
    'nofollow': '0',             # SEMPRE "0"
}
        ↓
wp_client.update_post_yoast_seo(wp_post_id, featured_media_id, seo_meta)
        ↓
yoast_fields = {
    ...,
    '_yoast_wpseo_meta-robots-noindex': seo_data.get('noindex', '0'),
    '_yoast_wpseo_meta-robots-nofollow': '0',
}
        ↓
POST /wp-json/wp/v2/posts/{id}
    {'meta': yoast_fields}
        ↓
WordPress salva no banco: wp_postmeta
    meta_key = '_yoast_wpseo_meta-robots-noindex' | meta_value = '1' ou '0'
        ↓
Yoast renderiza no HTML do post:
    <meta name="robots" content="noindex, follow" />   (se noindex=1)
    <meta name="robots" content="index, follow" />     (se noindex=0)
```

---

## 6. Mudanças em `app/wordpress.py`

**Função:** `update_post_yoast_seo()` — linha ~686

```python
# ANTES (sem controle de indexação):
yoast_fields = {
    '_yoast_wpseo_title': ...,
    '_yoast_wpseo_metadesc': ...,
    '_yoast_wpseo_focuskw': ...,
    '_yoast_wpseo_opengraph-image': '',
    '_yoast_wpseo_opengraph-image-id': str(featured_media_id),
    '_yoast_wpseo_content_score': '90',
    '_yoast_wpseo_primary_category': '',
}

# DEPOIS (com controle de indexação):
yoast_fields = {
    '_yoast_wpseo_title': ...,
    '_yoast_wpseo_metadesc': ...,
    '_yoast_wpseo_focuskw': ...,
    '_yoast_wpseo_opengraph-image': '',
    '_yoast_wpseo_opengraph-image-id': str(featured_media_id),
    '_yoast_wpseo_content_score': '90',
    '_yoast_wpseo_primary_category': '',
    '_yoast_wpseo_meta-robots-noindex': seo_data.get('noindex', '0'),
    '_yoast_wpseo_meta-robots-nofollow': '0',  # SEMPRE "0"
}
```

O default de `seo_data.get('noindex', '0')` garante que mesmo sem o campo, o comportamento é **indexar** — nunca bloquear conteúdo por acidente.

---

## 7. Por que `nofollow` é SEMPRE "0"

Este é um detalhe crítico de SEO que não é óbvio.

### O que nofollow faz

`nofollow` na diretiva Yoast controla se o Googlebot **segue os links** dentro do artigo. Valor `"1"` = não seguir links. Valor `"0"` = seguir links.

### Por que nunca bloquear os links

Mesmo artigos marcados como `noindex` (não aparecem no Google) **distribuem PageRank pelos links que contêm**. Isso é chamado de "link equity" ou "PageRank sculpting".

**Cenário concreto:**

```
Artigo curto sobre Batman (noindex, 300w, score=20)
    ↓ contém link interno para
Página evergreen Batman Timeline (index, 2000w, score=95)
```

Com `nofollow="0"`:
- O artigo curto não aparece no Google ✅
- Mas o link dele para o Batman Timeline **passa valor de PageRank** ✅
- O Batman Timeline fica mais forte no Google ✅

Com `nofollow="1"` (errado):
- O artigo curto não aparece no Google ✅
- O link para o Batman Timeline **não passa valor algum** ❌
- Crawl budget desperdiçado sem nenhum benefício em troca ❌

A regra é simples: **noindex + nofollow é sempre pior que noindex sozinho**.

---

## 8. Mudanças em `app/pipeline.py` — seo_meta

**Localização:** após `create_post()` retornar o ID, dentro do `try` de atualização Yoast.

```python
# ANTES:
seo_meta = {
    'title': rewritten_data.get('seo_title', title)[:70],
    'description': rewritten_data.get('meta_description', '')[:160],
    'focuskw': rewritten_data.get('focus_keyword', ...)[:30],
    'title_pt': title[:70],
    'description_pt': rewritten_data.get('meta_description', '')[:160],
}

# DEPOIS:
seo_meta = {
    'title': rewritten_data.get('seo_title', title)[:70],
    'description': rewritten_data.get('meta_description', '')[:160],
    'focuskw': rewritten_data.get('focus_keyword', ...)[:30],
    'title_pt': title[:70],
    'description_pt': rewritten_data.get('meta_description', '')[:160],
    'noindex': noindex_value,   # "0" = indexar, "1" = noindex
    'nofollow': '0',            # SEMPRE "0" — nunca mudar
}
```

---

## 9. `BeautifulSoup` — já estava importado

Não foi necessário adicionar import. `BeautifulSoup` já estava presente no arquivo:

```python
# app/pipeline.py — linha 43 (pré-existente)
from bs4 import BeautifulSoup
```

A função `assess_content_quality` usa `BeautifulSoup` para parsear o HTML e extrair:
- Texto limpo (`.get_text()`) → contagem de palavras
- Tags `<h2>` e `<h3>` → estrutura hierárquica
- Tags `<a href>` com domínio `maquinanerd.com.br` → links internos

---

## 10. Localização exata das 4 mudanças no código

| # | Arquivo | Linha | O que mudou |
|---|---|---|---|
| 1 | `app/pipeline.py` | ~64 | **Nova função** `assess_content_quality()` adicionada entre `CLEANER_FUNCTIONS` e `_get_article_url` |
| 2 | `app/pipeline.py` | ~489 | **3 linhas** de QA Score + log + `noindex_value` adicionadas após keyphrases Yoast, antes do CTA check |
| 3 | `app/pipeline.py` | ~531 | **2 campos** `'noindex'` e `'nofollow'` adicionados ao dict `seo_meta` |
| 4 | `app/wordpress.py` | ~686 | **2 campos** `_yoast_wpseo_meta-robots-noindex` e `_yoast_wpseo_meta-robots-nofollow` adicionados ao dict `yoast_fields` |

---

## 11. Como verificar nos logs

Após a próxima execução do pipeline, procure no log por `[QA]`:

```
grep "[QA]" logs/app.log
```

Formato esperado:
```
2026-03-12 14:23:01 - INFO - pipeline - [QA] Novo trailer de Deadpool & Wolverine revela | score=70 | 680w | h3=sim | links_int=3 → INDEX
2026-03-12 14:23:45 - INFO - pipeline - [QA] Marvel confirma data de estreia | score=25 | 280w | h3=não | links_int=1 → NOINDEX
```

---

## 12. Como ajustar os pesos

Para mudar os critérios de qualidade, edite diretamente `assess_content_quality()` em `app/pipeline.py`:

```python
# Aumentar exigência de palavras:
if   words >= 700: score += 30   # era 600
elif words >= 500: score += 15   # era 400

# Tornar H3 menos importante:
if soup.find("h3"): score += 10  # era 20

# Aumentar o threshold de corte:
should_index = score >= 55       # era 45
```

**Recomendação:** Rode o pipeline por 1-2 semanas sem alterar nada. Acumule dados no log (`grep "[QA]" logs/app.log | grep "NOINDEX"`). Analise quais artigos foram bloqueados e se a decisão faz sentido editorialmente. Só então ajuste os pesos.

---

## 13. Compatibilidade com artigos existentes

Esta implementação **só afeta artigos novos** publicados após o deploy. Artigos já publicados no WordPress não são alterados. O Yoast SEO deles continua com os valores que foram definidos na época da publicação (provavelmente o default do Yoast, que é indexar tudo).

Para retroativamente aplicar o QA nos artigos existentes, seria necessário um script separado que buscasse todos os posts, recalculasse o score e enviasse o update via REST API — isso está fora do escopo desta implementação.

---

## 14. Diagrama do fluxo completo

```
[RSS Feed]
    ↓
[FeedReader — filtra já processados]
    ↓
[ContentExtractor — scraping do conteúdo original]
    ↓
[AIProcessor — rewrite com Gemini (batch de 3)]
    ↓
[detect_forbidden_cta() — 4 camadas de verificação]
    ↓
[add_internal_links() — injeta links para maquinanerd.com.br]
    ↓
[assess_content_quality(content_html)]  ← NOVO
    │
    ├─ score >= 45  →  noindex_value = "0"  (INDEX)
    └─ score < 45   →  noindex_value = "1"  (NOINDEX)
    ↓
[detect_forbidden_cta() — verificação final]
    ↓
[html_to_gutenberg_blocks() — converte para Gutenberg]
    ↓
[create_post(post_payload)]
    ↓
[update_post_yoast_seo(wp_post_id, featured_media_id, seo_meta)]
    │
    └─ envia _yoast_wpseo_meta-robots-noindex: "0" ou "1"  ← NOVO
       envia _yoast_wpseo_meta-robots-nofollow: "0"        ← NOVO
    ↓
[WordPress — REST API v2]
    ↓
[Yoast SEO renderiza <meta name="robots"> correto no HTML do post]
```
