# Documentação Técnica do Pipeline — MaquinaNerd

> **Versão:** 1.0 | **Data:** Março de 2026  
> **Projeto:** TheNews_MaquinaNerd — Automação de conteúdo RSS → IA → WordPress

---

## Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Fluxo Completo de Processamento](#3-fluxo-completo-de-processamento)
4. [Componentes do Sistema](#4-componentes-do-sistema)
5. [APIs Utilizadas](#5-apis-utilizadas)
6. [Prompts Utilizados pela IA](#6-prompts-utilizados-pela-ia)
7. [Estrutura de Dados](#7-estrutura-de-dados)
8. [Sistema de Agendamento](#8-sistema-de-agendamento)
9. [Tratamento de Erros](#9-tratamento-de-erros)
10. [Logs e Monitoramento](#10-logs-e-monitoramento)
11. [Melhorias Futuras](#11-melhorias-futuras)

---

## 1. Visão Geral do Sistema

### Objetivo

O pipeline MaquinaNerd é uma automação de produção de conteúdo jornalístico para o portal **maquinanerd.com.br**. Ele resolve o problema de escalar a produção de notícias de entretenimento (filmes, séries, games) sem aumentar a equipe editorial.

### Como funciona em resumo

```
Feeds RSS (ScreenRant)
        ↓
  Leitura e filtragem
        ↓
  Extração do artigo original (HTML scraping)
        ↓
  Reescrita com IA — Gemini (português + SEO)
        ↓
  Limpeza, validação e otimização de título
        ↓
  Publicação no WordPress com metadados Yoast SEO
```

### Problema resolvido

Sites internacionais publicam dezenas de notícias por dia em inglês. O pipeline:
1. Monitora os feeds RSS dessas fontes continuamente.
2. Baixa e extrai o artigo original.
3. Reescreve em português jornalístico fluente usando Gemini.
4. Otimiza para SEO (Google News / Google Discover).
5. Publica automaticamente no WordPress, com imagem destacada, categorias, tags e metadados Yoast.

---

## 2. Arquitetura do Sistema

### Visão de alto nível

```
┌─────────────────────────────────────────────────────────────┐
│                        app/main.py                          │
│   Entry point ─ configura logging, DB, APScheduler         │
└────────────────────────┬────────────────────────────────────┘
                         │  dispara a cada 15 min (9h–19h BRT)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              app/pipeline.py — run_pipeline_cycle()         │
│   Lê RSS → filtra novos → enfileira artigos                 │
└────────────────────────┬────────────────────────────────────┘
                         │  enfileira em ArticleQueue (thread-safe)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          app/pipeline.py — worker_loop() [thread daemon]    │
│   Consome fila → chama process_batch()                      │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────────────┐
          ▼              ▼                       ▼
    ContentExtractor  AIProcessor          WordPressClient
    (trafilatura)     (Gemini API)         (REST API)
          │              │                       │
          ▼              ▼                       ▼
    HTML extraído    JSON reescrito        Post publicado
    + imagens        + SEO metadata        + Yoast meta
                         │
                    TokenTracker
                    (logs de uso)
```

### Componentes principais e responsabilidades

| Módulo | Responsabilidade |
|---|---|
| `app/main.py` | Entry point, scheduler APScheduler, inicialização do DB |
| `app/pipeline.py` | Orquestração completa do pipeline (ingestão, fila, processamento) |
| `app/config.py` | Toda configuração centralizada (feeds, WP, IA, schedule) |
| `app/feeds.py` | Leitura e normalização de feeds RSS/Sitemap |
| `app/extractor.py` | Extração de conteúdo HTML com trafilatura + BeautifulSoup |
| `app/ai_processor.py` | Reescrita de artigos via Gemini — orquestra chamadas de IA |
| `app/ai_client_gemini.py` | Cliente Gemini com rotação de chaves e backoff automático |
| `app/limiter.py` | Rate limiting + pool de chaves de API |
| `app/wordpress.py` | Cliente WordPress REST API (criar post, upload de mídia, Yoast) |
| `app/seo_title_optimizer.py` | Otimiza títulos para Google News / Discovery |
| `app/title_validator.py` | Valida regras editoriais do título (tamanho, clickbait, etc.) |
| `app/html_utils.py` | Utilitários HTML: CTA removal, Gutenberg blocks, figuras |
| `app/internal_linking.py` | Injeção de links internos com priorização por posts-pilar |
| `app/cleaners.py` | Limpadores HTML específicos por domínio (ex: Globo Esporte) |
| `app/media.py` | Validação e upload de imagens via URLs |
| `app/store.py` | Banco de dados SQLite — persiste artigos e status |
| `app/task_queue.py` | Fila thread-safe de artigos entre ingestão e processamento |
| `app/token_tracker.py` | Rastreamento de tokens consumidos por chamada de API |
| `app/token_guarantee.py` | Camada dupla de proteção de tokens |
| `app/exceptions.py` | Exceções customizadas do projeto |
| `universal_prompt.txt` | Prompt principal da IA (papel de jornalista, regras SEO) |

---

## 3. Fluxo Completo de Processamento

### Fase 1 — Ingestão (run_pipeline_cycle)

```
1. APScheduler dispara run_pipeline_cycle() a cada 15 minutos (entre 9h–19h BRT)

2. Para cada feed em PIPELINE_ORDER (config.py):
   a. Verifica circuit breaker: se >= 3 falhas consecutivas, pula o feed
   b. Chama FeedReader.read_feeds() → lista de itens RSS normalizados
   c. Chama db.filter_new_articles() → remove artigos já processados
   d. Aplica limite: máx 3 por feed / máx 10 por ciclo (MAX_PER_FEED_CYCLE / MAX_PER_CYCLE)
   e. Enfileira artigos em ArticleQueue

3. Aguarda 45s entre feeds (FEED_STAGGER_S) para não sobrecarregar

4. Fecha conexão com DB
```

### Fase 2 — Processamento (worker_loop + process_batch)

O `worker_loop()` roda em uma thread daemon em paralelo à ingestão.

```
1. worker_loop() faz polling da ArticleQueue com timeout de 30s
2. Se encontrar artigo, verifica limite de 10 requisições por ciclo (RPM protection)
   → Se atingir o limite: pausa 5 minutos antes de continuar
3. Chama process_batch([artigo])
```

### Fase 3 — process_batch (o coração do pipeline)

Cada artigo passa pelas seguintes etapas em sequência:

```
ETAPA 1 — Validação de URL
  - Verifica que a URL é válida (http/https)
  - Status → PROCESSING no banco

ETAPA 2 — Fetch HTML
  - extractor._fetch_html(url) — GET com User-Agent configurado
  - Se falhar: status → FAILED

ETAPA 3 — Limpeza por domínio
  - Verifica se o domínio tem cleaner específico (CLEANER_FUNCTIONS)
  - Ex: 'globo.com' → clean_html_for_globo_esporte()

ETAPA 4 — Extração de conteúdo
  - extractor.extract(html, url) via trafilatura + BeautifulSoup
  - Extrai: title, content (texto limpo), images, videos, featured_image_url, schema_original
  - Se content vazio: status → FAILED

ETAPA 5 — Reescrita com IA (AIProcessor.rewrite_batch)
  - Monta payload: título, html, URL fonte, categoria, imagens, vídeos, domínio WP
  - Chama Gemini API com o universal_prompt.txt + AI_SYSTEM_RULES
  - Resposta esperada: JSON com campos titulo_final, conteudo_final, meta, SEO, etc.
  - Se falhar: status → QUEUED (retry no próximo ciclo)

ETAPA 6 — Remoção de CTAs (4 camadas)
  Camada 1: remoção literal de frases exatas ("Thank you for reading...")
  Camada 1.5: regex flexível para variações com formatação inline
  Camada 2: remoção de parágrafos <p> inteiros com padrões de CTA
  Camada 3: remoção de tags HTML vazias deixadas para trás
  Camada 4: verificação final — se ainda houver CTA, REJEITA o artigo

ETAPA 7 — Validação e otimização de título
  - TitleValidator.validate() — verifica: tamanho (55–65 chars), verbo no presente,
    sem clickbait, sem múltiplos dois-pontos
  - Auto-correção: encurta se muito longo, expande se muito curto
  - optimize_title() — SEO para Google News (ação, número, contexto temporal)

ETAPA 8 — Limpeza de HTML
  - unescape_html_content() — desescapa entidades HTML da IA
  - validate_and_fix_figures() — corrige estruturas <figure>/<figcaption>
  - remove_broken_image_placeholders() — remove placeholders quebrados
  - strip_naked_internal_links() — remove links sem contexto
  - merge_images_into_content() — injeta imagens extraídas no corpo

ETAPA 9 — Upload de imagem destacada
  - Verifica URL da imagem principal (is_valid_upload_candidate)
  - wp_client.upload_media_from_url() → retorna featured_media_id

ETAPA 10 — Pós-limpeza final
  - strip_credits_and_normalize_youtube() — limpa créditos e normaliza embeds YT
  - remove_source_domain_schemas() — remove JSON-LD do domínio fonte
  - Adiciona linha de crédito: <p><strong>Fonte:</strong> <a>...</a></p>

ETAPA 11 — Categorização
  - Começa com categoria padrão: 'Notícias' (ID 20)
  - Adiciona categorias por feed (SOURCE_CATEGORY_MAP): ex. screenrant_movie_news → 'Filmes'
  - Também usa categorias sugeridas pela IA + CATEGORY_ALIASES para normalizar

ETAPA 12 — Links internos
  - add_internal_links() com data/internal_links.json
  - Prioridade: posts-pilar > mesma categoria > outros
  - Máx 6 links internos por artigo

ETAPA 13 — Montagem de metadados SEO
  - yoast_meta com title, metadesc, focuskw, keyphrases
  - Canonical URL = URL original da fonte

ETAPA 14 — Verificação final anti-CTA
  - detect_forbidden_cta() — se detectar CTA, BLOQUEIA publicação

ETAPA 15 — Conversão para Gutenberg
  - html_to_gutenberg_blocks() — converte HTML para formato de blocos do WP

ETAPA 16 — Publicação no WordPress
  - wp_client.create_post(payload) — POST /wp-json/wp/v2/posts
  - Se sucesso (wp_post_id > 0):
    a. update_post_yoast_seo() — atualiza metadados Yoast + OG:Image
    b. add_google_news_meta() — adiciona meta tags Google News
    c. sanitize_published_post() — sanitização final do post publicado
    d. Salva JSON de debug em debug/ai_response_{slug}_{timestamp}.json
    e. Registra tokens no TokenTracker
    f. db.save_processed_post() — marca como PUBLISHED no DB
  - Se falha: status → FAILED

ETAPA 17 — Delay entre publicações
  - time.sleep(30s) entre cada artigo publicado
```

---

## 4. Componentes do Sistema

### 4.1 `app/feeds.py` — FeedReader

**Papel:** Lê e normaliza feeds RSS e Sitemaps XML.

- Usa a biblioteca `feedparser` para RSS e `xml.etree.ElementTree` para Sitemaps
- Função `normalize_item()` padroniza campos: `id`, `title`, `link`, `published`
- Suporta feeds comprimidos com gzip
- Controle de deduplicação por hash SHA-256 da URL
- Ordena itens por data de publicação (mais recentes primeiro)
- Retorna lista de dicionários com campos normalizados

**Interface principal:**
```python
feed_reader = FeedReader(user_agent="MaquinaNerd")
items = feed_reader.read_feeds(feed_config, source_id)
# retorna: List[Dict] com campos: id, title, link, published
```

---

### 4.2 `app/extractor.py` — ContentExtractor

**Papel:** Baixa o HTML de um artigo e extrai o conteúdo editorial limpo.

- `_fetch_html(url)` — GET com User-Agent configurado, timeout 30s
- `extract(html, url)` — combina trafilatura + BeautifulSoup
- Trafilatura remove navegação, ads, sidebars e retorna texto limpo
- BeautifulSoup complementa com extração de imagens, vídeos, schema.org
- Filtragem de imagens com domínios ruins (trackers, avatars, logos)
- Detecção de dimensões de imagens pela URL (sufixos `-1200x630.jpg`)
- Prioridade de imagens por CDN confiável (ex: `static1.srcdn.com` para ScreenRant)
- Extração de vídeos do YouTube por padrão de URL

**Saída:**
```python
{
    "title": str,
    "content": str,          # HTML limpo
    "images": List[str],     # URLs de imagens no corpo
    "videos": List[str],     # IDs de vídeos YouTube
    "featured_image_url": str,
    "schema_original": dict   # JSON-LD original do artigo
}
```

---

### 4.3 `app/ai_processor.py` — AIProcessor

**Papel:** Reescreve o artigo em português jornalístico via Gemini, gerando também todos os metadados SEO.

- Singleton que compartilha o `AIClient` entre instâncias
- Carrega o `universal_prompt.txt` na primeira chamada (cache em memória)
- `rewrite_batch(batch_data)` — processa um artigo por chamada de API
- Monta o prompt completo: `AI_SYSTEM_RULES` + template do `universal_prompt.txt` + conteúdo do artigo
- Faz parse do JSON retornado pela IA
- Trata falhas de parsing (JSON malformado) retornando `(None, reason)`
- Registra tokens consumidos via `TokenTracker`

**Interface principal:**
```python
results = ai_processor.rewrite_batch([{
    "title": "...",
    "content_html": "...",
    "source_url": "...",
    "category": "movies",
    "domain": "maquinanerd.com.br",
    ...
}])
# retorna: List[Tuple[Optional[dict], Optional[str]]]
# Cada tupla: (rewritten_data, failure_reason)
```

---

### 4.4 `app/ai_client_gemini.py` — AIClient

**Papel:** Cliente baixo nível da API Gemini com rotação automática de chaves e retry com backoff exponencial.

- Gerencia pool de múltiplas chaves `GEMINI_*` do `.env`
- `KeyPool` — seleciona a próxima chave disponível por rodízio
- `RateLimiter` — garante intervalo mínimo entre chamadas (padrão: 6s + jitter até 5s)
- Em caso de erro 429 (quota): penaliza a chave por 30s e tenta outra
- Em caso de erro 5xx: penaliza por 10s
- Backoff exponencial: base 20s, máximo 300s
- Captura `usage_metadata` da resposta para contagem de tokens

---

### 4.5 `app/limiter.py` — RateLimiter + KeyPool

**Papel:** Controle de taxa de requisições à API.

- `RateLimiter` usa `monotonic()` para medir intervalo entre chamadas, com jitter aleatório
- `KeyPool` mantém deque de `KeySlot`, cada um com campo `cooldown_until`
- Ao penalizar uma chave, o pool rotaciona a deque para evitar re-uso imediato

---

### 4.6 `app/wordpress.py` — WordPressClient

**Papel:** Publica posts, faz upload de mídia e atualiza metadados no WordPress via REST API.

- Autenticação por Basic Auth (usuário + Application Password)
- `create_post(payload)` — POST `/wp-json/wp/v2/posts`
- `upload_media_from_url(url, title)` — baixa imagem e faz POST `/wp-json/wp/v2/media`
- `update_post_yoast_seo(post_id, media_id, seo_meta)` — atualiza campos `_yoast_wpseo_*`
- `add_google_news_meta(post_id, news_meta)` — adiciona campos de meta do Google News
- `sanitize_published_post(post_id)` — re-salva o post para acionar hooks do WordPress
- Gerenciamento de tags: `_get_existing_tag_id()` + `_create_tag()` com proteção de race condition
- `resolve_category_names_to_ids()` — converte nomes de categorias em IDs

---

### 4.7 `app/seo_title_optimizer.py` — optimize_title

**Papel:** Aplica regras de SEO para Google News ao título gerado pela IA.

- Remove clickbait (`"Você não vai acreditar..."`, `"Prepare-se para..."`)
- Remove entidades HTML (`&#8216;`, `&mdash;`, etc.)
- Verifica se o título contém verbos de ação (`anuncia`, `revela`, `confirma`, etc.)
- Penaliza palavras vagas (`pode`, `talvez`, `aparentemente`)
- Retorna o título otimizado + relatório com pontuação antes/depois

---

### 4.8 `app/title_validator.py` — TitleValidator

**Papel:** Valida regras editoriais do título antes da publicação.

- Valida tamanho: entre 55 e 65 caracteres
- Detecta clickbait e sensacionalismo
- Verifica uso de pontuação excessiva (múltiplos `:`)
- Retorna `{'status': 'OK'|'AVISO'|'ERRO', 'erros': [...], 'avisos': [...]}`
- `suggest_correction(title)` — tenta corrigir automaticamente

---

### 4.9 `app/html_utils.py` — Utilitários de HTML

**Papel:** Conjunto de funções para limpeza e transformação de HTML.

Funções principais:

| Função | O que faz |
|---|---|
| `unescape_html_content()` | Desescapa entidades HTML escapadas pela IA |
| `validate_and_fix_figures()` | Garante que `<figure>` tenha `<figcaption>` |
| `merge_images_into_content()` | Insere imagens extraídas no corpo do HTML |
| `rewrite_img_srcs_with_wp()` | Substitui src de imagens pelas URLs do WP |
| `strip_credits_and_normalize_youtube()` | Remove linhas de crédito e normaliza embeds |
| `remove_broken_image_placeholders()` | Remove placeholders de imagem quebrados |
| `strip_naked_internal_links()` | Remove links soltos sem texto âncora |
| `remove_source_domain_schemas()` | Remove JSON-LD do domínio fonte |
| `detect_forbidden_cta()` | Detecta CTAs proibidos no HTML |
| `strip_forbidden_cta_sentences()` | Remove frases de CTA do HTML |
| `html_to_gutenberg_blocks()` | Converte HTML para blocos Gutenberg do WP |

---

### 4.10 `app/internal_linking.py` — add_internal_links

**Papel:** Injeta links internos no conteúdo baseado em mapa de palavras-chave.

- Lê `data/internal_links.json` com posts existentes e suas keywords
- Estratégia de priorização:
  1. Posts-pilar (definidos em `PILAR_POSTS` no `config.py`) — prioridade máxima
  2. Posts da mesma categoria do artigo atual
  3. Outros posts
- Ordena keywords por comprimento (mais longa primeiro) para evitar substituições parciais
- Máxima 6 links por artigo
- Nunca insere links dentro de `<a>`, `<h1-h6>`, `<blockquote>`, `<code>`, `<figure>`

---

### 4.11 `app/store.py` — Database

**Papel:** Camada de persistência SQLite para rastrear artigos.

- Banco de dados em `data/app.db`
- Tabela principal `seen_articles`: `source_id`, `external_id`, `url`, `status`, `published_at`
- `filter_new_articles()` — filtra apenas artigos não vistos ainda
- `update_article_status()` — atualiza status: `QUEUED` → `PROCESSING` → `PUBLISHED` | `FAILED`
- `save_processed_post()` — salva `wp_post_id` no registro
- Circuit breaker: `get_consecutive_failures()` / `increment_consecutive_failures()` / `reset_consecutive_failures()`

---

### 4.12 `app/task_queue.py` — ArticleQueue

**Papel:** Fila thread-safe entre a ingestão (produtor) e o processamento (consumidor).

- Implementada como fila FIFO com `threading.Lock`
- `push(article)` — adiciona um artigo
- `push_many(articles)` — adiciona múltiplos artigos
- `pop()` — retira um artigo (retorna `None` se vazia)

---

### 4.13 `app/token_tracker.py` — TokenTracker

**Papel:** Rastreia e persiste o consumo de tokens da API Gemini.

- Registra no arquivo `logs/tokens/tokens_YYYY-MM-DD.jsonl` (formato JSONL)
- Mantém estatísticas acumuladas em `logs/tokens/token_stats.json`
- Cada linha registra: timestamp, model, api_key_suffix, prompt_tokens, completion_tokens, success, source_url, wp_post_id, article_title
- Também registra eventos de publicação (api_type="publishing", model="wordpress")

---

## 5. APIs Utilizadas

### 5.1 Google Gemini API

**Biblioteca:** `google-generativeai`  
**Modelo padrão:** `gemini-2.5-flash-lite` (configurável via `AI_MODEL` no `.env`)  
**Autenticação:** Chaves de API carregadas de variáveis de ambiente `GEMINI_*` (prefixo)

**Como é usada:**
- Uma chamada por artigo via `AIClient.generate_text(prompt)`
- O prompt combina regras do sistema + template universal + conteúdo do artigo
- Resposta esperada: JSON válido com campos de conteúdo e SEO
- Gerenciamento de quotas: pool de múltiplas chaves com rotação e cooldown automáticos

**Configuração relevante (`config.py`):**
```python
AI_MODEL = os.getenv('AI_MODEL', 'gemini-2.5-flash-lite')
AI_GENERATION_CONFIG = {
    'temperature': 0.7,
    'top_p': 1.0,
    'max_output_tokens': 4096,
}
```

**Variáveis de ambiente necessárias:**
```
GEMINI_KEY_1=AIza...
GEMINI_KEY_2=AIza...
# ... quantas chaves forem necessárias
```

---

### 5.2 WordPress REST API

**Endpoint base:** `{WORDPRESS_URL}/wp-json/wp/v2/`  
**Autenticação:** HTTP Basic Auth (user + Application Password)

**Endpoints utilizados:**

| Endpoint | Método | Uso |
|---|---|---|
| `/posts` | POST | Criar novo post |
| `/media` | POST | Upload de imagem destacada |
| `/tags` | GET | Buscar tag existente por nome/slug |
| `/tags` | POST | Criar nova tag |
| `/categories` | GET | Buscar categoria por nome |
| `/posts/{id}` | GET | Verificar/sanitizar post |
| `/posts/{id}` | POST | Atualizar metadados (Yoast, Google News) |

**Variáveis de ambiente necessárias:**
```
WORDPRESS_URL=https://www.maquinanerd.com.br/wp-json/wp/v2
WORDPRESS_USER=usuario_wp
WORDPRESS_PASSWORD=senha_de_aplicacao
```

**Categorias configuradas (`config.py`):**
```python
WORDPRESS_CATEGORIES = {
    'Notícias': 20,
    'Filmes': 24,
    'Séries': 21,
    'Games': 73,
}
```

---

### 5.3 Feeds RSS Externos (ScreenRant)

**Protocolo:** RSS 2.0 via HTTP GET  
**Parser:** `feedparser`

**Feeds ativos:**

| source_id | URL do Feed | Categoria |
|---|---|---|
| `screenrant_movie_lists` | `https://screenrant.com/feed/movie-lists/` | Filmes |
| `screenrant_movie_news` | `https://screenrant.com/feed/movie-news/` | Filmes |
| `screenrant_tv` | `https://screenrant.com/feed/tv/` | Séries |

---

### 5.4 TMDb API (opcional)

**Status:** Desativado por padrão (`TMDB_ENABLED=false`)  
**Uso:** Enriquecimento de dados de filmes/séries trendings e upcoming

**Variáveis de ambiente:**
```
TMDB_ENABLED=true
TMDB_API_KEY=...
TMDB_MAX_ENRICHMENTS=3
```

---

## 6. Prompts Utilizados pela IA

O pipeline usa dois conjuntos de instruções para a IA:

---

### 6.1 AI_SYSTEM_RULES (app/ai_processor.py)

**Objetivo:** Regras sistêmicas que são sempre enviadas como parte do prompt para garantir qualidade e formato.

**Conteúdo e responsabilidades:**

#### Regra 1 — Formato de saída obrigatório
A IA deve retornar **exclusivamente** um JSON válido com a estrutura:
```json
{
  "resultados": [
    {
      "titulo_final": "...",
      "conteudo_final": "...",
      "meta_description": "...",
      "focus_keyphrase": "...",
      "related_keyphrases": [...],
      "slug": "...",
      "categorias": [...],
      "tags_sugeridas": [...],
      "yoast_meta": {...}
    }
  ]
}
```

#### Regra 2 — Validação de título
O título deve passar no seguinte checklist:
- Entre 55–65 caracteres
- Começar com entidade (ator, franquia, plataforma)
- Verbo no presente (não infinitivo)
- Afirmação direta, sem pergunta
- Sem sensacionalismo
- Maiúsculas apenas em nomes próprios

#### Regra 3 — Validação de conteúdo
- Sem menção a concorrentes (Omelete, IGN, Jovem Nerd)
- Sem hashtags (`#`)
- Sem frases fracas ou CTAs
- Links internos com syntax `https://{domain}/tag/{tag}`
- Mínimo 3 subtítulos `<h2>`
- Parágrafos com máx 3–4 frases

#### Regra 4 — Meta description
- 140–155 caracteres
- Contém palavra-chave principal
- Sem call-to-action

#### Regra 5 — Remoção de CTAs (crítico)
Proibido no `conteudo_final`:
- "Thank you for reading" (todas variações)
- "Don't forget to subscribe"
- "Click here", "Read more", "Sign up"
- "Stay tuned", "Follow us"
- Caixas de newsletter, author bios

#### Regra 6 — Limpeza obrigatória
Deve remover do conteúdo:
- Texto de interface de comentários
- Fichas técnicas com "Release Date", "Director", "Cast"
- Seções "related", "trending", "read more"

---

### 6.2 universal_prompt.txt (raiz do projeto)

**Objetivo:** Template principal do prompt de usuário enviado ao Gemini junto com o conteúdo do artigo.

**Estrutura:**

1. **Regra da marca** — proibição absoluta de citar portais concorrentes. Se o artigo original diz "segundo a IGN", deve ser reescrito de forma neutra como "segundo informações do estúdio".

2. **Regra crítica anti-CTA** — reiteração das proibições de CTAs em inglês e português.

3. **Papel editorial** — "Você é um jornalista digital sênior, especialista em cultura pop, cinema, TV e games, e em SEO para portais de notícias de entretenimento."

4. **Regras de Português** (obrigatório, zero erros):
   - Verbo no presente para notícias quentes: "chega", "confirma", "revela"
   - Concordância verbal e nominal correta
   - Números por extenso até dez
   - Gírias proibidas: "nerfado" → "ajustado", "morto" → "saiu do elenco"

5. **Regras de SEO**:
   - Tom jornalístico, direto e objetivo
   - Até 3 categorias com `nome`, `grupo`, `evidence`
   - Até 5 tags coerentes com o texto
   - `focus_keyphrase` com máx 60 caracteres
   - `related_keyphrases`: 2–5 variações ou sinônimos

6. **Estrutura JSON esperada** (formato de saída explícito):
```json
{
  "titulo_final": "...",
  "conteudo_final": "<p>...</p><h2>...</h2>",
  "meta_description": "...",
  "focus_keyphrase": "...",
  "related_keyphrases": ["..."],
  "slug": "url-amigavel",
  "categorias": [{"nome": "...", "grupo": "franquias", "evidence": "..."}],
  "tags_sugeridas": ["tag-1", "tag-2"],
  "image_alt_texts": {"imagem.jpg": "Descrição SEO da imagem"},
  "yoast_meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "...",
    "_yoast_news_keywords": "...",
    "_yoast_wpseo_opengraph-title": "...",
    "_yoast_wpseo_opengraph-description": "...",
    "_yoast_wpseo_twitter-title": "...",
    "_yoast_wpseo_twitter-description": "..."
  }
}
```

**Formato de resposta esperado:** JSON puro, sem markdown, sem texto fora do objeto JSON.

---

## 7. Estrutura de Dados

### 7.1 Item RSS (saída de FeedReader)

```python
{
    "id": "https://screenrant.com/artigo-exemplo/",  # URL ou GUID
    "title": "Marvel Announces New Avengers Film",
    "link": "https://screenrant.com/artigo-exemplo/",
    "published": "2026-03-05T10:30:00+00:00",
    "source_id": "screenrant_movie_news"  # adicionado pela pipeline
}
```

### 7.2 Artigo no banco de dados (seen_articles)

```sql
CREATE TABLE seen_articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url         TEXT,
    status      TEXT DEFAULT 'QUEUED',  -- QUEUED|PROCESSING|PUBLISHED|FAILED
    published_at TIMESTAMP,
    wp_post_id  INTEGER,
    reason      TEXT  -- motivo de falha, se aplicável
);
```

**Status possíveis:**
- `QUEUED` — aguardando processamento (inclusive re-tentativas após falha de IA)
- `PROCESSING` — sendo processado atualmente
- `PUBLISHED` — publicado com sucesso no WordPress
- `FAILED` — falha permanente (URL inválida, CTA persistente, etc.)

### 7.3 Artigo enfileirado (ArticleQueue)

```python
{
    "db_id": 42,           # ID no banco SQLite
    "id": "https://...",   # GUID/URL do item RSS
    "title": "...",
    "link": "https://...",
    "published": "2026-03-05T10:30:00+00:00",
    "source_id": "screenrant_movie_news"
}
```

### 7.4 Conteúdo extraído (ContentExtractor.extract)

```python
{
    "title": "Marvel Announces New Avengers Film",
    "content": "<p>texto limpo sem ads...</p>",
    "images": ["https://cdn.srcdn.com/img1.jpg", ...],
    "videos": ["dQw4w9WgXcQ"],           # IDs YouTube
    "featured_image_url": "https://cdn.srcdn.com/featured.jpg",
    "schema_original": {"@type": "NewsArticle", ...}
}
```

### 7.5 Payload enviado à IA (AIProcessor)

```python
{
    "title": "Marvel Announces New Avengers Film",
    "content_html": "<p>texto + imagens concatenadas</p>",
    "source_url": "https://screenrant.com/...",
    "category": "movies",
    "videos": ["dQw4w9WgXcQ"],
    "images": ["https://cdn.srcdn.com/img1.jpg"],
    "source_name": "ScreenRant",
    "domain": "maquinanerd.com.br",
    "schema_original": {...}
}
```

### 7.6 Resposta da IA (rewritten_data)

```python
{
    "titulo_final": "Marvel confirma novo filme dos Vingadores para 2027",
    "conteudo_final": "<p>A Marvel anunciou...</p><h2>Detalhes...</h2>",
    "meta_description": "A Marvel revelou que o novo filme dos Vingadores chega em 2027...",
    "focus_keyphrase": "novo filme dos Vingadores",
    "related_keyphrases": ["Avengers 2027", "Marvel Phase 6", "Vingadores novo filme"],
    "slug": "marvel-confirma-novo-filme-vingadores-2027",
    "categorias": [{"nome": "Marvel", "grupo": "franquias", "evidence": "A Marvel anunciou"}],
    "tags_sugeridas": ["Marvel", "Vingadores", "MCU", "Cinema", "Avengers"],
    "image_alt_texts": {"featured.jpg": "Cartaz do novo filme dos Vingadores"},
    "yoast_meta": {
        "_yoast_wpseo_title": "Marvel confirma novo filme dos Vingadores para 2027",
        "_yoast_wpseo_metadesc": "A Marvel revelou que...",
        "_yoast_wpseo_focuskw": "novo filme dos Vingadores",
        "_yoast_news_keywords": "Marvel, Vingadores, MCU"
    }
}
```

### 7.7 Payload final para o WordPress (WordPressClient.create_post)

```python
{
    "title": "Marvel confirma novo filme dos Vingadores para 2027",
    "slug": "marvel-confirma-novo-filme-vingadores-2027",
    "content": "<!-- wp:paragraph --><p>A Marvel anunciou...</p><!-- /wp:paragraph -->",
    "excerpt": "A Marvel revelou que o novo filme dos Vingadores chega em 2027...",
    "categories": [20, 24],  # Notícias + Filmes
    "tags": ["Marvel", "Vingadores", "MCU", "Cinema", "Avengers"],
    "featured_media": 1234,  # media_id no WP
    "meta": {
        "_yoast_wpseo_title": "...",
        "_yoast_wpseo_metadesc": "...",
        "_yoast_wpseo_focuskw": "...",
        "_yoast_wpseo_canonical": "https://screenrant.com/..."
    },
    "status": "publish"
}
```

---

## 8. Sistema de Agendamento

### Biblioteca

O agendamento é feito com **APScheduler** (Advanced Python Scheduler), usando `BlockingScheduler`.

### Configuração

```python
# app/main.py
scheduler = BlockingScheduler(timezone='America/Sao_Paulo')
scheduler.add_job(
    run_pipeline_cycle,
    'cron',
    minute=f'*/{interval}',  # padrão: */15 (a cada 15 minutos)
    hour='9-18',              # 9h até 18h59 (horário de Brasília)
    timezone='America/Sao_Paulo'
)
```

### Parâmetros configuráveis (variáveis de ambiente)

| Variável | Padrão | Descrição |
|---|---|---|
| `CHECK_INTERVAL_MINUTES` | `15` | Intervalo entre ciclos de ingestão |
| `MAX_ARTICLES_PER_FEED` | `3` | Máx artigos novos por feed por ciclo |
| `MAX_PER_CYCLE` | `10` | Máx total de artigos por ciclo |
| `ARTICLE_SLEEP_S` | `120` | Pausa entre ciclos do worker (2 min) |
| `BETWEEN_BATCH_DELAY_S` | `30` | Pausa entre lotes de artigos |
| `BETWEEN_PUBLISH_DELAY_S` | `30` | Pausa entre publicações individuais |
| `FEED_STAGGER_S` | `45` | Pausa entre leitura de feeds diferentes |

### Modo de execução único (`--once`)

Para executar um único ciclo do pipeline e sair:
```bash
python -m app.main --once
```

Útil para testes e execução via cron externo (Windows Task Scheduler, crontab no Linux).

### Execução ao iniciar

O pipeline executa um ciclo imediatamente ao iniciar, antes de aguardar o schedule, para não deixar artigos parados caso o servidor tenha reiniciado.

### Thread do worker

A função `worker_loop()` roda em uma **thread daemon** inicializada no carregamento do módulo `pipeline.py`:
```python
worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()
```

Isso significa que o worker está processando artigos em background enquanto o scheduler principal dispara novos ciclos de ingestão.

### Proteção de RPM (Requests Per Minute)

O `worker_loop()` mantém um contador de requisições por ciclo:
- Limite: **10 requisições** por ciclo
- Ao atingir o limite: **pausa de 5 minutos** e retorna o artigo para a fila
- Período de inatividade de 2 minutos reseta o contador automaticamente

---

## 9. Tratamento de Erros

### 9.1 Falha no RSS

**Cenário:** Feed inacessível, timeout, XML malformado.

**Tratamento:**
1. Exceção capturada em `run_pipeline_cycle()` com `except Exception as e`
2. `db.increment_consecutive_failures(source_id)` — incrementa contador de falhas do feed
3. **Circuit breaker:** se `consecutive_failures >= 3`, o feed é pulado no próximo ciclo com aviso: `"Circuit open for feed {source_id} ({n} fails) -> skipping"`
4. `db.reset_consecutive_failures(source_id)` — reseta o contador após leitura bem-sucedida

**Impacto:** Os outros feeds continuam sendo processados normalmente.

---

### 9.2 Falha na extração de conteúdo

**Cenário:** URL inválida, site fora do ar, HTML sem conteúdo editorial.

**Tratamento:**
- URL inválida: `status → FAILED`, razão: `"Missing/invalid URL"`
- Falha no GET: `status → FAILED`, razão: `"Failed to fetch HTML"`
- Extração vazia: `status → FAILED`, razão: `"Extraction failed"`

**Status final:** `FAILED` — artigo **não** será retentado automaticamente.

---

### 9.3 Falha na IA

**Cenário:** Quota excedida, JSON malformado, timeout, erro 5xx da Gemini API.

**Tratamento em `ai_client_gemini.py`:**
- Erro 429 (ResourceExhausted): penaliza a chave por 30s, tenta próxima chave do pool
- Erros 5xx: penaliza a chave por 10s, tenta novamente
- Backoff exponencial: começa em 20s, dobra a cada tentativa, máximo de 300s

**Tratamento em `ai_processor.py`:**
- JSON malformado: retorna `(None, "JSON parse error: ...")`
- Campos obrigatórios ausentes: retorna `(None, "Missing required fields")`

**Tratamento em `process_batch()`:**
- `(None, reason)` → `status → QUEUED`, razão registrada no DB
- **Artigos `QUEUED` são retentados automaticamente** no próximo ciclo de ingestão (diferente de `FAILED`)

---

### 9.4 CTA detectado após limpeza

**Cenário:** A IA incluiu frases como "Thank you for reading" apesar das instruções.

**Tratamento (4 camadas):**
1. Remoção literal de frases exatas
2. Remoção por regex flexível (variações com HTML inline)
3. Remoção de parágrafos `<p>` inteiros com CTAs
4. Verificação final — se ainda presente: `status → FAILED`, razão: `"CTA persisted after cleaning - CRITICAL FAILURE"`

**Gate final:** Mesmo após as limpezas, há uma verificação extra (`detect_forbidden_cta()`) imediatamente antes da publicação. Se detectar CTA: `status → FAILED`, razão: `"FINAL CHECK: CTA detected before WordPress publishing - Article blocked"`.

---

### 9.5 Falha na publicação no WordPress

**Cenário:** Autenticação inválida, API do WP fora do ar, payload inválido.

**Tratamento:**
- `wp_client.create_post()` retorna `None` ou `0` → `status → FAILED`
- Erros de upload de mídia: ignorados (artigo publicado sem imagem destacada)
- Falha no Yoast SEO update: aviso no log, publicação **não** é bloqueada
- Falha no Google News meta: aviso no log de debug, publicação **não** é bloqueada
- Falha na sanitização: aviso no log, publicação **não** é bloqueada

---

### 9.6 Falha em lote (batch completo)

**Cenário:** A chamada `ai_processor.rewrite_batch()` lança uma exceção (ex: timeout, erro de rede).

**Tratamento:**
1. O batch inteiro é tratado na exceção `except Exception as e`
2. O pipeline tenta reprocessar cada artigo do lote **individualmente**
3. Cada artigo individual tem seu próprio tratamento de erro isolado

---

## 10. Logs e Monitoramento

### Arquivos de log

| Arquivo | Conteúdo |
|---|---|
| `logs/app.log` | Log principal da aplicação (INFO e acima) |
| `logs/tokens/tokens_YYYY-MM-DD.jsonl` | Consumo de tokens por chamada de API |
| `logs/tokens/token_stats.json` | Estatísticas acumuladas de tokens |
| `logs/tokens/token_debug.log` | Debug do TokenTracker |
| `debug/ai_response_{slug}_{timestamp}.json` | JSON completo retornado pela IA por artigo |

### Formato do log principal

```
2026-03-05 10:30:00 - INFO - pipeline - Starting new pipeline ingestion cycle.
2026-03-05 10:30:01 - INFO - pipeline - Ingesting feed: screenrant_movie_news
2026-03-05 10:30:02 - INFO - pipeline - Enqueued 3 articles from screenrant_movie_news. Total in cycle: 3.
2026-03-05 10:30:48 - INFO - pipeline - Processing article: Marvel Confirms... (DB ID: 42) from screenrant_movie_news
2026-03-05 10:31:05 - INFO - pipeline - FEATURED OK: ID 567
2026-03-05 10:31:30 - INFO - pipeline - PUBLICADO: Post 8901 | Marvel confirma novo filme dos Vingadores para 2027
2026-03-05 10:31:30 - INFO - pipeline -   URL no WordPress: https://www.maquinanerd.com.br/?p=8901
2026-03-05 10:31:30 - INFO - pipeline -   Categorias: {20, 24}
2026-03-05 10:31:30 - INFO - pipeline -   Tags: ['Marvel', 'Vingadores', 'MCU', 'Cinema', 'Avengers']
```

### Verificações de saúde recomendadas

**1. Verificar publicações recentes:**
```bash
tail -100 logs/app.log | grep "PUBLICADO:"
```

**2. Verificar falhas recentes:**
```bash
tail -200 logs/app.log | grep -E "FAILED|ERRO|ERROR"
```

**3. Verificar status do circuit breaker (feed com falhas):**
```bash
grep "Circuit open" logs/app.log
```

**4. Verificar consumo de tokens:**
```bash
cat logs/tokens/token_stats.json
```

**5. Verificar CTAs detectados:**
```bash
grep "CTA detectado\|CTA CRITICO\|LAYER 1" logs/app.log
```

**6. Inspecionar resposta da IA de um artigo específico:**
```bash
# Substituir pelo slug do artigo
cat debug/ai_response_batch_marvel-confirma-novo-filme-vingadores_*.json | python -m json.tool
```

### Variáveis de ambiente para debugging

Para aumentar o nível de detalhe dos logs:
```bash
# No .env ou no ambiente do sistema
LOG_LEVEL=DEBUG
```

---

## 11. Melhorias Futuras

### Alta prioridade

**1. Deduplicação por similaridade de conteúdo**  
Atualmente a deduplicação é feita apenas por URL/GUID. Artigos com o mesmo conteúdo mas URLs diferentes (syndication) podem ser processados múltiplas vezes. Implementar hashing do título ou embedding semântico para deduplicação por conteúdo.

**2. Filas persistentes com Redis ou RabbitMQ**  
A `ArticleQueue` atual é in-memory e perde o estado em caso de restart. Migrar para uma fila persistente (Redis, RabbitMQ, ou até uma tabela SQLite dedicada) garantiria que nenhum artigo seja perdido.

**3. Dashboard de monitoramento em tempo real**  
O arquivo `dashboard.py` já existe mas precisa ser integrado. Construir um painel web com status dos feeds, taxa de publicação, consumo de tokens e artigos com falha.

**4. Retry automático com backoff para artigos FAILED**  
Artigos com status `FAILED` nunca são retentados automaticamente. Implementar uma política de retry com número máximo de tentativas e backoff exponencial.

**5. Suporte a múltiplas fontes RSS além de ScreenRant**  
Adicionar feeds de outras fontes como Collider, CBR, GameRant, etc. A arquitetura já suporta via `RSS_FEEDS` no `config.py`.

---

### Média prioridade

**6. Validação diferenciada por tipo de erro da IA**  
Atualmente todos os erros de IA resultam em `QUEUED` genérico. Diferenciar: erro de quota (retry rápido) vs. erro estrutural no output (pode precisar de ajuste no prompt).

**7. Geração automática do `data/internal_links.json`**  
Hoje o arquivo de links internos precisa ser gerado/atualizado manualmente. Criar um script periódico que consulta o WordPress e regenera o mapa de keywords automaticamente.

**8. Suporte a vídeos do YouTube como mídia incorporada**  
O extrator já identifica IDs de YouTube, mas o pipeline ainda não converte automaticamente em blocos `<!-- wp:embed -->` do Gutenberg com URL completa.

**9. Testes automatizados do pipeline end-to-end**  
A pasta `tests/` existe mas está vazia. Implementar testes de integração com fixtures de RSS e mocks da API Gemini para garantir que mudanças no pipeline não quebrem o fluxo principal.

**10. Rate limiting adaptativo por modelo Gemini**  
Diferentes modelos Gemini têm limites diferentes de RPM/RPD. Implementar configuração de rate limit por modelo em vez de um valor fixo global.

---

### Baixa prioridade / Futuros

**11. Suporte a múltiplos idiomas de origem**  
Hoje o pipeline processa apenas artigos em inglês. Adicionar detecção de idioma e instruções de tradução condicionais no prompt.

**12. SEO A/B testing de títulos**  
Implementar geração de 2–3 variações de título pela IA e posterior análise de CTR via Google Search Console API para aprendizado contínuo.

**13. Enriquecimento com TMDb**  
O módulo `tmdb_client.py` existe mas está desabilitado. Ativar para enriquecer artigos de filmes/séries com dados estruturados (elenco, data de lançamento, trailer) diretamente do TMDb.

**14. Publicação em múltiplos sites WordPress**  
A arquitetura de `WordPressClient` é stateless por instância. Seria possível estender o `config.py` para suportar múltiplos destinos de publicação com um único pipeline.

---

*Documentação gerada com base no código-fonte do projeto em Março de 2026.*
