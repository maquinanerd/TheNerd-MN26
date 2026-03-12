# Fix: Canonical Externo — _yoast_wpseo_canonical

**Data:** 12 de março de 2026  
**Arquivo alterado:** `app/pipeline.py` — linha 446  
**Tipo:** Bug crítico de SEO  
**Impacto:** Indexação no Google  

---

## O Problema

### O que é o canonical?

A tag `<link rel="canonical">` é um sinal que você envia ao Google para dizer:
**"Esta é a versão oficial desta página. Indexe esta, não outras cópias."**

Quando o canonical aponta para um domínio externo, você está dizendo ao Google:
**"Minha página é uma cópia da fonte original. Não indexe a minha."**

O Google obedece. O artigo vai para o status **"Rastreada, não indexada"** no Google Search Console — aparece nos relatórios de cobertura como conteúdo detectado mas deliberadamente excluído do índice.

---

## Como estava o código (ANTES)

### Localização exata

**Arquivo:** `app/pipeline.py`  
**Linha:** 446  
**Contexto:** bloco de montagem do SEO meta, dentro do loop principal de processamento de artigos

```python
# SEO meta
yoast_meta = rewritten_data.get('yoast_meta', {})
yoast_meta['_yoast_wpseo_canonical'] = art_data['url']   # ← BUG
if related_kws := rewritten_data.get('related_keyphrases'):
    yoast_meta['_yoast_wpseo_keyphrases'] = json.dumps([{"keyword": kw} for kw in related_kws])
```

### O que `art_data['url']` contém

`art_data['url']` é a **URL original do artigo na fonte** — o endereço do site de onde o conteúdo foi coletado pelo RSS/XML feed. Exemplos reais do pipeline:

- `https://screenrant.com/movie-title-article-review/`
- `https://variety.com/2026/film/news/some-film-news/`
- `https://ign.com/articles/game-review`

### O que o pipeline fazia com isso

1. Coletava o artigo via RSS (`feeds.py`)
2. Reescrevia com Gemini AI (`rewriter.py`)
3. Montava o payload para o WordPress **incluindo** `_yoast_wpseo_canonical` com a URL da fonte
4. Publicava no `maquinanerd.com.br`

O resultado enviado para o WordPress ficava assim no payload:

```python
post_payload = {
    'title': title,
    'slug': rewritten_data.get('slug'),
    'content': gutenberg_content,
    'excerpt': rewritten_data.get('meta_description', ''),
    'categories': list(final_category_ids),
    'tags': rewritten_data.get('tags_sugeridas', []),
    'featured_media': featured_media_id,
    'meta': {
        '_yoast_wpseo_title': '...',
        '_yoast_wpseo_metadesc': '...',
        '_yoast_wpseo_focuskw': '...',
        '_yoast_wpseo_canonical': 'https://screenrant.com/artigo-original/',  # ← ENVIADO
        '_yoast_wpseo_keyphrases': '...',
    }
}
```

### O que o WordPress publicava no HTML

O Yoast SEO recebia esse valor e gerava no `<head>` de cada artigo:

```html
<link rel="canonical" href="https://screenrant.com/artigo-original/" />
```

Em vez de:

```html
<link rel="canonical" href="https://maquinanerd.com.br/slug-do-artigo/" />
```

### Consequência no Google Search Console

Todos os artigos publicados com esse bug apareciam na categoria:

> **"Rastreada — não indexada"**  
> *Detectamos esta URL, mas não a indexamos pois ela sinaliza que o conteúdo canônico está em outro domínio.*

O Google não desobedece canonical voluntariamente. O domínio `maquinanerd.com.br` estava acumulando páginas publicadas que nunca apareceriam na busca enquanto esse bug existisse.

---

## Por que o campo existia no código

O campo `_yoast_wpseo_canonical` foi provavelmente introduzido na lógica de montagem do SEO meta com a intenção de **referenciar editorialmente a fonte original**. A confusão foi entre dois conceitos distintos:

| Conceito | Finalidade | Onde deve aparecer |
|---|---|---|
| **Canonical** | Diz ao Google qual é a URL definitiva do conteúdo | `<link rel="canonical">` no `<head>` — deve ser a própria URL do artigo |
| **Fonte original** | Crédito editorial à origem do conteúdo | No **corpo do artigo** como link de texto (`Fonte: Screen Rant`) |

O pipeline já adicionava corretamente a linha de crédito editorial no corpo do artigo:

```python
# Trecho em pipeline.py — adicionado ao conteúdo HTML antes da publicação
source_name = art_data['feed_config'].get('source_name', urlparse(art_data['url']).netloc)
credit_line = f'<p><strong>Fonte:</strong> <a href="{art_data["url"]}" target="_blank" rel="noopener noreferrer">{source_name}</a></p>'
content_html += f"\n{credit_line}"
```

Ou seja: a URL da fonte já estava sendo usada **corretamente** no corpo do artigo. Colocá-la também no canonical era um erro duplo — além de quebrar a indexação, era redundante.

---

## A Correção (DEPOIS)

### O que foi removido

A linha:

```python
yoast_meta['_yoast_wpseo_canonical'] = art_data['url']
```

### O que ficou no lugar

```python
# canonical OMITIDO: Yoast gera self-referencing canonical automaticamente.
# A URL da fonte é citada editorialmente no corpo do artigo.
```

### Código completo do trecho após a correção

```python
# SEO meta
yoast_meta = rewritten_data.get('yoast_meta', {})
# canonical OMITIDO: Yoast gera self-referencing canonical automaticamente.
# A URL da fonte é citada editorialmente no corpo do artigo.
if related_kws := rewritten_data.get('related_keyphrases'):
    yoast_meta['_yoast_wpseo_keyphrases'] = json.dumps([{"keyword": kw} for kw in related_kws])
```

### Por que só remover é suficiente?

Quando o campo `_yoast_wpseo_canonical` **não é enviado** (ou é enviado vazio), o Yoast SEO gera automaticamente um **self-referencing canonical** — um canonical que aponta para a própria URL do artigo no domínio do site.

Comportamento padrão do Yoast quando canonical não é definido:

```html
<!-- Gerado automaticamente pelo Yoast quando canonical não é sobrescrito -->
<link rel="canonical" href="https://maquinanerd.com.br/slug-do-artigo/" />
```

Isso é exatamente o comportamento correto para indexação.

---

## Verificação pós-publicação

### Como confirmar que a correção funcionou

1. Execute o pipeline com `MAX_PER_CYCLE=3` para publicar poucos artigos de teste
2. Abra um dos artigos publicados no navegador
3. `Ctrl+U` para ver o código-fonte
4. `Ctrl+F` → buscar `canonical`

**Resultado correto (após a correção):**
```html
<link rel="canonical" href="https://maquinanerd.com.br/slug-do-artigo/" />
```

**Resultado incorreto (como estava antes):**
```html
<link rel="canonical" href="https://screenrant.com/artigo-original/" />
```

---

## Impacto esperado

| Período | O que acontece |
|---|---|
| **Imediato** | Novos artigos publicados já saem com canonical correto |
| **1–2 semanas** | Googlebot recrawla os artigos recentes |
| **2–4 semanas** | Artigos que estavam em "Rastreada, não indexada" começam a migrar para o índice |
| **4–8 semanas** | Impacto completo visível no Google Search Console — queda no relatório de "não indexadas" e subida nas impressões orgânicas |

> Esta é potencialmente a correção de maior impacto imediato para a indexação do domínio. Artigos com conteúdo reescrito e original que estavam bloqueados pelo canonical externo devem começar a aparecer nos resultados de busca após o período de recrawl.

---

## Commit

```
793f341 — Fix canonical externo — remover _yoast_wpseo_canonical da fonte original
```

**Branch:** `main`  
**Arquivo:** `app/pipeline.py` (+2 linhas de comentário, -1 linha de código)
