# Como o JSON é Criado, Publicado e Sincronizado com o Yoast SEO

> Documentação técnica do pipeline da Máquina Nerd — do RSS à publicação no WordPress com metadados SEO completos.

---

## Sumário

1. [Visão Geral do Fluxo](#1-visão-geral-do-fluxo)
2. [Como o JSON é Criado pela IA](#2-como-o-json-é-criado-pela-ia)
3. [Estrutura Completa do JSON — Explicada Campo a Campo](#3-estrutura-completa-do-json--explicada-campo-a-campo)
4. [Exemplo Prático Real](#4-exemplo-prático-real)
5. [O Processo de Publicação no WordPress](#5-o-processo-de-publicação-no-wordpress)
6. [Como o JSON Sincroniza com o Yoast SEO](#6-como-o-json-sincroniza-com-o-yoast-seo)
7. [Diagrama Completo do Pipeline](#7-diagrama-completo-do-pipeline)

---

## 1. Visão Geral do Fluxo

```
RSS Feed → Extração → IA (Gemini) → JSON → Pipeline → WordPress REST API → Yoast SEO
```

O pipeline funciona em **5 etapas principais**:

| Etapa | Arquivo responsável | O que faz |
|-------|--------------------|-|
| 1. Leitura de feeds | `app/feeds.py` | Lê RSS/Atom de fontes configuradas |
| 2. Extração de conteúdo | `app/extractor.py` | Faz scraping da página-fonte |
| 3. Reescrita por IA | `app/ai_processor.py` | Envia para Gemini e recebe **JSON** estruturado |
| 4. Orquestração | `app/pipeline.py` | Limpa, valida e prepara o payload completo |
| 5. Publicação | `app/wordpress.py` | Publica via REST API e injeta metadados Yoast |

---

## 2. Como o JSON é Criado pela IA

### 2.1 O Prompt enviado ao Gemini

O arquivo `app/ai_processor.py` monta um prompt com **regras obrigatórias** (`AI_SYSTEM_RULES`) somadas ao template em `universal_prompt.txt`. O conteúdo enviado para a API inclui:

```
titulo_original  → título do artigo-fonte
url_original     → URL da notícia original
content          → HTML completo extraído da página
domain           → domínio do portal (ex: maquinanerd.com.br)
fonte_nome       → nome da fonte (ex: igorsner.com)
categoria        → categoria sugerida pelo feed
schema_original  → JSON-LD extraído da página fonte (se existir)
videos_list      → URLs de vídeos encontrados
imagens_list     → URLs de imagens encontradas
```

### 2.2 Configuração do modelo

```python
generation_config = {
    "response_mime_type": "application/json",   # Força saída JSON puro
    "temperature": 0.2,                          # Determinístico (menos criativo)
    "top_p": 0.9,
    "max_output_tokens": 32000,
}
```

A instrução `response_mime_type: application/json` **garante** que o Gemini devolva apenas JSON válido, sem texto extra.

### 2.3 Estrutura obrigatória da resposta

O modelo é instruído a sempre devolver este contrato:

```json
{
  "resultados": [
    {
      "titulo_final": "...",
      "conteudo_final": "...",
      "meta_description": "...",
      "focus_keyphrase": "...",
      "related_keyphrases": ["..."],
      "slug": "...",
      "categorias": [...],
      "tags_sugeridas": [...],
      "yoast_meta": { ... }
    }
  ]
}
```

> O campo `resultados` é um array porque o pipeline processa **até 3 artigos em lote** por chamada de API (para economizar quota).

---

## 3. Estrutura Completa do JSON — Explicada Campo a Campo

```jsonc
{
  // ─── CONTEÚDO EDITORIAL ──────────────────────────────────────────────────

  "titulo_final": "...",
  // Título reescrito. Regras: 55–65 chars, começa com entidade, verbo no
  // presente, sem sensacionalismo, maiúsculas só em nomes próprios.

  "conteudo_final": "...",
  // HTML completo do artigo reescrito. Deve conter: mínimo 3 <h2>,
  // palavra-chave no 1º parágrafo, imagens em <figure><figcaption>,
  // links internos com href completo (https://dominio/tag/xxx).

  "meta_description": "...",
  // Resumo da notícia. Regras: 140–155 chars, contém a palavra-chave
  // principal, sem call-to-action.

  // ─── SEO ESTRUTURAL ──────────────────────────────────────────────────────

  "focus_keyphrase": "...",
  // Palavra-chave principal. Usada pelo Yoast para calcular SEO score.
  // Exemplo: "Lucas Ronier Coritiba"

  "related_keyphrases": ["...", "...", "..."],
  // Variações semânticas da palavra-chave. Injetadas no Yoast como
  // _yoast_wpseo_keyphrases.

  "slug": "...",
  // URL amigável do post. Gerada pela IA e enviada ao WordPress.
  // Exemplo: "lucas-ronier-coritiba-sete-gols"

  // ─── TAXONOMIA ───────────────────────────────────────────────────────────

  "categorias": [
    { "nome": "Coritiba", "grupo": "times", "evidence": "Coritiba" },
    { "nome": "Série B",  "grupo": "competicoes", "evidence": "Série B" }
  ],
  // Categorias sugeridas pela IA. O pipeline resolve os nomes para IDs
  // reais do WordPress via wp_client.resolve_category_names_to_ids().

  "tags_sugeridas": ["Lucas Ronier", "Coritiba", "Série B", "Lesão"],
  // Tags para o artigo. O WordPress cria tags novas automaticamente se
  // não existirem. Máximo de 10 tags efetivamente enviadas.

  // ─── YOAST META (sincronizado via REST API) ───────────────────────────────

  "yoast_meta": {
    "_yoast_wpseo_title":              "...",  // SEO title (tab do navegador)
    "_yoast_wpseo_metadesc":           "...",  // Meta description
    "_yoast_wpseo_focuskw":            "...",  // Focus keyword
    "_yoast_news_keywords":            "...",  // Palavras-chave para Google News
    "_yoast_wpseo_opengraph-title":    "...",  // Título do card OG (Facebook/WhatsApp)
    "_yoast_wpseo_opengraph-description": "...", // Descrição do card OG
    "_yoast_wpseo_twitter-title":      "...",  // Título do card Twitter/X
    "_yoast_wpseo_twitter-description":"..."   // Descrição do card Twitter/X
  }
}
```

---

## 4. Exemplo Prático Real

Este é um JSON real gerado e publicado pelo pipeline (arquivo `debug/ai_response_20250930-161754.json`):

```json
{
  "titulo_final": "Lucas Ronier atinge 7 gols e supera marca de 2024 no Coritiba",
  "conteudo_final": "<p>O atacante <b>Lucas Ronier</b> atingiu a marca de sete gols pelo <b>Coritiba</b> na temporada de 2025, superando os seis gols marcados em sua estreia no time profissional em 2024. O gol do jogador foi fundamental na vitória por 2 a 0 sobre o Avaí, na Ressacada, em partida válida pela 29ª rodada da <b>Série B</b>.</p>\n\n<figure class=\"image-container\">\n  <img src=\"https://lncimg.lance.com.br/cdn-cgi/image/width=950,quality=75,fit=pad,format=webp/uploads/2025/09/Lucas-Ronier-Coritiba-aspect-ratio-512-320.jpg\"\n       alt=\"Lucas Ronier comemora gol pelo Coritiba na Série B\">\n  <figcaption>Lucas Ronier marcou um dos gols na vitória do Coritiba sobre o Avaí.</figcaption>\n</figure>\n\n<h2>Lucas Ronier melhora desempenho em 2025</h2>\n<p>Com 20 anos, Lucas Ronier soma agora sete gols e uma assistência em 34 jogos disputados em 2025...</p>\n\n<h2>Preocupação com lesão de Lucas Ronier</h2>\n<p>Após abrir o placar no primeiro tempo contra o Avaí, Lucas Ronier deixou a partida sentindo dores na posterior da coxa esquerda...</p>\n\n<h2>Situação do Coritiba na Série B</h2>\n<p>Com a vitória sobre o Avaí, o Coritiba encerrou uma sequência negativa de duas derrotas...</p>",

  "meta_description": "Lucas Ronier marca seu 7º gol na temporada e supera o desempenho de 2024 pelo Coritiba na Série B. Atacante preocupa após lesão.",

  "focus_keyphrase": "Lucas Ronier Coritiba",

  "related_keyphrases": [
    "Lucas Ronier gols Coritiba",
    "Coritiba Série B",
    "artilharia Série B"
  ],

  "slug": "lucas-ronier-coritiba-sete-gols",

  "categorias": [
    { "nome": "Coritiba", "grupo": "times",      "evidence": "Coritiba" },
    { "nome": "Série B",  "grupo": "competicoes","evidence": "Série B"  },
    { "nome": "Avaí",     "grupo": "times",      "evidence": "Avaí"     }
  ],

  "tags_sugeridas": [
    "Lucas Ronier", "Coritiba", "Série B", "Avaí", "Gols", "Lesão"
  ],

  "yoast_meta": {
    "_yoast_wpseo_title":                  "Lucas Ronier marca 7 gols e supera 2024 no Coritiba | Série B",
    "_yoast_wpseo_metadesc":               "Lucas Ronier atinge sete gols em 2025 pelo Coritiba, superando marca de 2024. Atacante foi fundamental na vitória pela Série B, mas saiu machucado.",
    "_yoast_wpseo_focuskw":                "Lucas Ronier Coritiba",
    "_yoast_news_keywords":                "Lucas Ronier, Coritiba, Avaí, Série B, gols, lesão, futebol nacional",
    "_yoast_wpseo_opengraph-title":        "Lucas Ronier atinge 7 gols e supera marca de 2024 no Coritiba",
    "_yoast_wpseo_opengraph-description":  "O atacante Lucas Ronier atingiu a marca de sete gols pelo Coritiba na temporada de 2025...",
    "_yoast_wpseo_twitter-title":          "Lucas Ronier atinge 7 gols e supera marca de 2024 no Coritiba",
    "_yoast_wpseo_twitter-description":    "Lucas Ronier marca 7 gols pelo Coritiba em 2025, superando 2024. Vitórias na Série B, mas lesão preocupa."
  }
}
```

### O que acontece com esse JSON após ser gerado:

```
1. Pipeline lê titulo_final     → valida 55–65 chars, corrige se necessário
2. Pipeline lê conteudo_final   → remove CTAs (4 camadas de limpeza)
3. Pipeline converte HTML       → formato Gutenberg (<!-- wp:paragraph -->)
4. Pipeline sobe imagem         → WordPress Media Library → retorna media_id
5. Pipeline monta wp_payload    → title, slug, content, excerpt, categories, tags, featured_media
6. WordPressClient.create_post  → POST /wp-json/wp/v2/posts → retorna post_id
7. WordPressClient.update_post_yoast_seo → POST /wp-json/wp/v2/posts/{id} com meta Yoast
8. WordPressClient.add_google_news_meta  → POST /wp-json/wp/v2/posts/{id} com meta Google News
```

---

## 5. O Processo de Publicação no WordPress

### 5.1 Payload enviado ao WordPress (`POST /wp-json/wp/v2/posts`)

```python
post_payload = {
    "title":          "Lucas Ronier atinge 7 gols e supera marca de 2024 no Coritiba",
    "slug":           "lucas-ronier-coritiba-sete-gols",
    "content":        "<!-- wp:paragraph --><p>O atacante...</p><!-- /wp:paragraph -->...",
    "excerpt":        "Lucas Ronier marca seu 7º gol na temporada...",
    "categories":     [15, 42, 78],       # IDs resolvidos no WordPress
    "tags":           [101, 205, 310],    # IDs resolvidos/criados no WordPress
    "featured_media": 9834,               # ID da imagem já upada na Media Library
    "status":         "publish",
    "meta": {
        # ← campos Yoast já incluídos na criação inicial
        "_yoast_wpseo_title":    "Lucas Ronier marca 7 gols...",
        "_yoast_wpseo_metadesc": "Lucas Ronier atinge sete gols...",
        "_yoast_wpseo_focuskw":  "Lucas Ronier Coritiba",
        "_yoast_wpseo_canonical":"https://fonte-original.com.br/artigo",
        "_yoast_wpseo_keyphrases": "[{\"keyword\":\"Lucas Ronier gols Coritiba\"}, ...]"
    }
}
```

> **Importante:** o pipeline filtra o payload para enviar **apenas os campos seguros** (`title`, `slug`, `content`, `excerpt`, `categories`, `tags`, `featured_media`, `meta`, `status`) para evitar erros 500 do WordPress.

### 5.2 Upload da imagem destacada

Antes de criar o post, a imagem é enviada para a Media Library:

```
GET  {imagem_url}                        → baixa os bytes da imagem
POST /wp-json/wp/v2/media                → faz upload com Content-Disposition + Content-Type
     → retorna { "id": 9834, "source_url": "https://maquinanerd.com.br/wp-content/..." }

POST /wp-json/wp/v2/media/9834           → atualiza alt_text com o título do artigo
```

### 5.3 Resolução de taxonomia

**Categorias:**
```
1. Verifica WORDPRESS_CATEGORIES (dict local em config.py)
2. Se não encontrar → GET /wp-json/wp/v2/categories?search=nome
3. Se não existir   → POST /wp-json/wp/v2/categories { name, slug }
4. Retorna ID inteiro para incluir no payload
```

**Tags:**
```
1. GET /wp-json/wp/v2/tags?search=nome (busca por nome exato e slug)
2. Se não existir → POST /wp-json/wp/v2/tags { name, slug }
3. Race condition protegida: se 400 com term_exists → rebusca o ID existente
```

---

## 6. Como o JSON Sincroniza com o Yoast SEO

A sincronização com o Yoast acontece em **duas fases** após a criação do post.

### Fase 1 — Inclusão direta no `create_post`

O campo `meta` do payload inicial já carrega os metadados Yoast. O WordPress REST API v2 aceita campos de meta registrados pelo plugin — o Yoast registra todos os seus campos `_yoast_wpseo_*` como metadados públicos.

```json
"meta": {
  "_yoast_wpseo_title":     "SEO Title aqui",
  "_yoast_wpseo_metadesc":  "Meta description aqui",
  "_yoast_wpseo_focuskw":   "palavra-chave principal",
  "_yoast_wpseo_canonical": "https://fonte-original.com.br/artigo",
  "_yoast_wpseo_keyphrases": "[{\"keyword\": \"variacao 1\"}, {\"keyword\": \"variacao 2\"}]"
}
```

### Fase 2 — `update_post_yoast_seo()` (após criação)

Após receber o `post_id` do WordPress, o pipeline faz um segundo `POST` para completar o Yoast com os campos de imagem OG:

```python
# app/wordpress.py → update_post_yoast_seo()

yoast_fields = {
    "_yoast_wpseo_title":              "SEO Title",
    "_yoast_wpseo_metadesc":           "Meta description",
    "_yoast_wpseo_focuskw":            "palavra-chave",
    "_yoast_wpseo_opengraph-image":    "https://maquinanerd.com.br/wp-content/...",  # URL real da imagem
    "_yoast_wpseo_opengraph-image-id": "9834",   # ID na Media Library
    "_yoast_wpseo_content_score":      "90",
}

# Requisição:
POST /wp-json/wp/v2/posts/{post_id}
Body: { "meta": yoast_fields }
```

> A **OG image** é buscada dinamicamente no WordPress (`GET /wp-json/wp/v2/media/{media_id}`) para garantir que aponte para a URL hospedada no site, nunca para a URL externa da fonte original.

### Fase 3 — Google News Meta

```python
# app/wordpress.py → add_google_news_meta()

news_fields = {
    "googleNews_keywords": "Lucas Ronier, Coritiba, Série B, gols, lesão",
    "googleNews_genres":   "Blog, News",
    "googleNews_standout": "no",
    "googleNews_access":   "Free",
}

POST /wp-json/wp/v2/posts/{post_id}
Body: { "meta": news_fields }
```

### Mapa completo: campo JSON → campo Yoast

| Campo no JSON da IA | Campo no WordPress/Yoast | Onde aparece |
|---------------------|--------------------------|--------------|
| `titulo_final` | `title` (campo nativo WP) | Título do post |
| `yoast_meta._yoast_wpseo_title` | `_yoast_wpseo_title` | SEO title (aba navegador, Google) |
| `yoast_meta._yoast_wpseo_metadesc` | `_yoast_wpseo_metadesc` | Meta description no Google |
| `yoast_meta._yoast_wpseo_focuskw` | `_yoast_wpseo_focuskw` | Focus keyphrase no painel Yoast |
| `yoast_meta._yoast_news_keywords` | `_yoast_news_keywords` | Plugin Yoast News SEO |
| `yoast_meta._yoast_wpseo_opengraph-title` | `_yoast_wpseo_opengraph-title` | Card Facebook/WhatsApp |
| `yoast_meta._yoast_wpseo_opengraph-description` | `_yoast_wpseo_opengraph-description` | Card Facebook/WhatsApp |
| `yoast_meta._yoast_wpseo_twitter-title` | `_yoast_wpseo_twitter-title` | Card Twitter/X |
| `yoast_meta._yoast_wpseo_twitter-description` | `_yoast_wpseo_twitter-description` | Card Twitter/X |
| `related_keyphrases` | `_yoast_wpseo_keyphrases` (JSON array) | Related keyphrases no Yoast |
| URL original da fonte | `_yoast_wpseo_canonical` | Tag canonical (evita duplicate content) |
| ID da imagem upada | `_yoast_wpseo_opengraph-image-id` | OG image ID |
| URL da imagem upada | `_yoast_wpseo_opengraph-image` | OG image URL |

---

## 7. Diagrama Completo do Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PIPELINE MÁQUINA NERD                              │
└─────────────────────────────────────────────────────────────────────────────┘

  [RSS Feed]
      │
      ▼
  feeds.py ──────► FeedReader.fetch()
      │              Lê XML, extrai entries (title, url, published_at)
      │
      ▼
  extractor.py ──► ContentExtractor.extract()
      │              Scraping da página: HTML, imagens, vídeos, schema JSON-LD
      │
      ▼
  ai_processor.py ► AIProcessor.rewrite_batch(batch=[art1, art2, art3])
      │
      │   PROMPT ENVIADO AO GEMINI:
      │   ┌─────────────────────────────────────┐
      │   │  AI_SYSTEM_RULES (regras editoriais) │
      │   │  + universal_prompt.txt              │
      │   │  + titulo_original, content, domain  │
      │   │  + schema_original, imagens, vídeos  │
      │   └─────────────────────────────────────┘
      │
      │   JSON RETORNADO PELO GEMINI:
      │   ┌─────────────────────────────────────┐
      │   │  { "resultados": [                  │
      │   │    {                                │
      │   │      titulo_final, conteudo_final,  │
      │   │      meta_description,              │
      │   │      focus_keyphrase,               │
      │   │      related_keyphrases,            │
      │   │      slug, categorias,              │
      │   │      tags_sugeridas, yoast_meta     │
      │   │    }                                │
      │   │  ]}                                 │
      │   └─────────────────────────────────────┘
      │
      ▼
  pipeline.py ───► Limpeza e validação
      │              ├── 4 camadas anti-CTA (remove "Thank you for reading...")
      │              ├── TitleValidator (55–65 chars, entidade, verbo presente)
      │              ├── optimize_title() (Google News & Discovery)
      │              ├── unescape_html, validate_and_fix_figures
      │              ├── add_internal_links (link map do banco)
      │              └── html_to_gutenberg_blocks() → formato WordPress
      │
      ▼
  wordpress.py ──► WordPressClient.upload_media_from_url()
      │              POST /wp-json/wp/v2/media
      │              → retorna featured_media_id: 9834
      │
      ▼
  wordpress.py ──► WordPressClient.create_post(payload)
      │              POST /wp-json/wp/v2/posts
      │              Body: { title, slug, content (Gutenberg),
      │                      excerpt, categories, tags,
      │                      featured_media, status: "publish",
      │                      meta: { _yoast_wpseo_* } }
      │              → retorna wp_post_id: 12345
      │
      ├──────────► WordPressClient.update_post_yoast_seo(12345)
      │              POST /wp-json/wp/v2/posts/12345
      │              Body: { meta: { _yoast_wpseo_opengraph-image,
      │                              _yoast_wpseo_opengraph-image-id,
      │                              _yoast_wpseo_content_score } }
      │
      └──────────► WordPressClient.add_google_news_meta(12345)
                     POST /wp-json/wp/v2/posts/12345
                     Body: { meta: { googleNews_keywords,
                                     googleNews_genres,
                                     googleNews_access } }

  RESULTADO FINAL:
  ┌────────────────────────────────────────────────────────────────┐
  │  Post publicado em https://maquinanerd.com.br/?p=12345        │
  │  ✅ Título SEO configurado no Yoast                           │
  │  ✅ Meta description no Yoast                                 │
  │  ✅ Focus keyphrase no Yoast                                  │
  │  ✅ OG Image apontando para CDN do Maquina Nerd               │
  │  ✅ Canonical para a fonte original (evita duplicate content) │
  │  ✅ Twitter/X card configurado                                │
  │  ✅ Google News keywords configurados                         │
  │  JSON salvo em debug/ai_response_batch_{slug}_{timestamp}.json│
  └────────────────────────────────────────────────────────────────┘
```

---

## Observações Importantes

### Por que o Yoast recebe os dados em dois momentos?

O `create_post` já envia os campos `_yoast_wpseo_*` no `meta`, mas o campo `_yoast_wpseo_opengraph-image` (URL real da imagem) só pode ser preenchido **depois** que a imagem foi upada e o WordPress devolveu a URL final hospedada no servidor. Por isso existe o segundo `update_post_yoast_seo()`.

### O que acontece se o Yoast não atualizar?

O pipeline loga `⚠️ Falha ao atualizar Yoast SEO para post {id}` mas **não cancela** a publicação. O post fica publicado com os metadados básicos do `create_post` e sem a OG image atualizada.

### Onde ficam os JSONs salvos?

Cada artigo publicado com sucesso gera um arquivo em:
```
debug/ai_response_batch_{slug}_{YYYYMMDD-HHMMSS}.json
```

Exemplo: `debug/ai_response_batch_lucas-ronier-coritiba-sete-gols_20250930-161754.json`
