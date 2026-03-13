# TheNerd-MN26 — Guia Completo de Replicação

> Pipeline de autopublicação de conteúdo: RSS → Extração → IA (Gemini) → WordPress  
> Versão documentada: `main` | Gerado automaticamente com base no código-fonte.

---

## Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Estrutura de Arquivos](#3-estrutura-de-arquivos)
4. [Instalação](#4-instalação)
5. [Configuração do `.env`](#5-configuração-do-env)
6. [O Que Mudar para Outro Site](#6-o-que-mudar-para-outro-site) ⭐ _seção crítica_
7. [Fluxo Completo do Pipeline](#7-fluxo-completo-do-pipeline)
8. [Sistema Evergreen](#8-sistema-evergreen)
9. [Sistema de Qualidade (QA)](#9-sistema-de-qualidade-qa)
10. [Linkagem Interna Automática](#10-linkagem-interna-automática)
11. [Extratores por Site de Origem](#11-extratores-por-site-de-origem)
12. [Token Tracking e Controle de Custos](#12-token-tracking-e-controle-de-custos)
13. [Manutenção e Monitoramento](#13-manutenção-e-monitoramento)
14. [Histórico de Commits Importantes](#14-histórico-de-commits-importantes)
15. [Problemas Conhecidos e Soluções](#15-problemas-conhecidos-e-soluções)

---

## 1. Visão Geral do Sistema

O pipeline funciona em **quatro etapas principais** que rodam automaticamente a cada 15 minutos:

```
RSS/Sitemap  →  Extração Web  →  Reescrita por IA  →  Publicação WordPress
```

**O que o sistema faz:**

1. **Ingesta** feeds RSS de sites parceiros (ScreenRant por padrão)
2. **Extrai** o conteúdo HTML bruto da página de origem
3. **Reescreve** o conteúdo com Gemini AI: título SEO, corpo em PT-BR, tags, slug, metadados
4. **Publica** no WordPress via API REST com Yoast SEO, categorias, tags e imagem destacada
5. **Gera** artigos "evergreen" auxiliares com base em entidades de alto valor (Marvel, Star Wars, etc.)
6. **Atualiza** o link store para inserir links internos automáticos em artigos futuros

**Tecnologias utilizadas:**

| Componente | Tecnologia |
|---|---|
| Runtime | Python 3.10+ |
| Scheduler | APScheduler (cron) |
| IA | Google Gemini 2.5 Flash Lite |
| Banco de dados | SQLite (`data/app.db`) |
| CMS | WordPress REST API |
| Web scraping | Trafilatura + BeautifulSoup4 |
| Imagens | Hotlink (sem re-upload por padrão) |

---

## 2. Pré-requisitos

### Software
- Python **3.10+** (testado com 3.11)
- pip / venv
- Git
- Acesso SSH ou RDP ao servidor (Windows ou Linux)

### Contas e credenciais
- **Google AI Studio**: conta com acesso ao Gemini API (https://aistudio.google.com) — plano gratuito suporta ~60 req/min
- **WordPress**: site com API REST habilitada + Application Password configurado
  - Ativar em: **WordPress Admin → Usuários → Seu Perfil → Senhas de aplicativo**
  - O usuário precisa ter função **Editor** ou **Administrador**
- **TMDb** (opcional): chave de API se quiser enriquecimento de dados de filmes (https://www.themoviedb.org/settings/api)

### WordPress: plugins necessários
- **Yoast SEO** (obrigatório — o pipeline grava `_yoast_wpseo_*` direto no banco via REST)
- **JWT Authentication for WP-API** ou **Application Passwords** (nativo desde WP 5.6)
- **WPCode** (opcional, para snippets como o validador de sitemap)

---

## 3. Estrutura de Arquivos

```
TheNerd-MN26/
│
├── main.py                      # Ponto de entrada: inicia o APScheduler
├── pyproject.toml               # Metadados do projeto Python
├── requirements.txt             # Dependências pip
├── universal_prompt.txt         # ⭐ Prompt mestre do Gemini (português, editável)
├── .env                         # Credenciais e variáveis de ambiente (NÃO commitar)
├── .env.example                 # Template do .env
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # Inicializa DB, configura logs, agenda ciclos
│   ├── config.py                # ⭐ CONFIGURAÇÃO CENTRAL (feeds, categorias, horários)
│   ├── pipeline.py              # ⭐ ORQUESTRADOR PRINCIPAL do pipeline
│   │
│   ├── ai_client_gemini.py      # Wrapper da API Gemini com retry e rotação de chaves
│   ├── ai_processor.py          # Monta prompts e faz dispatch ao Gemini
│   ├── batch_processor.py       # Processamento em lote (utilitário)
│   │
│   ├── feeds.py                 # Leitura de feeds RSS/Atom/Sitemap
│   ├── extractor.py             # Web scraping (Trafilatura + cleaners por site)
│   ├── scraper.py               # Scraper HTTP de baixo nível
│   │
│   ├── wordpress.py             # Cliente WordPress REST API
│   ├── store.py                 # Banco SQLite: artigos, status, deduplicação
│   ├── link_store.py            # Banco SQLite: últimos 200 artigos para links internos
│   │
│   ├── html_utils.py            # ⭐ Transformações HTML (CTA removal, H1→H2, etc.)
│   ├── cleaners.py              # Cleaners por domínio (ScreenRant, Globo, etc.)
│   ├── cleanup.py               # Limpeza periódica de registros antigos
│   │
│   ├── cluster_engine.py        # ⭐ Pontuação de evento + decisão de evergreen
│   ├── evergreen_publisher.py   # ⭐ Geração de artigos evergreen (5 templates)
│   │
│   ├── internal_linking.py      # Insere links internos automáticos no conteúdo
│   ├── seo_title_optimizer.py   # Pontuação e otimização automática de títulos
│   ├── title_validator.py       # Validação editorial de títulos
│   │
│   ├── models.py                # Modelos de dados (dataclasses)
│   ├── categorizer.py           # Classificação automática de categorias
│   ├── content_enricher.py      # Enriquecimento de conteúdo
│   ├── media.py                 # Gerenciamento de mídia WP
│   ├── page_generator.py        # Gerador de páginas estáticas
│   ├── rss_builder.py           # Construção de feeds RSS customizados
│   ├── synthetic_rss.py         # RSS sintético gerado internamente
│   ├── tags.py                  # Gerenciamento de tags WP
│   │
│   ├── limiter.py               # RateLimiter + KeyPool (rotação de chaves API)
│   ├── task_queue.py            # Fila in-memory de artigos para processar
│   ├── token_bucket.py          # Algoritmo token bucket para rate limiting
│   ├── token_tracker.py         # Registro de tokens consumidos por chamada
│   ├── token_guarantee.py       # Garantia de tokens mínimos
│   │
│   ├── tmdb_client.py           # Cliente TMDb (dados de filmes)
│   ├── tmdb_extended.py         # Funções estendidas TMDb
│   ├── movie_hub_manager.py     # Gerenciador de hub de filmes
│   ├── movie_repository.py      # Repositório de dados de filmes
│   │
│   ├── logging_conf.py          # Configuração de logging
│   ├── logging_config.py        # Alternativa de configuração de logging
│   ├── exceptions.py            # Exceções customizadas
│   │
│   ├── keys.py                  # Carregamento de chaves de API
│   └── keys.example.py          # Template de chaves
│
├── data/
│   ├── app.db                   # Banco SQLite principal (criado automaticamente)
│   └── internal_links.json      # Mapa de links internos (gerado/atualizado)
│
├── logs/
│   ├── pipeline.log             # Log principal do pipeline
│   └── tokens/                  # Logs de consumo de tokens por dia
│       └── tokens_YYYY-MM-DD.jsonl
│
├── debug/
│   └── ai_response_*.json       # Respostas brutas da IA por artigo publicado
│
├── templates/                   # Templates HTML (se houver)
├── tests/                       # Testes unitários
├── scripts/                     # Scripts auxiliares
└── docs/                        # Documentação adicional
```

---

## 4. Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/maquinanerd/TheNerd-MN26.git
cd TheNerd-MN26

# 2. Criar ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar o arquivo .env (NUNCA commitar o .env real)
cp .env.example .env
# Editar .env com suas credenciais

# 5. Inicializar banco de dados e testar
python main.py --once

# 6. Rodar em modo contínuo
python main.py
```

### Iniciar automaticamente no Windows (como serviço)

Use o arquivo `CONFIGURAR_AUTO_INICIAR.bat` incluído no projeto, ou crie uma tarefa agendada:

```
Tarefa: TheNerd Pipeline
Programa: C:\caminho\.venv\Scripts\python.exe
Argumentos: C:\caminho\main.py
Inicializar em: Início de sessão / Sempre
```

---

## 5. Configuração do `.env`

Copie `.env.example` e preencha todos os campos:

```env
# ── GEMINI API ──────────────────────────────────────────────────────────────
# Obtenha em: https://aistudio.google.com/app/apikey
GEMINI_KEY_1=AIzaSy...           # Primeira chave (obrigatória)
GEMINI_KEY_2=AIzaSy...           # Segunda chave (rotação automática — opcional mas recomendado)
GEMINI_KEY_3=AIzaSy...           # Terceira chave (opcional)
GEMINI_MODEL_ID=gemini-2.5-flash-lite   # Modelo a usar
AI_MODEL=gemini-2.5-flash-lite         # Alias (usado em alguns módulos)

# ── WORDPRESS ────────────────────────────────────────────────────────────────
# URL do site SEM barra no final
WORDPRESS_URL=https://www.seusite.com.br
# Usuário administrador ou editor
WORDPRESS_USER=seu_usuario
# Application Password (WP Admin → Usuários → Senhas de Aplicativo)
WORDPRESS_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

# ── PIPELINE ─────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
CHECK_INTERVAL_MINUTES=15         # Intervalo do scheduler (minutos)
MAX_ARTICLES_PER_FEED=3          # Máx. artigos por feed por ciclo
MAX_PER_FEED_CYCLE=3             # Alias (usado no pipeline)
MAX_PER_CYCLE=10                 # Máx. artigos por ciclo total
ARTICLE_SLEEP_S=120              # Pausa entre artigos processados (segundos)
PER_ARTICLE_DELAY_SECONDS=8      # Delay extra entre artigos (segundos)
PER_FEED_DELAY_SECONDS=15        # Delay entre feeds (segundos)
FEED_STAGGER_S=45                # Escalonamento entre feeds no ciclo

# ── IMAGENS ──────────────────────────────────────────────────────────────────
IMAGES_MODE=hotlink              # "hotlink" = usa URL original | "upload" = re-faz upload
PUBLISHER_LOGO_URL=https://www.seusite.com.br/wp-content/logo.png

# ── SEGURANÇA ────────────────────────────────────────────────────────────────
SECRET_KEY=chave-secreta-aleatoria   # Para assinar tokens internos (se usar dashboard)

# ── MANUTENÇÃO ───────────────────────────────────────────────────────────────
CLEANUP_AFTER_HOURS=72           # Limpar registros processados após N horas
```

---

## 6. O Que Mudar para Outro Site

> ⭐ **Esta é a seção mais importante para replicação.** Cada ponto abaixo descreve exatamente o que alterar.

---

### 6.1 `app/config.py` — Configuração Central

Este é o arquivo mais importante. Todas as configurações do site ficam aqui.

#### 6.1.1 — Feeds RSS de origem

```python
# app/config.py
RSS_FEEDS = {
    'screenrant_movie_lists': {
        'url': 'https://screenrant.com/feed/category/movies/',
        'category': 'Filmes',
        'source_name': 'Screen Rant',
        'type': 'rss',
    },
    # ↓ SUBSTITUA pelos feeds do novo site
    'meusite_tecnologia': {
        'url': 'https://techcrunch.com/feed/',
        'category': 'Tecnologia',
        'source_name': 'TechCrunch',
        'type': 'rss',
    },
}
```

**Regras ao adicionar feeds:**
- A chave (ex: `'meusite_tecnologia'`) é o `source_id` — use apenas letras minúsculas, underscores, sem espaços
- `category` deve corresponder a uma chave em `WORDPRESS_CATEGORIES`
- `source_name` aparece na linha de crédito publicada no artigo

#### 6.1.2 — Ordem de processamento dos feeds

```python
# Define qual feed é processado primeiro a cada ciclo
PIPELINE_ORDER = ['screenrant_movie_lists', 'screenrant_movie_news', 'screenrant_tv']

# ALTERE para os IDs dos seus novos feeds:
PIPELINE_ORDER = ['meusite_tecnologia', 'meusite_ciencia']
```

#### 6.1.3 — Categorias do WordPress

```python
# Os IDs numéricos devem corresponder às categorias REAIS do seu WordPress
# Verifique em: WP Admin → Posts → Categorias (ID aparece na URL ao editar)
WORDPRESS_CATEGORIES = {
    'Notícias': 20,   # ← substitua pelo ID real no novo WP
    'Filmes':   24,   # ← substitua
    'Séries':   21,   # ← substitua
    'Games':    73,   # ← substitua
}

# EXEMPLO para um site de tecnologia:
WORDPRESS_CATEGORIES = {
    'Notícias':    5,
    'Tecnologia': 12,
    'IA':         18,
    'Gadgets':    22,
}
```

#### 6.1.4 — Mapeamento feed → categoria

```python
# Define qual(is) categoria(s) recebe cada feed
SOURCE_CATEGORY_MAP = {
    'screenrant_movie_lists': ['Filmes'],
    'screenrant_movie_news':  ['Notícias', 'Filmes'],
    'screenrant_tv':          ['Séries'],
}

# EXEMPLO para tecnologia:
SOURCE_CATEGORY_MAP = {
    'meusite_tecnologia': ['Tecnologia', 'Notícias'],
    'meusite_ia':         ['IA', 'Tecnologia'],
}
```

#### 6.1.5 — PILAR_POSTS (links para artigos prioritários)

```python
# URLs dos seus artigos mais importantes — recebem prioridade no link store
# Insira os artigos âncora/hub do novo site aqui
PILAR_POSTS = [
    'https://www.seusite.com.br/guia-completo-de-ia/',
    'https://www.seusite.com.br/melhores-gadgets-2025/',
]
```

#### 6.1.6 — Aliases de categorias (normalização)

```python
# Se a IA sugerir nomes alternativos de categoria, eles são mapeados aqui
CATEGORY_ALIASES = {
    'movies': 'Filmes',
    'series': 'Séries',
    'tv':     'Séries',
    # ADICIONE aliases para o novo nicho:
    'tech':         'Tecnologia',
    'artificial intelligence': 'IA',
}
```

---

### 6.2 `app/cluster_engine.py` — Entidades de Alto Valor

Este arquivo define quais entidades (franquias, marcas, personagens) disparam a geração de artigos evergreen.

```python
HIGH_VALUE_ENTITIES = {
    # Universos cinematográficos
    "Marvel", "MCU", "Avengers", "Spider-Man", "X-Men",
    "DC", "Batman", "Superman",
    # Séries
    "The Boys", "Stranger Things", "Game of Thrones",
    # Franquias
    "Star Wars", "Harry Potter", "Lord of the Rings",
    # ... ~60 entidades no total
}
```

**Para um site de tecnologia**, substitua por:

```python
HIGH_VALUE_ENTITIES = {
    "Apple", "iPhone", "MacBook",
    "Google", "Android", "Pixel",
    "Microsoft", "Windows", "Copilot",
    "OpenAI", "ChatGPT", "GPT-4",
    "Tesla", "SpaceX",
    "Samsung", "Galaxy",
    "NVIDIA", "AMD", "Intel",
    "Meta", "Instagram", "WhatsApp",
}
```

**Threshold de score**: entidades com score ≥ 50 disparam cluster; ajuste em:

```python
CLUSTER_THRESHOLD = 50  # linha no cluster_engine.py
```

---

### 6.3 `app/evergreen_publisher.py` — Templates Evergreen

Os prompts de geração evergreen contêm menções diretas ao site atual. **Substitua todos os valores hardcodados:**

| O que alterar | Valor atual | Substitua por |
|---|---|---|
| Nome do site | `Máquina Nerd` | Nome do novo site |
| Domínio | `maquinanerd.com.br` | Domínio do novo site |
| Persona do redator | `redator especialista em cultura pop e entretenimento` | Persona adequada ao nicho |
| Tom editorial | referências a filmes/séries | Referências ao nicho do novo site |

**Busque por:**
```bash
grep -r "maquinanerd\|Máquina Nerd" app/evergreen_publisher.py
```

Os 5 templates disponíveis são:
1. `timeline` — Linha do tempo de eventos
2. `cast_guide` — Guia de elenco/personagens
3. `villains` — Análise de vilões/antagonistas
4. `ending_explained` — Explicação de final
5. `easter_eggs` — Easter eggs e referências

Para outros nichos, renomeie os templates e ajuste as instruções dentro de cada prompt string.

---

### 6.4 `universal_prompt.txt` — Prompt Mestre do Gemini

Este arquivo é o cérebro editorial do sistema. Contém:

- Detecção de tipo (Tipo A = notícia, Tipo B = listicle)
- Regras de fidelidade ao conteúdo original
- Estrutura esperada dos artigos
- Instruções de SEO (títulos, headings, meta)
- Regras de formatação HTML
- Checklist de validação pré-publicação

**O que substituir para outro site:**

1. **Menções ao domínio**: busque `maquinanerd.com.br` e substitua pelo novo domínio
2. **Persona editorial**: altere a descrição do redator para o nicho do novo site
3. **Estrutura "Nossa Análise"**: se o novo site não usar este bloco, remova ou renomeie
4. **Checklist final**: adapte as regras ao novo contexto editorial
5. **Exemplos de H2/H3**: substitua pelos exemplos do nicho do novo site

---

### 6.5 `app/html_utils.py` — URLs hardcodadas

A função `strip_ai_tag_links()` filtra links para o domínio atual:

```python
def strip_ai_tag_links(html: str, domain: str = "maquinanerd.com.br") -> str:
```

Ela já aceita o `domain` como parâmetro, mas o default é hardcodado. Na pipeline, ela é chamada assim:

```python
# em pipeline.py — já passa o domínio dinamicamente via wp_client
content_html = strip_ai_tag_links(content_html)
```

Altere o default para o novo domínio (ou deixe o wp_client passar corretamente).

---

### 6.6 `app/pipeline.py` — URLs hardcodadas

Busque por `maquinanerd.com.br` no arquivo:

```bash
grep -n "maquinanerd" app/pipeline.py
```

Você encontrará:
1. `int_links = [a for a in ... if "maquinanerd.com.br" in a["href"]]` — no `assess_content_quality()`, linha ~97
2. `url=f"https://www.maquinanerd.com.br/{slug}/"` — no link_store save, linha ~700

**Substitua pelo domínio do novo site** em ambas as ocorrências, ou refatore para ler o domínio do `WORDPRESS_CONFIG`.

---

### 6.7 Checklist completo para novo site

- [ ] Criar novo repositório no GitHub
- [ ] Copiar todos os arquivos do projeto
- [ ] Editar `.env` com credenciais do novo WP e novas chaves Gemini
- [ ] Editar `app/config.py`: feeds, categorias, source_map, pilar_posts
- [ ] Editar `app/cluster_engine.py`: HIGH_VALUE_ENTITIES para o novo nicho
- [ ] Editar `app/evergreen_publisher.py`: nome do site, domínio, persona, templates
- [ ] Editar `universal_prompt.txt`: domínio, persona editorial, exemplos de H2/H3
- [ ] Substituir `maquinanerd.com.br` em `html_utils.py` e `pipeline.py`
- [ ] Adicionar cleaners em `app/cleaners.py` para os novos sites de origem
- [ ] Inicializar DB limpo: deletar `data/app.db` e rodar `python main.py --once`
- [ ] Verificar primeiro artigo publicado manualmente no WP

---

## 7. Fluxo Completo do Pipeline

```
main.py
└── APScheduler (cron: a cada 15min, horário 9h–18h BRT)
    └── run_pipeline_cycle()          [pipeline.py]
        │
        ├── process_evergreen_queue() [evergreen_publisher.py]
        │   └── Publica até 2 artigos evergreen pendentes da fila
        │
        └── Para cada feed em PIPELINE_ORDER:
            ├── FeedReader.read_feeds()    [feeds.py]    → RSS/Atom/Sitemap parse
            ├── Database.filter_new_articles()           → Deduplicação (SQLite)
            └── article_queue.push_many()                → Enfileira novos artigos
                                                           (máx. MAX_PER_FEED_CYCLE)

worker_loop()  [pipeline.py — thread paralela em background]
└── Para cada artigo na fila:
    │
    ├── ContentExtractor._fetch_html()  [extractor.py]  → HTTP GET da URL de origem
    ├── Cleaner por domínio             [cleaners.py]   → Remove widgets/ads/captions
    ├── ContentExtractor.extract()                      → Trafilatura → texto + imagens
    │
    ├── cluster_engine.score_event()    [cluster_engine.py]
    │   └── Pré-detecta entidade para sugestão de links internos
    │
    ├── link_store.get_related()        [link_store.py]
    │   └── Busca 3 artigos relacionados para bloco de links no prompt
    │
    ├── AIProcessor.rewrite_batch()     [ai_processor.py]
    │   ├── Monta prompt com universal_prompt.txt + conteúdo + link_block
    │   └── AIClient.generate_text()   [ai_client_gemini.py]
    │       ├── KeyPool: rotação de chaves GEMINI_KEY_*
    │       ├── Retry com backoff exponencial
    │       └── Retorna (text_json, tokens_info)
    │
    └── [processamento pós-IA]
        │
        ├── LIMPEZA CTA (4 camadas):
        │   ├── strip_forbidden_cta_sentences()
        │   ├── Literal string removal
        │   ├── Sentence regex patterns
        │   └── Paragraph regex + tags vazias
        │
        ├── VALIDAÇÃO DE TÍTULO:
        │   ├── TitleValidator.validate()   → tamanho, caracteres especiais
        │   └── optimize_title()            → score SEO (verbos de ação, comprimento)
        │
        ├── LIMPEZA HTML (em ordem):
        │   ├── unescape_html_content()
        │   ├── validate_and_fix_figures()
        │   ├── remove_broken_image_placeholders()
        │   ├── downgrade_h1_to_h2()        ← evita H1 duplicado (WP injeta H1)
        │   ├── strip_ai_tag_links()         ← remove links /tag/ inventados pela IA
        │   ├── strip_naked_internal_links() ← remove URLs nuas em parágrafos
        │   └── merge_images_into_content()  ← distribui imagens no corpo
        │
        ├── UPLOAD DE IMAGEM:
        │   └── wp_client.upload_media_from_url() → apenas se is_valid_upload_candidate()
        │
        ├── strip_credits_and_normalize_youtube()
        ├── remove_source_domain_schemas()   ← evita JSON-LD do domínio de origem
        ├── Linha de crédito: "Fonte: [ScreenRant](url)"
        │
        ├── CATEGORIAS:
        │   ├── SOURCE_CATEGORY_MAP → categorias fixas por feed
        │   └── IA sugere → resolve_category_names_to_ids() (cria se não existir)
        │
        ├── add_internal_links()    [internal_linking.py]
        │   └── Insere até 6 links internos do link_store
        │
        ├── QA CAMADA 1 — assess_content_quality():
        │   ├── Pontuação multicritério (palavras, H2/H3, links int., "Nossa Análise")
        │   └── Score ≥ 45 → INDEX | Score < 45 → NOINDEX
        │
        ├── QA CAMADA 2 — semantic_qa_flash() [apenas score 35–49]:
        │   ├── Gemini avalia: CTA residual, valor original, tipo de conteúdo
        │   └── Pode forçar INDEX (evergreen com valor) ou confirmar NOINDEX
        │
        ├── VERIFICAÇÃO FINAL CTA → bloqueia publicação se detectar
        │
        ├── html_to_gutenberg_blocks()  → converte para formato WordPress
        │
        ├── WordPressClient.create_post()  [wordpress.py]
        │   ├── POST /wp/v2/posts
        │   └── Retorna wp_post_id
        │
        ├── wp_client.update_post_yoast_seo() → title, description, focuskw, noindex
        ├── wp_client.add_google_news_meta()  → keywords, genres
        ├── wp_client.sanitize_published_post()
        │
        ├── token_tracker.log_tokens()   → registra uso de tokens
        │
        ├── cluster_engine.score_event() → score final pós-publicação
        │   └── Se score ≥ 50: schedule_cluster_pages() → fila evergreen
        │
        ├── link_store.save_article()    → registra para uso em links futuros
        │
        └── Database.save_processed_post()  → marca PUBLISHED no SQLite
```

---

## 8. Sistema Evergreen

O sistema evergreen gera artigos complementares automaticamente quando um evento de alto valor é detectado.

### Como funciona

1. Após publicar um artigo normal, `score_event()` avalia se é sobre uma entidade de alto valor
2. Se score ≥ 50, `schedule_cluster_pages()` enfileira 3 artigos na tabela `evergreen_queue`
3. A cada ciclo do pipeline, `process_evergreen_queue()` publica até 2 artigos da fila

### Timing de publicação

| Artigo | Delay após artigo original |
|---|---|
| Evergreen #1 | +1 hora |
| Evergreen #2 | +6 horas |
| Evergreen #3 | +24 horas |

### Templates disponíveis

| Template | Tipo de artigo gerado |
|---|---|
| `timeline` | Linha do tempo da franquia/entidade |
| `cast_guide` | Guia completo do elenco/personagens |
| `villains` | Análise dos vilões/antagonistas |
| `ending_explained` | Explicação do final/último episódio |
| `easter_eggs` | Easter eggs e referências escondidas |
| `powers` | Poderes e habilidades dos personagens |

### Imagem destacada

O sistema usa `wp_client.find_media_by_search(entity)` para reutilizar imagens já existentes na biblioteca de mídia do WordPress, evitando uploads desnecessários.

### Ajustando para outro nicho

Em `evergreen_publisher.py`, modifique:
- Os prompts de cada template para o novo contexto
- O `EVERGREEN_TEMPLATES` dict em `cluster_engine.py` para incluir novos tipos
- O número de artigos por cluster (atualmente 3) editando `schedule_cluster_pages()`

---

## 9. Sistema de Qualidade (QA)

### QA Camada 1 — Estrutural (sempre executado)

Função: `assess_content_quality()` em `pipeline.py`

| Critério | Pontos | Condição |
|---|---|---|
| Volume de palavras ≥ 600 | 30 | Artigo completo |
| Volume de palavras ≥ 400 | 15 | Artigo mínimo |
| Presença de `<h3>` | 20 | Profundidade hierárquica |
| Presença de `<h2>` | 10 | Estrutura básica |
| Links internos ≥ 2 | 20 | Boa linkagem |
| Links internos ≥ 1 | 10 | Linkagem mínima |
| Bloco "Nossa Análise" | 15 | Editorial próprio |

**Score ≥ 45 → INDEX** | **Score < 45 → NOINDEX**

> ⚠️ Se seu site não usa "Nossa Análise", ajuste o critério 7 para outro elemento editorial que você use.

### QA Camada 2 — Semântica (score borderline 35–49)

Função: `semantic_qa_flash()` em `pipeline.py`

Faz uma chamada extra ao Gemini para avaliar:
- `has_original_value`: o conteúdo tem valor informacional real?
- `has_cta_residual`: sobrou algum CTA do original?
- `content_type`: `"news"` / `"analysis"` / `"evergreen"`

**Custo estimado:** ~$0,24/mês adicional.

### Remoção de CTA (4 camadas)

O sistema remove frases como "Thank you for reading, don't forget to subscribe!" em 4 etapas progressivas de limpeza:

1. **Literal**: string exact match
2. **Sentence regex**: regex flexível com variações de apóstrofos/espaços
3. **Paragraph regex**: regex que remove parágrafos inteiros com padrões CTA
4. **Tag cleanup**: remove tags HTML vazias deixadas pelas remoções anteriores

Se CTA ainda for detectado após as 4 camadas, o artigo é **rejeitado** (`FAILED` no banco).

---

## 10. Linkagem Interna Automática

### Como funciona

1. Cada artigo publicado é salvo no `link_store` (SQLite, tabela `link_store`)
2. O link store guarda os **200 artigos mais recentes** com: título, URL, categoria, entidade
3. Ao processar novos artigos, `add_internal_links()` busca artigos relacionados e insere até **6 links** no corpo

### Prioridade dos links

1. **PILAR_POSTS** (lista manual em `config.py`) — máxima prioridade
2. Mesma categoria que o artigo atual
3. Mesma entidade detectada (`cluster_engine.score_event()`)
4. Outros artigos recentes

### Onde os links são inseridos

- Apenas em parágrafos `<p>` normais
- **Nunca** dentro de: `<a>`, `<h1>`–`<h6>`, `<blockquote>`, `<code>`, `<pre>`, `<figure>`, `<figcaption>`
- Máximo de 6 links por artigo (hard cap)

### Arquivo `data/internal_links.json`

Este arquivo é um mapa estático de links que pode ser carregado como fallback. Mantenha-o atualizado ou deixe vazio (`{}`).

---

## 11. Extratores por Site de Origem

### Como funciona

O `ContentExtractor` em `extractor.py`:
1. Faz HTTP GET da URL de origem
2. Aplica cleaner específico por domínio (se existir em `CLEANER_FUNCTIONS`)
3. Usa **Trafilatura** para extrair texto principal
4. Fallback para BeautifulSoup se Trafilatura falhar

### Cleaners disponíveis

Definidos em `app/cleaners.py` e mapeados em `pipeline.py`:

```python
CLEANER_FUNCTIONS = {
    'screenrant.com': clean_html_for_screenrant,
    'globo.com':      clean_html_for_globo_esporte,
}
```

O cleaner de ScreenRant remove:
- `display-cards` (widgets de artigos relacionados)
- Caixas de destaque e ads
- Legendas em inglês de imagens (`img[alt]`)

### Adicionando um novo extrator

1. Crie a função em `app/cleaners.py`:

```python
def clean_html_for_meusite(soup: BeautifulSoup) -> BeautifulSoup:
    # Remover elementos indesejados específicos do site
    for el in soup.select('.ad-unit, .newsletter-box, .related-posts'):
        el.decompose()
    return soup
```

2. Registre em `pipeline.py`:

```python
CLEANER_FUNCTIONS = {
    'screenrant.com': clean_html_for_screenrant,
    'meusite.com':    clean_html_for_meusite,   # ← adicionar
}
```

---

## 12. Token Tracking e Controle de Custos

### Onde os dados ficam

```
logs/tokens/
├── tokens_2025-01-15.jsonl     # Log JSONL por dia
├── tokens_2025-01-16.jsonl
└── token_stats.json            # Estatísticas acumuladas
```

### Formato do log (`.jsonl`)

Cada linha é um JSON com:
```json
{
  "timestamp": "2025-01-15T14:32:11",
  "api_type": "rewrite",
  "model": "gemini-2.5-flash-lite",
  "prompt_tokens": 2847,
  "completion_tokens": 1203,
  "source_url": "https://screenrant.com/...",
  "article_title": "Marvel anuncia...",
  "wp_post_id": 75668
}
```

### Estimativa de custo

Com Gemini 2.5 Flash Lite (Tier Gratuito):
- **60 requisições/minuto** por chave
- Com 2 chaves em rotação: até 120 req/min teórico
- Pipeline usa **1 req/artigo** + ocasional QA Camada 2
- ~10–30 artigos/dia = custo praticamente zero no tier gratuito

### Como monitorar

```bash
# Ver tokens do dia atual
cat logs/tokens/tokens_$(date +%Y-%m-%d).jsonl | python -c "
import sys, json
total_p = total_c = 0
for line in sys.stdin:
    d = json.loads(line)
    total_p += d.get('prompt_tokens', 0)
    total_c += d.get('completion_tokens', 0)
print(f'Prompt: {total_p} | Completion: {total_c} | Total: {total_p+total_c}')
"
```

---

## 13. Manutenção e Monitoramento

### Logs principais

| Arquivo | Conteúdo |
|---|---|
| `logs/pipeline.log` | Log completo do pipeline (INFO + acima) |
| `logs/tokens/*.jsonl` | Tokens consumidos por artigo |
| `debug/ai_response_*.json` | Resposta bruta da IA por artigo publicado |

### Banco SQLite

```bash
# Ver artigos processados hoje
sqlite3 data/app.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"

# Ver últimos artigos falhados
sqlite3 data/app.db "SELECT title, source_id, failure_reason FROM articles WHERE status='FAILED' ORDER BY created_at DESC LIMIT 10;"

# Ver link store
sqlite3 data/app.db "SELECT title, url, category FROM link_store ORDER BY published DESC LIMIT 10;"

# Ver fila evergreen pendente
sqlite3 data/app.db "SELECT entity, template, scheduled_for, status FROM evergreen_queue WHERE status='pending' ORDER BY scheduled_for;"
```

### Reiniciar o pipeline (Windows)

```powershell
# Verificar se está rodando
Get-Process python

# Matar processo
Get-Process python | Stop-Process

# Reiniciar
cd "e:\Área de Trabalho 2\Portal The News\Nerd\TheNerd-MN26"
.venv\Scripts\activate
python main.py
```

### Testar sem publicar

Para testar extração + IA sem publicar no WordPress:

```python
# Editar app/config.py temporariamente:
# Comente a linha do WORDPRESS_CONFIG e adicione:
PIPELINE_CONFIG['dry_run'] = True
```

Ou use `python main.py --once` e monitore os logs.

### Limpeza de registros antigos

O módulo `app/cleanup.py` remove artigos processados após `CLEANUP_AFTER_HOURS` horas (padrão: 72h). Isso evita crescimento ilimitado do banco SQLite.

### Circuit breaker por feed

Se um feed falhar **3 vezes consecutivas**, o pipeline pula automaticamente aquele feed no próximo ciclo e reseta o contador. Isso evita loops de erro em feeds instáveis.

---

## 14. Histórico de Commits Importantes

| Commit | Descrição |
|---|---|
| `1d895be` | Fix: `AI_API_KEYS` não definido em `semantic_qa_flash` |
| `3cb4a9c` | Evergreen: imagem destacada da biblioteca WP existente |
| `72a716f` | Prompt: substituir mínimo de palavras por regra de fidelidade (v1) |
| `7dba824` | Prompt fidelidade v2 + `max_output_tokens` 4096→8192 |
| `d3d5b03` | Prompt: detecção Tipo A (notícia) / Tipo B (listicle) |
| `c0470ae` | HTML: remover links `/tag/` inventados pela IA |
| `3bb5be2` | HTML: `downgrade_h1_to_h2()` + regra no prompt (`NUNCA <h1>`) |

---

## 15. Problemas Conhecidos e Soluções

### `FutureWarning: google.generativeai`

**Sintoma:**
```
FutureWarning: google.generativeai is deprecated. Use google.genai instead.
```

**Causa:** `app/ai_client_gemini.py` usa o SDK legado `google-generativeai`.

**Solução pendente (não crítica):** Migrar para `google-genai`:
```bash
pip install google-genai
# e atualizar import em ai_client_gemini.py
```

---

### `[PUBLISHING] Entrada: 0 | Saída: 0 | Total: 0`

**Sintoma:** Logs mostram tokens zerados na etapa de publicação.

**Causa:** Comportamento intencional. O registro com tokens zerados é criado ao publicar apenas para associar o `wp_post_id` ao token log. Os tokens reais já foram registrados pelo `AIProcessor` no momento da chamada ao Gemini.

**Solução:** Sem ação necessária. Verifique os tokens reais nos arquivos `.jsonl`.

---

### Post com 5000+ links no schema

**Sintoma:** Ferramenta de análise reporta milhares de links na página.

**Causa:** Widget "Categorias" do tema WordPress listando centenas de categorias no sidebar — não é problema do pipeline.

**Solução:** Desabilitar ou limitar o widget de categorias no tema WordPress.

---

### Artigos publicados com H1 em vez de H2

**Sintoma:** Auditoria mostra `h1_count=2` nos posts.

**Causa:** A IA gerava `<h1>` no corpo do artigo. O WordPress já injeta um `<h1>` automático com o título.

**Status:** ✅ Corrigido em `3bb5be2` com `downgrade_h1_to_h2()`.

---

### Links `/tag/algo` inválidos no conteúdo

**Sintoma:** Artigos publicados com links `<a href="/tag/marvel">Marvel</a>` apontando para 404.

**Causa:** IA inventava links de tag não existentes.

**Status:** ✅ Corrigido em `c0470ae` com `strip_ai_tag_links()`.

---

### Artigo com CTA em inglês publicado

**Sintoma:** Post contém "Thank you for reading this post, don't forget to subscribe!".

**Causa:** Frase escapou das camadas de limpeza.

**Diagnóstico:** Verifique `debug/ai_response_*.json` para o artigo específico e adicione o padrão às listas `nuclear_phrases` ou `cta_patterns` em `pipeline.py`.

---

## Apêndice: Variáveis de Ambiente — Referência Completa

| Variável | Padrão | Descrição |
|---|---|---|
| `GEMINI_KEY_1` | — | Chave Gemini principal (obrigatória) |
| `GEMINI_KEY_2` | — | Chave Gemini secundária (rotação) |
| `GEMINI_KEY_N` | — | Chaves adicionais (padrão `GEMINI_*`) |
| `GEMINI_MODEL_ID` | `gemini-2.5-flash-lite` | Modelo Gemini a usar |
| `AI_MODEL` | `gemini-2.5-flash-lite` | Alias do modelo |
| `WORDPRESS_URL` | — | URL do site WP sem barra final |
| `WORDPRESS_USER` | — | Usuário WP (editor/admin) |
| `WORDPRESS_PASSWORD` | — | Application Password do WP |
| `LOG_LEVEL` | `INFO` | Nível de log (DEBUG/INFO/WARNING/ERROR) |
| `CHECK_INTERVAL_MINUTES` | `15` | Intervalo do scheduler em minutos |
| `MAX_ARTICLES_PER_FEED` | `3` | Máx. artigos por feed por ciclo |
| `MAX_PER_FEED_CYCLE` | `3` | Alias do acima |
| `MAX_PER_CYCLE` | `10` | Máx. total de artigos por ciclo |
| `ARTICLE_SLEEP_S` | `120` | Pausa entre artigos (segundos) |
| `PER_ARTICLE_DELAY_SECONDS` | `8` | Delay extra entre artigos |
| `PER_FEED_DELAY_SECONDS` | `15` | Delay entre feeds |
| `FEED_STAGGER_S` | `45` | Escalonamento entre feeds |
| `IMAGES_MODE` | `hotlink` | `hotlink` ou `upload` |
| `PUBLISHER_LOGO_URL` | — | URL do logo para schema |
| `SECRET_KEY` | — | Chave secreta para tokens internos |
| `CLEANUP_AFTER_HOURS` | `72` | Limpar registros após N horas |

---

*Documentação gerada a partir do código-fonte — versão branch `main`.*
