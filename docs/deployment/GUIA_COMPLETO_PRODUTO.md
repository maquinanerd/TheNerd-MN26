# MaquinaNerd Pipeline — Guia Completo do Produto

> **Versão:** 2.0 | **Data:** Março de 2026  
> **Produto:** TheNews_MaquinaNerd — Automação editorial RSS → IA → WordPress  
> **Portal:** maquinanerd.com.br  
> **Stack:** Python 3.11 · Google Gemini · WordPress REST API · SQLite · APScheduler

---

## Índice

1. [Visão Geral do Produto](#1-visão-geral-do-produto)
2. [Problema Resolvido](#2-problema-resolvido)
3. [Arquitetura Completa](#3-arquitetura-completa)
4. [Fluxo de Processamento Detalhado](#4-fluxo-de-processamento-detalhado)
5. [Módulos e Responsabilidades](#5-módulos-e-responsabilidades)
6. [Sistema de IA e Prompt Engineering](#6-sistema-de-ia-e-prompt-engineering)
7. [Análise de SEO Completa](#7-análise-de-seo-completa)
8. [Análise de Schema e Dados Estruturados](#8-análise-de-schema-e-dados-estruturados)
9. [Análise de Performance e Rate Limiting](#9-análise-de-performance-e-rate-limiting)
10. [Banco de Dados e Persistência](#10-banco-de-dados-e-persistência)
11. [Rastreamento de Tokens](#11-rastreamento-de-tokens)
12. [Integrações Externas](#12-integrações-externas)
13. [Instalação e Configuração](#13-instalação-e-configuração)
14. [Variáveis de Ambiente](#14-variáveis-de-ambiente)
15. [Operação e Monitoramento](#15-operação-e-monitoramento)
16. [Tratamento de Erros e Resiliência](#16-tratamento-de-erros-e-resiliência)
17. [Análise de Qualidade e Pontos de Melhoria](#17-análise-de-qualidade-e-pontos-de-melhoria)
18. [Análise de Segurança OWASP](#18-análise-de-segurança-owasp)
19. [Roadmap e Versões Futuras](#19-roadmap-e-versões-futuras)
20. [Glossário Técnico](#20-glossário-técnico)

---

## 1. Visão Geral do Produto

O **MaquinaNerd Pipeline** é um sistema de automação editorial de produção que transforma feeds RSS internacionais (em inglês) em artigos jornalísticos publicados automaticamente em Português-Brasil no portal **maquinanerd.com.br**, com total otimização para SEO.

### O que o sistema faz em 30 segundos

```
📡 Monitora feeds RSS (ScreenRant, outros)
        ↓
🔍 Extrai artigo original completo (HTML, imagens, vídeos)
        ↓
🤖 Reescreve em PT-BR jornalístico via Gemini AI
        ↓
🔎 Otimiza SEO: título, meta description, slug, keyphrases
        ↓
📤 Publica no WordPress com Yoast SEO, categorias e tags
```

### Métricas de operação

| Indicador | Valor |
|---|---|
| Ciclos por dia | ~40 (a cada 15min entre 9h–19h BRT) |
| Máximo de artigos por ciclo | 10 artigos |
| Máximo por feed por ciclo | 3 artigos |
| Delay entre publicações | 30 segundos |
| Delay entre feeds | 45 segundos |
| Modelo de IA padrão | `gemini-2.5-flash-lite` |
| Tokens máximos por resposta | 4.096 |
| Janela de operação | 09h00–19h00 BRT |

---

## 2. Problema Resolvido

### Contexto editorial

Portais de entretenimento como o MaquinaNerd competem com gigantes (Omelete, IGN Brasil, AdoroCinema) pela fração de audiência de cultura pop no Brasil. O desafio central é **volume + qualidade editorial + SEO**, pois o Google News e o Google Discover privilegiam portais que publicam com frequência, consistência e otimização técnica.

### Solução automatizada

| Sem o pipeline | Com o pipeline |
|---|---|
| 1 editor produz ~5 artigos/dia | Sistema produz até 40 artigos/dia |
| Artigos sem metadados Yoast | Todos os artigos com Yoast completo |
| Tradução manual e lenta | Reescrita automática em minutos |
| SEO inconsistente | SEO padronizado por regras de IA |
| Sem linkagem interna sistemática | Links internos automáticos priorizados |
| Imagens sem alt text | Alt texts gerados por IA com keyword |

---

## 3. Arquitetura Completa

### Diagrama de alto nível

```
┌──────────────────────────────────────────────────────────────────┐
│                       app/main.py (Entry Point)                  │
│         APScheduler: cron job 15min · janela 9h–19h BRT          │
└───────────────────────────┬──────────────────────────────────────┘
                            │ dispara
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   app/pipeline.py                                │
│   ┌─────────────────────────┐   ┌──────────────────────────┐    │
│   │  run_pipeline_cycle()   │   │    worker_loop() [daemon] │    │
│   │  Ingestão de feeds RSS  │──▶│  Consome ArticleQueue     │    │
│   └─────────────────────────┘   └────────────┬─────────────┘    │
└────────────────────────────────────────────── │ ─────────────────┘
                                                │ process_batch()
              ┌─────────────────────────────────┼─────────────────────┐
              ▼                                 ▼                     ▼
   ┌─────────────────┐              ┌────────────────────┐  ┌──────────────────┐
   │ ContentExtractor│              │    AIProcessor     │  │  WordPressClient │
   │  (trafilatura   │              │  (Gemini API)      │  │  (REST API)      │
   │   + BS4)        │              │  + KeyPool         │  │  + Yoast SEO     │
   └────────┬────────┘              └─────────┬──────────┘  └────────┬─────────┘
            │                                 │                      │
            ▼                                 ▼                      ▼
     HTML + imagens                  JSON reescrito           Post publicado
     vídeos YouTube                  + SEO metadata           + metadados
                                     + Gutenberg blocks       + imagem
                                              │
                                     ┌────────▼────────┐
                                     │  TokenTracker   │
                                     │  (audit trail)  │
                                     └─────────────────┘

Camadas transversais:
  ├── app/store.py     → SQLite (estado dos artigos: PENDING/PROCESSING/PUBLISHED/FAILED)
  ├── app/limiter.py   → Rate limiting + rotação de chaves API
  ├── app/html_utils.py → CTA removal, Gutenberg conversion, figura validação
  ├── app/internal_linking.py → Links internos automáticos (pilar > categoria > outros)
  └── app/seo_title_optimizer.py → Otimização de títulos Google News
```

### Tecnologias utilizadas

| Camada | Tecnologia | Versão |
|---|---|---|
| Linguagem | Python | 3.11+ |
| Scheduler | APScheduler | 3.11+ |
| Extração HTML | trafilatura | 2.0+ |
| Parsing HTML | BeautifulSoup4 + lxml | 4.13+ / 5.4+ |
| IA | Google Gemini (google-genai) | 1.29+ |
| WordPress | Requests (REST API v2) | 2.32+ |
| Banco de dados | SQLite (stdlib) | — |
| ORM (modelos) | SQLAlchemy | — |
| Feed RSS | feedparser | 6.0+ |
| Imagens | Pillow | 11.3+ |
| Web Framework | Flask | 3.1+ |
| Monitoramento | psutil | 7.0+ |

---

## 4. Fluxo de Processamento Detalhado

O pipeline executa **17 etapas** sequenciais por artigo, garantindo qualidade editorial e técnica em cada fase.

### Etapa 1 — Validação de URL (`pipeline.py`)
- Verifica que a URL é `http` ou `https`
- Rejeita URLs malformadas ou vazias
- Status do artigo no DB → `PROCESSING`

### Etapa 2 — Fetch do HTML (`extractor._fetch_html`)
- `GET` com `User-Agent` configurado (Chrome 91 simulado)
- Timeout de 30 segundos
- Falha → status `FAILED`, não reprocessado

### Etapa 3 — Limpeza por domínio (`cleaners.py`)
- Cada domínio pode ter função de limpeza dedicada
- Exemplo: `globo.com` → `clean_html_for_globo_esporte()` remove blocos não jornalísticos
- Permite suporte a fontes com HTML não-padrão

### Etapa 4 — Extração de conteúdo (`extractor.extract`)
- **trafilatura** remove navegação, ads, sidebars — retorna texto editorial limpo
- **BeautifulSoup** complementa com extração de imagens, vídeos, schema.org
- Filtragem de imagens por CDN: exclui trackers (`sb.scorecardresearch.com`), avatares e imagens < 5KB
- Prioridade de imagem: CDN confiável do domínio fonte
- YouTube: detecta por padrão de URL, extrai IDs `<iframe>` embed
- Saída:
  ```json
  {
    "title": "...",
    "content": "<p>...</p>",
    "images": ["https://..."],
    "videos": ["youtube_id_1"],
    "featured_image_url": "https://...",
    "schema_original": { "@type": "NewsArticle", ... }
  }
  ```

### Etapa 5 — Reescrita com IA (`ai_processor.rewrite_batch`)
- Monta payload com: título, HTML, URL fonte, categoria, imagens, domínio WP
- Chama Gemini com `AI_SYSTEM_RULES` + `universal_prompt.txt`
- Resposta: JSON estruturado com 10+ campos de conteúdo e metadata
- Falha de quota 429 → penaliza chave, tenta outra do pool
- Falha de parsing JSON → status `QUEUED` (retry no próximo ciclo)

### Etapa 6 — Remoção de CTAs (4 camadas)
Pipeline de limpeza de "junk content" em 4 níveis progressivos:

| Camada | Método | Exemplos detectados |
|---|---|---|
| 1 | Correspondência literal normalizada | "thank you for reading", "obrigado por ler" |
| 1.5 | Regex com variações inline HTML | `<b>Thank</b> you for reading` |
| 2 | Parágrafos `<p>` inteiros com padrão CTA | `<p>Don't forget to subscribe!</p>` |
| 3 | Tags HTML vazias residuais | `<p></p>`, `<span> </span>` |
| 4 | Verificação final — **bloqueia** publicação se CTA persistir | — |

### Etapa 7 — Validação e otimização de título
**TitleValidator** verifica:
- ✅ 55–65 caracteres
- ✅ Verbo no presente (não infinitivo)
- ✅ Sem clickbait ("você não vai acreditar", "bomba")
- ✅ Sem múltiplos dois-pontos
- ✅ Começa com entidade (ator/franquia/plataforma)
- Auto-correção: encurta se > 65 chars, expande se < 55 chars

**SEO Title Optimizer** (`seo_title_optimizer.py`) aplica:
- Verbos de ação: `anuncia`, `confirma`, `revela`, `estreia`, etc.
- Remoção de palavras vagas: `talvez`, `parece`, `supostamente`
- Limpeza de entidades HTML: `&#8220;` → `"`, `&#8211;` → `-`
- Remoção de padrões clickbait explícitos

### Etapa 8 — Limpeza de HTML
Funções de `html_utils.py` em sequência:
1. `unescape_html_content()` — desescapa entidades HTML residuais da IA
2. `validate_and_fix_figures()` — corrige estrutura `<figure>`/`<figcaption>` malformada
3. `remove_broken_image_placeholders()` — remove imgs sem `src`
4. `strip_naked_internal_links()` — remove `<a>` sem contexto textual
5. `merge_images_into_content()` — injeta imagens extraídas no corpo em posições relevantes

### Etapa 9 — Upload de imagem destacada
- `is_valid_upload_candidate()` valida:
  - Extensões permitidas: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`
  - Exclui: domínios de tracking, imagens de avatar/autor
  - Exclui: imagens com dimensões ≤ 100px (via parâmetros de URL)
- HEAD request para verificar `Content-Type` e tamanho mínimo (5KB)
- Upload via `wp_client.upload_media_from_url()` → retorna `featured_media_id`

### Etapa 10 — Pós-limpeza final
- `strip_credits_and_normalize_youtube()` — normaliza embeds YouTube e remove créditos de agência
- `remove_source_domain_schemas()` — remove JSON-LD do site fonte (evita schema duplicado)
- Adiciona linha de crédito: `<p><strong>Fonte:</strong> <a href="url_original">...</a></p>`

### Etapa 11 — Categorização (`categorizer.py`)
- Categoria base: `Notícias` (ID WordPress 20)
- Por feed (`SOURCE_CATEGORY_MAP`):
  - `screenrant_movie_lists` → `Filmes` (ID 24)
  - `screenrant_movie_news` → `Filmes` (ID 24)
  - `screenrant_tv` → `Séries` (ID 21)
- Categorias sugeridas pela IA + normalização via `CATEGORY_ALIASES`

### Etapa 12 — Links internos (`internal_linking.py`)
**Sistema de priorização em 3 níveis:**

```
Nível 1 (PILAR): Posts definidos em PILAR_POSTS (config.py)
      ↓
Nível 2 (CATEGORY): Posts que compartilham categorias com o artigo atual
      ↓
Nível 3 (OTHER): Todos os outros posts do `data/internal_links.json`
```

- Dentro de cada nível: keywords ordenadas por comprimento (maior primeiro)
  → matcheia "Real Madrid Club de Fútbol" antes de "Real Madrid"
- Máximo de 6 links por artigo
- Tags excluídas do match: `a`, `h1–h6`, `blockquote`, `code`, `pre`, `figure`

### Etapa 13 — Metadados SEO (Yoast)
Campos preenchidos automaticamente:
```
_yoast_wpseo_title          → título otimizado (≤ 65 chars)
_yoast_wpseo_metadesc       → meta description (140–155 chars)
_yoast_wpseo_focuskw        → focus keyphrase principal
_yoast_news_keywords        → keywords para Google News
_yoast_wpseo_opengraph-title       → título para Open Graph (redes sociais)
_yoast_wpseo_opengraph-description → descrição para Open Graph
_yoast_wpseo_twitter-title         → título para Twitter Card
_yoast_wpseo_twitter-description   → descrição para Twitter Card
```

### Etapa 14 — Verificação final anti-CTA
- `detect_forbidden_cta(content)` — varredura final no HTML processado
- Se detectar qualquer CTA: **bloqueia** publicação, registra log de rejeição

### Etapa 15 — Conversão para Gutenberg (`html_utils.html_to_gutenberg_blocks`)
- Converte HTML padrão para formato de blocos do WordPress (Block Editor)
- Preserva: parágrafos, headings, imagens, figuras, iframes, listas
- Adiciona comentários de bloco: `<!-- wp:paragraph -->`, `<!-- wp:heading -->`, etc.

### Etapa 16 — Publicação no WordPress
1. `wp_client.create_post(payload)` → POST `/wp-json/wp/v2/posts`
2. Se `wp_post_id > 0`:
   - `update_post_yoast_seo()` → atualiza metadados Yoast + `og:image`
   - `add_google_news_meta()` → injeta meta tags para Google News  
   - `sanitize_published_post()` → sanitização final do post no WP
   - Salva JSON de debug em `debug/ai_response_{slug}_{timestamp}.json`
   - Registra tokens no `TokenTracker`
   - `db.save_processed_post()` → status `PUBLISHED`
3. Se falha → status `FAILED` + log detalhado

### Etapa 17 — Delay entre publicações
- `time.sleep(30s)` garante cadência humana entre publicações
- Evita spam na fila de revisão do WordPress
- Reduz pressão sobre rate limits da WP REST API

---

## 5. Módulos e Responsabilidades

### Mapa completo de módulos

| Módulo | Classe/Função Principal | Responsabilidade |
|---|---|---|
| `app/main.py` | `main()` | Entry point, APScheduler, inicialização |
| `app/pipeline.py` | `run_pipeline_cycle()`, `worker_loop()`, `process_batch()` | Orquestração completa |
| `app/config.py` | `PIPELINE_ORDER`, `RSS_FEEDS`, `WORDPRESS_CONFIG` | Toda a configuração centralizada |
| `app/feeds.py` | `FeedReader` | Leitura e normalização de feeds RSS |
| `app/extractor.py` | `ContentExtractor` | Extração HTML + imagens + vídeos |
| `app/ai_processor.py` | `AIProcessor.rewrite_batch()` | Reescrita com Gemini (orquestração) |
| `app/ai_client_gemini.py` | `AIClient` | Cliente Gemini (baixo nível, rotação de chaves) |
| `app/limiter.py` | `RateLimiter`, `KeyPool`, `KeySlot` | Rate limiting + pool de API keys |
| `app/wordpress.py` | `WordPressClient` | Publicação no WordPress (REST API v2) |
| `app/seo_title_optimizer.py` | `optimize_title()` | Otimização de títulos para Google News |
| `app/title_validator.py` | `TitleValidator` | Validação editorial de títulos |
| `app/html_utils.py` | 10+ funções utilitárias | Limpeza HTML, CTA removal, Gutenberg |
| `app/internal_linking.py` | `add_internal_links()` | Links internos com priorização |
| `app/cleaners.py` | `clean_html_for_globo_esporte()` | Limpadores HTML por domínio |
| `app/media.py` | `MediaHandler` | Validação e upload de imagens |
| `app/store.py` | `Database` | SQLite: artigos, estados, histórico |
| `app/task_queue.py` | `ArticleQueue` | Fila thread-safe entre ingestão e worker |
| `app/token_tracker.py` | `TokenTracker` | Rastreamento detalhado de tokens API |
| `app/token_guarantee.py` | `TokenGuarantee` | Camada dupla de proteção de tokens |
| `app/models.py` | `Movie`, `TvSeries`, `Actor`, `Genre` | Modelos ORM para Hub de Filmes/Séries |
| `app/tmdb_client.py` | `TMDbClient` | Cliente da API do The Movie Database |
| `app/content_enricher.py` | `ContentEnricher` | Enriquecimento de artigos com dados TMDB |
| `app/page_generator.py` | `MoviePageGenerator` | Geração de páginas HTML para filmes |
| `app/rss_builder.py` | `build_rss_feed()` | Constrói feeds RSS/XML a partir de artigos |
| `app/synthetic_rss.py` | `extract_links_via_jsonld()` | RSS sintético via scraping JSON-LD |
| `app/batch_processor.py` | `BatchProcessor` | Processamento em lote de artigos |
| `app/categorizer.py` | `categorize()` | Mapeamento feed → categorias WordPress |
| `app/tags.py` | `extract_tags()` | Extração de tags do conteúdo |
| `app/exceptions.py` | `AIProcessorError`, etc. | Exceções customizadas |
| `app/logging_conf.py` | `setup_logging()` | Configuração do sistema de logs |
| `app/token_bucket.py` | `TokenBucket` | Rate limiting por token bucket |
| `app/rewriter.py` | `validate_response()` | Validação e sanitização da resposta da IA |
| `universal_prompt.txt` | — | Prompt principal da IA (regras editoriais + SEO) |

---

## 6. Sistema de IA e Prompt Engineering

### Modelo utilizado

- **Modelo padrão:** `gemini-2.5-flash-lite`
- **Configuração de geração:**
  ```python
  AI_GENERATION_CONFIG = {
      'temperature': 0.7,     # Criatividade equilibrada
      'top_p': 1.0,           # Vocabulário completo disponível
      'max_output_tokens': 4096,  # ~3.000 palavras de saída
  }
  ```

### Estrutura do prompt (em camadas)

```
Camada 1: AI_SYSTEM_RULES (ai_processor.py)
  └── Regras absolutas, formato JSON obrigatório, checklist de título

Camada 2: universal_prompt.txt
  ├── Regra de Ouro: remoção de marcas concorrentes
  ├── Regra Crítica: remoção de CTAs/junk
  ├── Papel: jornalista digital sênior, especialista em cultura pop
  ├── Regras de Português obrigatórias
  ├── Regras de Conteúdo e SEO
  └── Especificação do JSON de saída (schema completo)

Camada 3: Conteúdo do artigo
  └── Título, HTML extraído, URL, categoria, imagens, vídeos
```

### JSON de saída esperado da IA

```json
{
  "titulo_final": "Título SEO em PT-BR (55–65 chars)",
  "conteudo_final": "<p>HTML jornalístico...</p><h2>...</h2>",
  "meta_description": "Resumo 140–155 chars sem CTA",
  "focus_keyphrase": "frase-chave principal",
  "related_keyphrases": ["variação 1", "sinônimo 2"],
  "slug": "url-amigavel-do-post",
  "categorias": [
    { "nome": "Marvel", "grupo": "franquias", "evidence": "trecho do texto" }
  ],
  "tags_sugeridas": ["tag-1", "tag-2", "tag-3"],
  "image_alt_texts": {
    "imagem.jpg": "Descrição com keyword para SEO e acessibilidade"
  },
  "yoast_meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "...",
    "_yoast_news_keywords": "kw1, kw2",
    "_yoast_wpseo_opengraph-title": "...",
    "_yoast_wpseo_opengraph-description": "...",
    "_yoast_wpseo_twitter-title": "...",
    "_yoast_wpseo_twitter-description": "..."
  }
}
```

### Gestão de múltiplas chaves API

```
.env:
  GEMINI_KEY_1=AIza...
  GEMINI_KEY_2=AIza...
  GEMINI_KEY_3=AIza...
  ...
  GEMINI_KEY_N=AIza...

KeyPool (limiter.py):
  ┌─────┬─────┬─────┬─────┐
  │ Key1│ Key2│ Key3│ KeyN│  ← deque rotativa
  └──┬──┴──┬──┴──┬──┴──┬──┘
     │     │     │     │
     ▼     ▼     ▼     ▼
  pronto pronto cooldown pronto
  
  → Seleção por rodízio (rotation_index)
  → Penalidade por erro 429: cooldown 30s + jitter
  → Penalidade por erro 5xx: cooldown 10s
  → Backoff exponencial: base 20s, máximo 300s
```

---

## 7. Análise de SEO Completa

### 7.1 SEO On-Page — O que o pipeline implementa

#### Títulos (Title Tags)

| Regra | Implementação | Status |
|---|---|---|
| 55–65 caracteres | `TitleValidator` + auto-correção | ✅ Implementado |
| Palavra-chave no início | `AI_SYSTEM_RULES`: "Começa com ENTIDADE" | ✅ Implementado |
| Verbo de ação no presente | `ACTION_VERBS` + validação IA | ✅ Implementado |
| Sem clickbait | `remove_clickbait()` + VAGUE_WORDS | ✅ Implementado |
| Sem entidades HTML | `clean_html_characters()` | ✅ Implementado |
| Plataforma no fim (quando relevante) | Prompt IA | ✅ Implementado |
| Maiúsculas apenas em nomes próprios | Regras de português do prompt | ✅ Implementado |

#### Meta Descriptions

| Regra | Implementação | Status |
|---|---|---|
| 140–155 caracteres | Validação no prompt da IA | ✅ Implementado |
| Contém keyword principal | Exigido no prompt | ✅ Implementado |
| Sem call-to-action | Filtrado pelo sistema anti-CTA | ✅ Implementado |
| Factual e informativa | Tom jornalístico exigido | ✅ Implementado |

#### Conteúdo

| Regra | Implementação | Status |
|---|---|---|
| Parágrafos curtos (3–4 frases) | Exigido no prompt + `html_utils` | ✅ Implementado |
| Mínimo 3 subtítulos `<h2>` | `AI_SYSTEM_RULES` | ✅ Implementado |
| Keyword no primeiro parágrafo | `AI_SYSTEM_RULES` | ✅ Implementado |
| Imagens com `<figure>` + `<figcaption>` | `validate_and_fix_figures()` | ✅ Implementado |
| Alt text com keyword | Campo `image_alt_texts` no JSON da IA | ✅ Implementado |
| Sem CTAs | 4 camadas de remoção | ✅ Implementado |
| Língua: Português-BR | Exigido no prompt | ✅ Implementado |
| Links internos priorizados | `add_internal_links()` | ✅ Implementado |
| Máx 6 links internos | Configuração de `max_links` | ✅ Implementado |

#### URLs (Slugs)

| Regra | Implementação | Status |
|---|---|---|
| URL amigável | Campo `slug` gerado pela IA | ✅ Implementado |
| Slugify no WordPress | `_slugify()` no `wordpress.py` | ✅ Implementado |
| Limite de 190 caracteres | `s.strip('-')[:190]` | ✅ Implementado |

### 7.2 SEO para Google News

O Google News tem requisitos específicos além do SEO padrão:

| Requisito Google News | Implementação | Status |
|---|---|---|
| Artigo em PT-BR | Prompt obrigatório | ✅ |
| URL única por artigo | UUID + slug | ✅ |
| Publicação datada | WordPress timestamp | ✅ |
| Byline de autor | Via WordPress | ⚠️ Depende da config WP |
| Sem conteúdo gerado por máquina sem valor editorial | Prompt jornalístico + regras rígidas | ✅ |
| Metadados `_yoast_news_keywords` | Campo do JSON de saída | ✅ |
| `add_google_news_meta()` | Meta tags específicas GN injetadas | ✅ |

### 7.3 SEO para Google Discover

| Requisito Google Discover | Implementação | Status |
|---|---|---|
| Imagem de alta qualidade (≥ 1200px) | Filtro por CDN confiável | ✅ |
| Título atraente sem clickbait | `TitleValidator` + anti-clickbait | ✅ |
| Conteúdo atualizado e relevante | RSS polling contínuo | ✅ |
| Open Graph tags | `_yoast_wpseo_opengraph-*` | ✅ |
| Twitter Card | `_yoast_wpseo_twitter-*` | ✅ |

### 7.4 SEO Técnico

| Aspecto Técnico | Implementação | Status |
|---|---|---|
| Sitemap XML | `validate_news_sitemap.py` + `WPCODE_NEWS_SITEMAP_ENHANCEMENT.php` | ✅ |
| Canonical URL | URL original da fonte como canonical | ✅ |
| Structured Data (Schema.org) | Extraído da fonte + reprocessado | ✅ (ver Seção 8) |
| Gutenberg Blocks | `html_to_gutenberg_blocks()` | ✅ |
| RSS Feed próprio | `rss_builder.py` | ✅ |
| Feed em PT-BR | `fg.language("pt-BR")` no `rss_builder.py` | ✅ |

### 7.5 Análise de keywords e keyphrases

O sistema gera automaticamente:
- **1 focus_keyphrase**: frase curta e natural, máx 60 chars
- **2–5 related_keyphrases**: variações e sinônimos
- **_yoast_news_keywords**: lista CSV das keywords principais

**Padrão de qualidade exigido:**
- Keyphrases alinhadas com o texto (não genéricas)
- Evita termos em inglês (exceto nomes próprios internacionais)
- Coerência entre focus_keyphrase e conteúdo do artigo

### 7.6 Pontuação SEO estimada (Yoast verde)

Com as regras implementadas, os artigos gerados devem atingir:

| Critério Yoast | Status Esperado |
|---|---|
| Keyphrase in SEO title | 🟢 Verde |
| Keyphrase in first paragraph | 🟢 Verde |
| Keyphrase density | 🟢 Verde |
| Meta description length | 🟢 Verde |
| Image alt attributes | 🟢 Verde |
| Internal links | 🟢 Verde |
| Text length | 🟢 Verde (artigos ≥ 300 palavras) |
| Subheadings (H2) | 🟢 Verde (mínimo 3) |
| Sentence length | 🟡 Amarelo (depende da resposta da IA) |
| Paragraph length | 🟢 Verde (máx 3–4 frases) |

---

## 8. Análise de Schema e Dados Estruturados

### 8.1 Extração de Schema original

O `ContentExtractor` extrai o JSON-LD original da fonte:

```python
# extractor.py — extração de schema.org
schema_data = {
    "@type": "NewsArticle",
    "headline": "...",
    "datePublished": "...",
    "author": { "@type": "Person", "name": "..." },
    "publisher": { "@type": "Organization", "name": "..." },
    "image": { "@type": "ImageObject", "url": "..." }
}
```

O schema da fonte é extraído via `extract_links_via_jsonld()` (`synthetic_rss.py`), que detecta tipos:
- `NewsArticle`
- `BlogPosting`
- `Article`
- `ItemList`

### 8.2 Schema removido na publicação

O `remove_source_domain_schemas()` **remove o JSON-LD da fonte** do conteúdo antes de publicar. Isso é correto porque:
1. O WordPress (via Yoast SEO) gera o próprio schema do post
2. Manter o schema da fonte causaria duplicação e confusão de autoria

### 8.3 Schema recomendado para o portal (o que Yoast gera)

O WordPress com Yoast gera automaticamente:

```json
{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "Título do artigo (≤ 110 chars)",
  "description": "Meta description (140–155 chars)",
  "image": {
    "@type": "ImageObject",
    "url": "https://maquinanerd.com.br/wp-content/uploads/...",
    "width": 1200,
    "height": 630
  },
  "datePublished": "2026-03-06T10:00:00-03:00",
  "dateModified": "2026-03-06T10:00:00-03:00",
  "author": {
    "@type": "Person",
    "name": "Nome do Autor"
  },
  "publisher": {
    "@type": "Organization",
    "name": "MaquinaNerd",
    "logo": {
      "@type": "ImageObject",
      "url": "https://maquinanerd.com.br/logo.png"
    }
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://maquinanerd.com.br/post-slug/"
  }
}
```

### 8.4 Lacunas de Schema identificadas

| Schema | Status | Recomendação |
|---|---|---|
| `NewsArticle` (Yoast) | ✅ Automático via Yoast | Verificar se Yoast está configurado corretamente |
| `BreadcrumbList` | ✅ Yoast gera automaticamente | — |
| `FAQPage` | ❌ Não implementado | Adicionar para artigos de lista/guia |
| `VideoObject` | ⚠️ Parcial (iframes YouTube) | Complementar com schema VideoObject explícito |
| `Movie` / `TVSeries` | ❌ Não implementado | Alta prioridade — usar dados do TMDb |
| `Review` / `AggregateRating` | ❌ Não implementado | Para artigos de review de filmes/games |
| `Person` (atores/diretores) | ❌ Não implementado | Enriquecer com TMDb |
| `Event` (lançamentos) | ❌ Não implementado | Para cobertura de estreias/premiações |

### 8.5 Schema para Hub de Filmes e Séries (`models.py`)

O projeto contém modelos ORM para um hub de filmes e séries com dados do TMDb:

```python
# Modelos disponíveis em app/models.py
Movie       → filme com gêneros, atores, TMDb ID, ratings
TvSeries    → série com gêneros, atores, TMDb ID
Actor       → ator/atriz com biography, birth_date, popularity
Genre       → gênero cinematográfico
```

**Schema recomendado para páginas do hub:**

```json
{
  "@type": "Movie",
  "name": "Nome do Filme",
  "description": "Sinopse",
  "datePublished": "2025-01-01",
  "genre": ["Ação", "Aventura"],
  "actor": [
    { "@type": "Person", "name": "Ator Principal" }
  ],
  "director": { "@type": "Person", "name": "Diretor" },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 8.5,
    "ratingCount": 10000
  }
}
```

### 8.6 Validação de Schema

Para validar o schema gerado pelo portal:
1. **Google Rich Results Test:** `https://search.google.com/test/rich-results`
2. **Schema.org Validator:** `https://validator.schema.org/`
3. **Google Search Console:** aba Melhorias → Resultados avançados

---

## 9. Análise de Performance e Rate Limiting

### 9.1 Rate Limiting da API Gemini

```
RateLimiter:
  min_interval_s = 60s  (1 RPM conservador)
  jitter         = 0–5s  (aleatório para evitar picos)

KeyPool:
  rotação: rodízio circular entre chaves disponíveis
  penalidade 429: cooldown 30s + jitter 0–2s
  penalidade 5xx: cooldown 10s
  backoff exponencial: 20s base → 300s máximo
```

### 9.2 Throughput do pipeline

| Fase | Tempo estimado |
|---|---|
| Fetch RSS + filtragem | ~2–5s por feed |
| Fetch HTML do artigo | ~3–10s por artigo |
| Extração (trafilatura) | ~1–2s por artigo |
| Chamada Gemini API | ~15–45s por artigo |
| Upload imagem (WP) | ~5–15s por imagem |
| Publicação no WordPress | ~3–8s por artigo |
| Delay entre publicações | 30s fixo |
| **Total por artigo** | **~60–115s** |

### 9.3 Thread model

```
Thread Principal (main):
  └── APScheduler job → run_pipeline_cycle() (a cada 15min)
      └── FeedReader → articlesQueue.push_many()

Thread Daemon (worker_loop):
  └── poll ArticleQueue (timeout 30s)
      └── process_batch([article])
          ├── ContentExtractor
          ├── AIProcessor (Gemini API)
          └── WordPressClient
```

### 9.4 Circuit Breaker por feed

```python
# Proteção contra feeds com falhas repetitivas
if feed_failures[source_id] >= 3:
    logger.warning(f"Circuit breaker aberto para {source_id} — pulando")
    continue
```

---

## 10. Banco de Dados e Persistência

### 10.1 Estrutura do SQLite (`app/store.py`)

```sql
-- Tabela principal: artigos vistos e processados
CREATE TABLE seen_articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    TEXT NOT NULL,         -- ex: 'screenrant_movie_news'
    external_id  TEXT NOT NULL,         -- hash SHA-256 da URL
    url          TEXT,
    status       TEXT NOT NULL,         -- PENDING|PROCESSING|QUEUED|PUBLISHED|FAILED
    published_at DATETIME,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 10.2 Ciclo de vida de um artigo

```
NOVO (não existe no DB)
    │
    ▼
PENDING (inserido pelo FeedReader)
    │
    ▼
PROCESSING (início do process_batch)
    │
    ├──[sucesso]──▶ PUBLISHED
    │
    ├──[falha IA]──▶ QUEUED (reprocessado no próximo ciclo)
    │
    └──[erro fatal]──▶ FAILED (não reprocessado)
```

### 10.3 Deduplicação

- Hash SHA-256 da URL do artigo
- Verificado antes de enfileirar: `db.filter_new_articles()`
- Artigos `PUBLISHED` nunca são reprocessados
- Artigos `FAILED` também não reentram na fila (evita loops)

### 10.4 Modelos ORM do Hub (`models.py` com SQLAlchemy)

```
movies              → filmes (id, tmdb_id, title, description, rating, poster_url)
tv_series           → séries (id, tmdb_id, title, seasons, status)
actors              → atores (id, tmdb_id, name, biography, popularity)
genres              → gêneros (id, name, slug)
movie_genre_association   → M2M filmes ↔ gêneros
tv_genre_association      → M2M séries ↔ gêneros
actor_movie_association   → M2M atores ↔ filmes
actor_tv_association      → M2M atores ↔ séries
```

---

## 11. Rastreamento de Tokens

### 11.1 TokenTracker (`app/token_tracker.py`)

Registra **cada** chamada à API Gemini com:
- `prompt_tokens` (entrada)
- `completion_tokens` (saída)
- `total_tokens`
- Modelo utilizado
- Timestamp ISO
- Operação realizada

**Arquivos de log gerados:**
```
logs/tokens/
  ├── tokens_2026-03-06.jsonl    ← log diário linha por linha
  ├── token_stats.json           ← estatísticas acumuladas
  └── token_debug.log            ← debug de chamadas
```

### 11.2 TokenGuarantee (`app/token_guarantee.py`)

Camada dupla de proteção com 3 níveis:
1. **Log de garantia** — arquivo de backup independente
2. **Arquivo diário JSONL** — linha por linha com timestamp
3. **Log de auditoria** — timestamp ISO para cada registro

**Validações obrigatórias:**
- Tokens negativos → rejeitados
- Tokens não-numéricos → rejeitados com log de erro

### 11.3 Estimativa de custo

Com o modelo `gemini-2.5-flash-lite`:
- Input: ~$0.075 por 1M tokens
- Output: ~$0.30 por 1M tokens
- Por artigo (estimativa): ~2.000–4.000 tokens de input + ~1.500–3.000 output
- **Custo estimado por artigo: $0.001–$0.002**
- **Custo diário (40 artigos): ~$0.04–$0.08**

---

## 12. Integrações Externas

### 12.1 Google Gemini API

- **Endpoint:** `generativelanguage.googleapis.com`
- **Modelo:** `gemini-2.5-flash-lite` (padrão)
- **Autenticação:** API Key (rotação automática via KeyPool)
- **Configuração:** `.env` com chaves `GEMINI_KEY_*` ou `GEMINI_API_*`

### 12.2 WordPress REST API v2

- **Endpoints utilizados:**
  - `POST /wp-json/wp/v2/posts` — criar post
  - `POST /wp-json/wp/v2/media` — upload de mídia
  - `GET /wp-json/wp/v2/tags?search=` — buscar tag existente
  - `POST /wp-json/wp/v2/tags` — criar nova tag
  - `POST /wp-json/wp/v2/posts/{id}` — atualizar metadados Yoast
- **Autenticação:** Basic Auth (usuário + Application Password do WP)

### 12.3 The Movie Database (TMDb API v3)

- **Base URL:** `https://api.themoviedb.org/3`
- **Endpoints:**
  - `/search/movie` — busca filmes
  - `/search/tv` — busca séries
  - `/movie/{id}` — detalhes do filme
  - `/tv/{id}` — detalhes da série
  - `/person/{id}` — detalhes de ator
- **Configuração:** `TMDB_API_KEY` no `.env`

### 12.4 Feeds RSS monitorados

| Feed ID | URL | Categoria WP |
|---|---|---|
| `screenrant_movie_lists` | `https://screenrant.com/feed/movie-lists/` | Filmes (ID 24) |
| `screenrant_movie_news` | `https://screenrant.com/feed/movie-news/` | Filmes (ID 24) |
| `screenrant_tv` | `https://screenrant.com/feed/tv/` | Séries (ID 21) |

### 12.5 Categorias WordPress mapeadas

| Nome | ID WordPress |
|---|---|
| Notícias | 20 |
| Filmes | 24 |
| Séries | 21 |
| Games | 73 |

---

## 13. Instalação e Configuração

### 13.1 Pré-requisitos

- Python 3.11 ou superior
- Acesso à internet (APIs externas)
- WordPress com REST API habilitada
- Plugin Yoast SEO instalado no WordPress
- Conta Google Cloud com acesso à Gemini API

### 13.2 Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/maquinanerd/TheNerdMN.git
cd TheNerdMN

# 2. Crie o ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. Instale as dependências
make install
# ou: pip install -r requirements.txt

# 4. Configure o arquivo .env
copy app\keys.example.py app\keys.py   # Windows
# cp app/keys.example.py app/keys.py  # Linux

# 5. Edite o .env e preencha todas as variáveis (ver Seção 14)

# 6. Inicialize o banco de dados
python -c "from app.store import Database; Database()"

# 7. Inicie o pipeline
python main.py
# ou: StartMN.bat (Windows)
# ou: INICIAR_PIPELINE.bat (Windows, com auto-início)
```

### 13.3 Inicialização automática (Windows)

Use o `CONFIGURAR_AUTO_INICIAR.bat` para configurar o pipeline para iniciar automaticamente com o Windows via Agendador de Tarefas.

---

## 14. Variáveis de Ambiente

### Arquivo `.env` completo

```ini
# ================================
# GOOGLE GEMINI API
# ================================
GEMINI_KEY_1=AIza...
GEMINI_KEY_2=AIza...
GEMINI_KEY_3=AIza...
# Adicione quantas chaves precisar: GEMINI_KEY_N=...

# Modelo da IA (padrão: gemini-2.5-flash-lite)
AI_MODEL=gemini-2.5-flash-lite

# ================================
# WORDPRESS
# ================================
WORDPRESS_URL=https://maquinanerd.com.br/wp-json/wp/v2
WORDPRESS_USER=seu_usuario
WORDPRESS_PASSWORD=sua_application_password

# ================================
# TMDB (opcional - Hub de Filmes)
# ================================
TMDB_API_KEY=sua_chave_tmdb

# ================================
# CONTROLE DO PIPELINE
# ================================
MAX_PER_FEED_CYCLE=3      # Máx artigos por feed por ciclo
MAX_PER_CYCLE=10          # Máx artigos por ciclo total
ARTICLE_SLEEP_S=120       # Delay entre ciclos (segundos)
BETWEEN_BATCH_DELAY_S=30  # Delay entre batches
BETWEEN_PUBLISH_DELAY_S=30 # Delay entre publicações

# ================================
# RATE LIMITING DA API
# ================================
AI_MIN_INTERVAL_S=6       # Intervalo mínimo entre chamadas (segundos)
BACKOFF_BASE_S=20         # Backoff base para retry
BACKOFF_MAX_S=300         # Backoff máximo
```

---

## 15. Operação e Monitoramento

### 15.1 Scripts de operação

| Script | Função |
|---|---|
| `StartMN.bat` | Inicia o pipeline principal |
| `INICIAR_PIPELINE.bat` | Inicia com verificações |
| `CONFIGURAR_AUTO_INICIAR.bat` | Configura auto-start no Windows |
| `VALIDAR_CTA_REMOVAL.bat` | Valida se remoção de CTAs está funcionando |
| `dashboard_server.py` | Servidor web do dashboard de monitoramento |
| `dashboard.py` | Dashboard de estatísticas |
| `token_dashboard.py` | Dashboard específico de tokens API |
| `token_validator.py` | Valida integridade dos logs de tokens |
| `test_token_system.py` | Testes do sistema de tokens |

### 15.2 Estrutura de logs

```
logs/
  ├── pipeline.log          ← log principal do pipeline
  ├── errors.log            ← apenas erros críticos
  └── tokens/
      ├── tokens_YYYY-MM-DD.jsonl  ← uso de tokens por dia
      ├── token_stats.json         ← estatísticas acumuladas
      ├── token_debug.log          ← debug detalhado
      ├── token_guarantee.log      ← log de garantia (backup)
      ├── token_emergency.log      ← emergências
      └── token_audit.log          ← auditoria com timestamp

debug/
  └── ai_response_{slug}_{timestamp}.json  ← resposta bruta da IA por artigo
```

### 15.3 Monitoramento de saúde do pipeline

Indicadores a monitorar:
- **Taxa de sucesso (PUBLISHED/tentativas):** alvo ≥ 90%
- **Taxa de CTA bloqueados:** alvo ≤ 5% (indica qualidade da IA)
- **Tokens por artigo:** monitorar creep de custo
- **Tempo de ciclo:** alvo < 10min para 10 artigos
- **Erros 429 (quota):** aumentar número de chaves se frequente

---

## 16. Tratamento de Erros e Resiliência

### 16.1 Estratégias de retry

| Tipo de erro | Estratégia |
|---|---|
| Erro de rede (extrator) | Falha imediata → `FAILED` (não reprocessado no ciclo atual) |
| Timeout na extração | `FAILED` + log |
| Erro 429 Gemini | Penaliza chave, troca para próxima, backoff exponencial |
| Erro 5xx Gemini | Penaliza chave por 10s, tenta outra |
| JSON inválido da IA | Status `QUEUED` → retry no próximo ciclo |
| CTA detectado no final | `FAILED` + log de rejeição |
| Falha no upload de imagem | Continua publicação sem imagem destacada |
| Erro 400 WP (tag duplicada) | Race condition handler → re-busca ID da tag |

### 16.2 Circuit breaker por feed

- Após 3 falhas consecutivas no mesmo feed: feed ignorado no ciclo atual
- Protege contra feeds temporariamente indisponíveis ou com HTML quebrado

### 16.3 Proteção de dados

- Banco de dados SQLite com `timeout=10` para evitar deadlocks
- `conn.row_factory = sqlite3.Row` para acesso seguro por nome de coluna
- `db_file.parent.mkdir(parents=True, exist_ok=True)` → cria diretório se não existe
- JSON de debug salvo antes de confirmar publicação (rollback manual possível)

---

## 17. Análise de Qualidade e Pontos de Melhoria

### 17.1 Pontos fortes do sistema

✅ **SEO completo e automatizado** — 20+ campos de metadados preenchidos por artigo  
✅ **Remoção robusta de CTAs** — 4 camadas com fallback de rejeição  
✅ **Prompt engineering maduro** — regras gramaticais, editoriais e de SEO no mesmo prompt  
✅ **Resiliência da API** — rotação de chaves + backoff + circuit breaker  
✅ **Rastreamento de tokens duplo** — TokenTracker + TokenGuarantee  
✅ **Links internos inteligentes** — priorização por posts-pilar  
✅ **Imagens validadas** — HEAD request + filtro por CDN + filtro de tamanho  
✅ **Limpeza HTML profunda** — domain-specific cleaners + utilitários genéricos  

### 17.2 Lacunas e oportunidades de melhoria

#### Alta prioridade

| Item | Descrição | Impacto |
|---|---|---|
| Schema `Movie`/`TVSeries` | Implementar schema.org para páginas do Hub (dados TMDb disponíveis) | SEO alto |
| Schema `VideoObject` | Completar schema para embeds YouTube | SEO médio |
| Testes automatizados | Expandir cobertura de testes (apenas `test_token_system.py` existe) | Qualidade |
| `data/internal_links.json` | Atualizar automaticamente com novos posts publicados | Performance de linking |
| Webhook de publicação | Notificar sistemas externos após publicação | Integração |

#### Média prioridade

| Item | Descrição | Impacto |
|---|---|---|
| Mais feeds RSS | Adicionar IGN, Variety, Hollywood Reporter, etc. | Volume de conteúdo |
| Schema `FAQPage` | Para artigos tipo lista/guia | SEO nicho |
| Dashboard web completo | `dashboard_server.py` parece incompleto | Observabilidade |
| Rotação automática de `internal_links.json` | Atualizar JSON com posts novos via WP API | SEO linking |
| Detecção de duplicate content | Verificar similaridade semântica antes de publicar | Qualidade |

#### Baixa prioridade

| Item | Descrição | Impacto |
|---|---|---|
| Suporte a mais idiomas | Artigos originais em espanhol, etc. | Volume |
| Cache de fetching | Redis/memcache para HTML extraído recentemente | Performance |
| Métricas de clique (CTR) | Integrar Google Search Console API | Analytics |
| A/B test de títulos | Testar variações de título para otimizar CTR | SEO |

### 17.3 Dívida técnica identificada

1. **`README.md` vs código:** O README original menciona feeds de Economia/Política, mas o código atual processa Filmes/Séries (ScreenRant). Documentação desatualizada.
2. **`requirements.txt` vs `pyproject.toml`:** Dois arquivos de dependências com listas divergentes. Consolidar em apenas um.
3. **`app/logging_conf.py` e `app/logging_config.py`:** Dois arquivos de configuração de logging. Eliminar duplicata.
4. **`data/internal_links.json`:** Atualização manual. Deveria ser populado automaticamente.
5. **`PILAR_POSTS` vazia em `config.py`:** Lista de posts-pilar está vazia, o que invalida o nível 1 do sistema de linkagem interna.

---

## 18. Análise de Segurança OWASP

### 18.1 A01 — Broken Access Control

| Ponto | Status | Observação |
|---|---|---|
| WordPress Basic Auth | ⚠️ Risco médio | Usar Application Password (não senha principal) — **JÁ IMPLEMENTADO** |
| Variáveis de ambiente em `.env` | ✅ Correto | `.env` não deve ser commitado no git |
| API Keys no `.env` | ✅ Correto | `keys.example.py` fornecido (sem valores reais) |

### 18.2 A02 — Cryptographic Failures

| Ponto | Status | Observação |
|---|---|---|
| HTTPS para WordPress URL | ✅ Exigido | `WORDPRESS_URL` deve ser HTTPS |
| HTTPS para feeds RSS | ✅ ScreenRant usa HTTPS | — |
| HTTPS para Gemini API | ✅ Automático (SDK Google) | — |
| Armazenamento de chaves | ⚠️ Plaintext no `.env` | Considerar vault para produção de alta escala |

### 18.3 A03 — Injection

| Ponto | Status | Observação |
|---|---|---|
| SQL Injection (SQLite) | ✅ Parametrizado | Usa `?` placeholders em todas as queries |
| HTML Injection (conteúdo da IA) | ✅ Sanitizado | `html_utils.py` valida e limpa o HTML |
| Script Injection (tags WP) | ✅ `_slugify()` | Remove caracteres não-alfanuméricos |
| Command Injection | ✅ Não executa comandos externos | — |

### 18.4 A05 — Security Misconfiguration

| Ponto | Status | Observação |
|---|---|---|
| Debug files públicos | ⚠️ Atenção | Pasta `debug/` com JSON bruto da IA não deve ser servida publicamente |
| Logs com dados sensíveis | ⚠️ Atenção | Logs registram partes de chaves de API (últimos 4 chars) |
| User-Agent genérico | ✅ OK | Usa Chrome genérico — evita bloqueios por bot detection |

### 18.5 A10 — Server-Side Request Forgery (SSRF)

| Ponto | Status | Observação |
|---|---|---|
| URLs de imagens (upload WP) | ⚠️ Risco potencial | `is_valid_upload_candidate()` filtra por extensão, mas não valida domínio de destino |
| URLs de feeds RSS | ✅ Hardcoded em `config.py` | Não aceita URLs externas dinâmicas |
| `_fetch_html()` | ⚠️ Potencial | URL vem do feed RSS — confiança na fonte. Filtro por `http/https` existe |

**Recomendação:** Para `upload_media_from_url()`, adicionar allowlist de domínios de CDN permitidos.

---

## 19. Roadmap e Versões Futuras

### v2.1 — Qualidade e Schema (curto prazo)
- [ ] Implementar schema.org `Movie` e `TVSeries` nas páginas do Hub
- [ ] Completar `data/internal_links.json` com atualização automática via WP API
- [ ] Popular `PILAR_POSTS` com as URLs dos artigos mais importantes
- [ ] Testes unitários para `html_utils.py`, `seo_title_optimizer.py`, `internal_linking.py`
- [ ] Consolidar `requirements.txt` e `pyproject.toml`

### v2.2 — Expansão de fontes (médio prazo)
- [ ] Adicionar feeds: IGN, Variety, The Hollywood Reporter, Polygon
- [ ] Suporte a feeds em espanhol (fontes latino-americanas)
- [ ] Sistema de `content_enricher.py` integrado ao pipeline principal (TMDb dados nos artigos)

### v2.3 — Analytics e otimização (médio prazo)
- [ ] Integração Google Search Console API (CTR por artigo)
- [ ] Dashboard web completo (métricas de publicação, tokens, CTR)
- [ ] A/B testing de títulos com análise de CTR
- [ ] Detector de duplicate content semântico (embeddings)

### v3.0 — Plataforma completa (longo prazo)
- [ ] API REST própria para gerenciar o pipeline
- [ ] Interface web de edição antes de publicar
- [ ] Suporte a vídeo-artigos (Shorts/Reels gerados por IA)
- [ ] Multi-portal (múltiplos WordPress com configuração por portal)
- [ ] Integração direta com Google Ads para artigos monitorados

---

## 20. Glossário Técnico

| Termo | Definição |
|---|---|
| **APScheduler** | Biblioteca Python para agendamento de tarefas (cron jobs) |
| **Application Password** | Senha de aplicação do WordPress (diferente da senha do usuário) |
| **Backoff exponencial** | Estratégia de retry com espera crescente: 20s, 40s, 80s... até max |
| **Canonical URL** | URL preferida que o Google deve indexar (evita duplicate content) |
| **Circuit Breaker** | Padrão de resiliência: para requisições a um serviço com muitas falhas |
| **CTA (Call-to-Action)** | Frases que incentivam ação do leitor (ex.: "Clique aqui", "Assine") |
| **Focus Keyphrase** | Palavra-chave principal para a qual o artigo é otimizado (Yoast) |
| **Gutenberg Blocks** | Formato de conteúdo em blocos do WordPress Block Editor |
| **JSON-LD** | Formato JavaScript Object Notation for Linked Data (schema.org) |
| **KeyPool** | Pool de chaves de API com rotação e controle de cooldown |
| **OG (Open Graph)** | Protocolo de metadados para compartilhamento em redes sociais |
| **Pilar Posts** | Artigos mais importantes do site, target prioritário de links internos |
| **Rate Limiting** | Controle da frequência de chamadas a uma API |
| **RSS** | Really Simple Syndication — formato XML para distribuição de conteúdo |
| **Schema.org** | Vocabulário de dados estruturados para web semântica |
| **Slug** | Parte da URL amigável de um post: `maquinanerd.com.br/slug-do-artigo/` |
| **SQLite** | Banco de dados relacional embutido, sem servidor |
| **trafilatura** | Biblioteca Python para extração de conteúdo editorial de páginas HTML |
| **TMDb** | The Movie Database — base de dados de filmes, séries e pessoas |
| **Token (IA)** | Unidade de processamento da IA (~0.75 palavras em inglês) |
| **WPCODE** | Plugin WordPress para injeção de código personalizado |
| **Yoast SEO** | Plugin WordPress para otimização de SEO |
| **Jitter** | Variação aleatória adicionada aos timers para evitar picos simultâneos |

---

## Referências

- [Google News Publisher Center — Políticas de conteúdo](https://support.google.com/news/publisher-center/answer/6204050)
- [Google Search Central — Structured Data (schema.org)](https://developers.google.com/search/docs/appearance/structured-data)
- [Yoast SEO — Technical docs](https://developer.yoast.com/)
- [WordPress REST API Handbook](https://developer.wordpress.org/rest-api/)
- [Google Gemini API Docs](https://ai.google.dev/api)
- [TMDb API Documentation](https://developer.themoviedb.org/docs)
- [trafilatura Documentation](https://trafilatura.readthedocs.io/)
- [Schema.org — NewsArticle](https://schema.org/NewsArticle)
- [Schema.org — Movie](https://schema.org/Movie)
- [OWASP Top 10 — 2021](https://owasp.org/www-project-top-ten/)

---

*Documentação gerada em 06 de março de 2026 | MaquinaNerd Pipeline v2.0*
