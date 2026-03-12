# 📋 LEVANTAMENTO COMPLETO - TheNews Máquina Nerd

**Data**: 18 de Fevereiro de 2026  
**Status Final**: Análise concluída  
**Versão do Projeto**: 1.0 (Produção)

---

## 1) VISÃO GERAL

### Propósito Declarado
[IMPLEMENTADO] Sistema automatizado que **lê feeds RSS de notícias sobre filmes, séries e games**, reescreve o conteúdo usando IA (Google Gemini), aplica otimizações SEO e publica automaticamente em WordPress.

### Problema Que Tenta Resolver
[IMPLEMENTADO] Automação de produção de conteúdo editorial com:
- Leitura contínua de múltiplas fontes RSS
- Reescrita inteligente com IA para evitar duplicação
- Otimização SEO automática (títulos, imagens, meta-dados)
- Publicação direta em WordPress sem intervenção manual
- Rastreamento completo de tokens/custos de IA

### Outputs Gerados
[IMPLEMENTADO]
- **Posts publicados em WordPress** (com metadados SEO)
- **Arquivos JSON** com resposta da IA (salvos em `debug/ai_response_batch_*.json`)
- **Logs estruturados** (em `logs/` e `logs/tokens/`)
- **Banco de dados SQLite** (`data/app.db`) com histórico de artigos
- **Dashboard Web** (porta 5000) com métricas em tempo real
- **News Sitemap XML** (consumido pelo Google News)

### Consumidores Dos Outputs
[IMPLEMENTADO]
- **WordPress** - publica conteúdo via REST API
- **Google News** - indexa via news-sitemap.xml
- **Google Search Console** - rastreamento de performance
- **Dashboard interno** - visualização de métricas
- **Logs/análise** - scripts de auditoria e debugging

---

## 2) FONTES DE DADOS

### Tipos de Fontes Usadas

#### RSS/Feeds
[IMPLEMENTADO]
- **ScreenRant Movie Lists** (`screenrant_movie_lists`)
- **ScreenRant Movie News** (`screenrant_movie_news`)
- **ScreenRant TV** (`screenrant_tv`)
- Todas com classe `FeedReader` usando `feedparser 6.0.11+`

#### APIs Externas
[IMPLEMENTADO]
- **Google Gemini 2.5-Flash-Lite** - reescrita de conteúdo
- **WordPress REST API v2** - publicação
- **TMDb API v3** - [PARCIAL] dados enriquecidos de filmes/séries (estrutura pronta, não usado no pipeline principal)

#### Scraping/Extração
[IMPLEMENTADO]
- **Trafilatura 2.0.0+** - extração de conteúdo completo das URLs
- **BeautifulSoup4 4.13.4+** - parsing HTML avançado

#### Arquivos Locais
[IMPLEMENTADO]
- **universal_prompt.txt** - prompt único para IA (284 linhas)
- **.env** - configuração sensível (chaves de API, URLs)

### Como Fontes Entram no Sistema
[IMPLEMENTADO]
```
RSS Feed → FeedReader.read() → normalize_item() → Database(seen_articles)
         ↓
    ContentExtractor._fetch_html()
         ↓
    HTML+Metadados → AIProcessor.generate_text()
         ↓
    JSON resposta → WordPressClient.publish()
```

### Normalização/Processamento
[IMPLEMENTADO]
- **Normalização de data**: ISO 8601 com fallback para múltiplos formatos
- **Deduplicação**: por `external_id` (guid/link/hash)
- **Metadata extraction**: autor, summary, published date
- **CTA removal**: 5 camadas (extractor, prompt, pipeline, html_utils, wordpress)

### O Que Foi Tentado e Abandonado
[DESCARTADO]
- **Synthetic RSS** (`app/synthetic_rss.py`) - módulo para extrair links via JSON-LD de páginas; código existe mas não integrado ao pipeline principal
- **TMDB Hub** (`app/movie_hub_manager.py`) - sistema completo de sincronização de filmes/séries do TMDb para banco local; estrutura pronta, nunca ativada (config `TMDB_ENABLED=false`)
- **Movie Pages Generator** (`app/page_generator.py`, `app/movie_repository.py`) - geração de páginas HTML para catálogo de filmes; código 100% funcional, sem uso

---

## 3) PIPELINE / FLUXO DE PROCESSAMENTO

### Etapas Implementadas (Em Ordem)

#### 1. **Leitura de Feeds** [IMPLEMENTADO]
- Executa em sequência: `PIPELINE_ORDER = [screenrant_movie_lists, screenrant_movie_news, screenrant_tv]`
- `FeedReader.read()` → retorna lista de artigos normalizados
- Limite: `MAX_ARTICLES_PER_FEED = 3` artigos por feed (configurável)

#### 2. **Deduplicação** [IMPLEMENTADO]
- Consulta `seen_articles` no SQLite
- Busca por `external_id` e `url`
- Status: PENDING, PROCESSING, PUBLISHED, FAILED

#### 3. **Download de Conteúdo** [IMPLEMENTADO]
- `ContentExtractor._fetch_html(url)` com timeout 20-25s
- Segue redirecionamentos, respeita User-Agent
- Aplica limpeza específica por domínio (ex: Globo Esporte tem cleaner próprio)

#### 4. **Parsing HTML** [IMPLEMENTADO]
- Trafilatura extrai conteúdo principal
- BeautifulSoup refina extração
- Extrai título, corpo, imagens, vídeos YouTube, metadados

#### 5. **Limpeza de Imagens** [IMPLEMENTADO]
- `validate_and_fix_figures()` - desescapa HTML em atributos
- `unescape_html_content()` - converte entidades HTML
- Valida figcaption + alt text
- Remove imagens de "author box", "profiles", placeholders, trackers

#### 6. **Remoção de CTAs** [IMPLEMENTADO - 5 CAMADAS]
- **Camada 1**: `ContentExtractor` (~1100-1400 linhas) - remove CTAs durante extração
- **Camada 2**: `universal_prompt.txt` - instrui IA a remover CTAs
- **Camada 3**: `AI_SYSTEM_RULES` (em `ai_processor.py`) - reforça proibição
- **Camada 4**: `pipeline.py` - limpeza agressiva pós-IA
- **Camada 5**: `WordPressClient._publish_post()` - validação final pré-publicação

Detecta 27+ padrões de CTA em **PT-BR e EN**:
- "thank you for reading", "subscribe", "obrigado por ler", "inscreva-se", etc.

#### 7. **Processamento de IA** [IMPLEMENTADO]
```python
AIProcessor.generate_text(prompt) 
  ↓
AIClient.generate_text() [Google Gemini 2.5-flash-lite]
  ↓
TokenTracker.log_tokens() [Registra entrada/saída]
```
- Retorna JSON com: `titulo_final`, `conteudo_final`, `meta_description`, `focus_keyphrase`, `categorias`, `tags_sugeridas`, `yoast_meta`
- Timeout: 6 segundos mínimo entre requisições (rate limiting)
- Backoff exponencial: 20-300s em caso de 429/erro

#### 8. **Otimização de Título** [IMPLEMENTADO]
- `seo_title_optimizer.optimize_title()`
- Score 0-100 baseado em:
  - Tamanho: 55-65 caracteres (ótimo)
  - Verbo de ação (presente, não infinitivo)
  - Entidade no início
  - Sem clickbait, sensacionalismo
  - Concordância perfeita
- Detecta/remove: "você não vai acreditar", "surpreendente", "nerfado", "morto", etc.

#### 9. **Validação de Título** [IMPLEMENTADO]
- `TitleValidator` - checklist de 15 pontos
- Rejeita: verbos infinitivos, >65 chars, gírias, etc.
- Se falhar: tenta corrigir até 3 vezes

#### 10. **Linkagem Interna** [IMPLEMENTADO]
- `add_internal_links()` - injeta links para posts pilares
- Máximo: 6 links por artigo
- Mapeia tags para URLs internas

#### 11. **Conversão para Gutenberg** [IMPLEMENTADO]
- `html_to_gutenberg_blocks()` - converte HTML para blocos Gutenberg
- Preserva estrutura semântica
- Suporta `<!-- wp:paragraph -->`, `<!-- wp:image -->`, `<!-- wp:heading -->`, etc.

#### 12. **Validação de CTA Final** [IMPLEMENTADO]
- `detect_forbidden_cta()` - regex 27+ padrões
- Se detectado: rejeta publicação, registra erro

#### 13. **Upload de Imagens** [IMPLEMENTADO]
- `MediaManager.upload_image()` - faz upload para WordPress
- Modo: `hotlink` (padrão) ou `download_upload` (configurável)
- Associa featured image ao post

#### 14. **Publicação WordPress** [IMPLEMENTADO]
- `WordPressClient.publish_post()` - POST para `/posts`
- Campos: title, content, excerpt, categories, tags, featured_media, meta_yoast
- Validação: tamanho payload, fields inválidos, categorias existence check
- Retorna `wp_post_id`

#### 15. **Correlação JSON→Post** [IMPLEMENTADO]
- Salva JSON em `debug/ai_response_batch_{slug}_{timestamp}.json`
- Registra `wp_post_id` no banco de dados
- Permite rastreabilidade completa

#### 16. **Rastreamento de Tokens** [IMPLEMENTADO]
- `TokenTracker.log_tokens()` registra em `logs/tokens_{YYYY-MM-DD}.jsonl`
- Campos: timestamp, prompt_tokens, completion_tokens, model, cost_usd, wp_post_id, source_url
- Arquivo diário JSONL (1 registro por linha)

### Ciclo de Execução
[IMPLEMENTADO]
- **Agendamento**: APScheduler (cron)
- **Frequência**: A cada 15 minutos (configurável via `CHECK_INTERVAL_MINUTES`)
- **Horário**: 9h-19h horário de Brasília (weekdays/weekends configurável)
- **Modo Teste**: `python main.py --once` executa uma vez e sai
- **Modo Contínuo**: `python main.py` roda agendador infinito

### Delays/Timeouts Entre Etapas
[IMPLEMENTADO]
- Entre feeds: 15s (`PER_FEED_DELAY_SECONDS`)
- Entre artigos: 8s (`PER_ARTICLE_DELAY_SECONDS`)
- Entre publicações: 30s (`BETWEEN_PUBLISH_DELAY_S`)
- Download: 20-25s timeout
- IA: 6s mínimo entre requisições

### Onde o Fluxo Quebra/É Interrompido
[IMPLEMENTADO]
- **URL inválida**: marca como FAILED, continua próximo
- **Extração vazia**: marca como FAILED, continua
- **IA timeout/429**: retry com backoff exponencial (até 300s), tenta outra chave
- **WordPress erro 500**: tenta novamente até 3 vezes, marca como FAILED
- **CTA detectado**: rejeita publicação, salva JSON em debug/ como "falhou"
- **Quota Gemini**: ciclo aguarda reset (respeita todos os dias à meia-noite UTC)

### Síncrono vs Assíncrono
[PARCIAL]
- **Síncrono**: Fluxo principal (leitura → extração → IA → publicação) é sequencial
- **Assíncrono**: Não há uso de `asyncio` ou threads, apesar de imports em alguns arquivos
- **Fila de Artigos**: Classe `ArticleQueue` existe mas não usada no pipeline ativo

---

## 4) LÓGICA DE DECISÃO / PRIORIDADE

### O que processar primeiro?
[IMPLEMENTADO]
```python
PIPELINE_ORDER = [
    'screenrant_movie_lists',
    'screenrant_movie_news', 
    'screenrant_tv'
]
```
- Ordem fixa, não baseada em data/prioridade
- Max 3 artigos por feed por ciclo
- Se uma fonte falhar, continua na próxima

### O que é Considerado Válido?
[IMPLEMENTADO]
- **URL**: deve ser HTTP/HTTPS válido
- **Conteúdo**: mínimo 200 caracteres
- **Imagens**: mínimo 300px, não deve ser logo/avatar/tracker
- **Título**: 55-65 chars, presente, não vazio
- **CTA**: NÃO deve conter padrões (27+ detectados)
- **Yoast Meta**: deve ter focus_keyphrase + meta_description válida

### O que é Considerado Duplicado?
[IMPLEMENTADO]
- **Mesma URL**: consulta campo `url` em `seen_articles`
- **Mesmo external_id**: consulta campo `external_id` (guid/link hash)
- **Mesmo título**: não há comparação, é possível duplicação por título

### O que é Descartado?
[IMPLEMENTADO]
- **CTAs/Garbage**: detected por `detect_forbidden_cta()` e removido antes publicação
- **Imagens quebradas**: removidas se não conseguir validar/corrigir
- **Links internos inválidos**: descartados se URL malformada
- **Posts sem featured_image**: criado placeholder ou descartado (configurável)

### Critérios Obsoletos/Experimentais
[DESCARTADO]
- **Sufixo " lança"**: era adicionado a títulos (BUG_FIX_LANCA_SUFFIX.py desativou)
- **English caption filtering**: (`ENGLISH_CAPTIONS_FILTERING.md`) - tentativa de bloquear captions em inglês, não integrada
- **TMDB enrichment**: estrutura pronta, nunca ativada; config `TMDB_ENABLED=false`

---

## 5) ESTRUTURA DE DADOS

### Banco de Dados
[IMPLEMENTADO] SQLite em `data/app.db`

#### Tabelas Principais
1. **`seen_articles`** [IMPLEMENTADO]
   - `id` INTEGER PRIMARY KEY
   - `source_id` TEXT (screenrant_movie_lists, etc)
   - `external_id` TEXT (guid ou hash)
   - `url` TEXT
   - `title` TEXT
   - `status` TEXT (PENDING, PROCESSING, PUBLISHED, FAILED)
   - `published_at` DATETIME
   - `inserted_at` DATETIME
   - `error_reason` TEXT

2. **`posts`** [IMPLEMENTADO]
   - `id` INTEGER PRIMARY KEY
   - `source_id` TEXT
   - `external_id` TEXT
   - `wp_post_id` INTEGER (ID do post em WordPress após publicação)
   - `url` TEXT
   - `title_original` TEXT
   - `title_final` TEXT
   - `slug` TEXT
   - `status` TEXT
   - `created_at` DATETIME
   - `json_path` TEXT (caminho do arquivo JSON salvo)

3. **`failures`** [IMPLEMENTADO]
   - `id` INTEGER PRIMARY KEY
   - `article_id` INTEGER (FK para seen_articles)
   - `error_type` TEXT (extraction_failed, ai_timeout, wordpress_500, cta_detected)
   - `error_message` TEXT
   - `retry_count` INTEGER
   - `created_at` DATETIME

4. **`api_usage`** [IMPLEMENTADO]
   - `id` INTEGER PRIMARY KEY
   - `api_type` TEXT (gemini, wordpress)
   - `usage_count` INTEGER
   - `last_used` DATETIME
   - `inserted_at` DATETIME

5. **`movies`** [PARCIAL] (Models/ORM SQLAlchemy)
   - Estrutura completa para TMDb integration
   - Campos: `tmdb_id`, `title`, `slug`, `overview`, `release_date`, `runtime`, `budget`, `revenue`, `rating`, `poster_url`, `backdrop_url`, `is_trending`, `updated_at`
   - **Status**: Definido, nunca usado em produção

6. **`tv_series`** [PARCIAL]
   - Similar a movies
   - **Status**: Definido, nunca usado

7. **`genres`** [PARCIAL]
   - Tabela auxiliar para categorizar filmes/séries
   - **Status**: Definido, nunca usado

8. **`actors`** [PARCIAL]
   - Armazena dados de atores do TMDb
   - **Status**: Definido, nunca usado

#### Associações M2M
[PARCIAL]
- `movie_genre_association`
- `tv_genre_association`
- `actor_movie_association`
- `actor_tv_association`
- **Status**: Todas definidas, nunca usadas

### Estrutura de Arquivos JSON de IA

[IMPLEMENTADO] Formato salvo em `debug/ai_response_batch_{slug}_{YYYY-MM-DD-HHMMSS}.json`

```json
{
  "resultados": [
    {
      "titulo_final": "Marvel confirma novo filme",
      "conteudo_final": "<p>O estúdio...</p>",
      "meta_description": "Marvel anuncia novo filme em 2025",
      "focus_keyphrase": "Marvel novo filme",
      "related_keyphrases": ["Marvel 2025", "filme Marvel"],
      "slug": "marvel-novo-filme",
      "categorias": [
        {
          "nome": "Marvel",
          "grupo": "franquias",
          "evidence": "The Marvel logo appears..."
        }
      ],
      "tags_sugeridas": ["Marvel", "Filmes", "2025"],
      "yoast_meta": {
        "_yoast_wpseo_focuskw": "Marvel novo filme",
        "_yoast_wpseo_metadesc": "Marvel anuncia nuevo..."
      }
    }
  ]
}
```

### Modelos ORM/Pydantic
[NÃO IDENTIFICADO] - não há Pydantic, apenas dataclasses simples:
```python
@dataclass
class Article:
    wp_id: str
    title: str
    excerpt: str
    content: str
    status: str
    source_url: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[Dict] = None
```

### Status/Enums
[IMPLEMENTADO]
- **Article Status**: PENDING, PROCESSING, PUBLISHED, FAILED
- **Error Type**: extraction_failed, ai_timeout, wordpress_500, cta_detected, invalid_url, invalid_field

### Campos Aparentemente Obsoletos
[DESCARTADO]
- **`Article.category`**: sempre None, não usado (vai por `SOURCE_CATEGORY_MAP`)
- **`Article.metadata`**: estrutura definida, nunca preenchida
- **Movie models**: 100% completo, 0% usado

---

## 6) CONFIGURAÇÃO E CONTROLE

### Variáveis de Ambiente (.env)
[IMPLEMENTADO]
```bash
# Chaves IA (múltiplas suportadas)
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...
GEMINI_API_KEY_N=AIza...

# Model (default gemini-2.5-flash-lite)
AI_MODEL=gemini-2.5-flash-lite

# WordPress
WORDPRESS_URL=https://seu-site.com
WORDPRESS_USER=api_user
WORDPRESS_PASSWORD=app_password

# TMDb (desativado por padrão)
TMDB_ENABLED=false
TMDB_API_KEY=sua_chave

# Agendamento
CHECK_INTERVAL_MINUTES=15 (padrão)
MAX_ARTICLES_PER_FEED=3 (padrão)
MAX_PER_FEED_CYCLE=3 (padrão)
MAX_PER_CYCLE=10 (padrão)

# Rate Limiting
AI_MIN_INTERVAL_S=6 (padrão)
BACKOFF_BASE_S=20 (padrão)
BACKOFF_MAX_S=300 (padrão)

# Delays (em segundos)
PER_ARTICLE_DELAY_SECONDS=8
PER_FEED_DELAY_SECONDS=15
BETWEEN_PUBLISH_DELAY_S=30
ARTICLE_SLEEP_S=120

# Media
IMAGES_MODE=hotlink (ou download_upload)
PUBLISHER_LOGO_URL=https://...

# Limpeza
CLEANUP_AFTER_HOURS=72
```

### Arquivos de Configuração
[IMPLEMENTADO]
- **`app/config.py`**: Centraliza todas as configs (155 linhas)
- **`universal_prompt.txt`**: Instrução para IA (284 linhas)
- **`.env.example`**: Template (não listado, presumido existir)

### Flags de Execução
[IMPLEMENTADO]
- `python main.py --once` : executa 1 ciclo e sai
- `python main.py`: executa agendador (9h-19h cada 15min)
- `python dashboard.py`: inicia web interface (porta 5000)
- Scripts em `scripts/`: diversos modos de análise/monitoramento

### Limites Conhecidos
[IMPLEMENTADO]
- **Max tags por post**: 5
- **Max imagens a injetar**: 6
- **Max links internos**: 6
- **Tamanho máximo de título**: 65 caracteres (target)
- **Meta description**: 140-155 caracteres
- **Rate limit IA**: 6 segundos mínimo entre requisições
- **Quota Gemini**: Depende do plano (free/paid)
- **Timeout HTTP**: 20-25 segundos por requisição
- **Featured image**: 1200x630px recomendado (não obrigatório)

### Modos Especiais
[IMPLEMENTADO]
- **Debug**: Salva JSONs em `debug/failed_ai_*.json`
- **Production**: Apenas posts com status PUBLISHED vão pro destino

---

## 7) LOGS E MONITORAMENTO

### O Que É Logado Atualmente
[IMPLEMENTADO]
- **`logs/app.log`**: INFO/WARNING/ERROR do pipeline principal
  - Ciclos iniciados/finalizados
  - Artigos processados
  - Erros de extração/IA/WordPress
  - Tempo decorrido
  
- **`logs/tokens/tokens_YYYY-MM-DD.jsonl`**: Registro diário de tokens
  - Entrada (prompt_tokens)
  - Saída (completion_tokens)
  - Timestamp
  - Modelo usado
  - wp_post_id (correlação)
  - source_url
  - Custo estimado USD
  - Status (success/failure)

- **`logs/tokens/token_stats.json`**: Estatísticas agregadas
  - Total tokens por dia/semana/mês
  - Custo total
  - Taxa de sucesso

- **`logs/tokens/token_debug.log`**: Debug detalhado de tokens
  - Rastreamento de anomalias
  - Tokens zerados aviso
  - Tentativas de retry

### Onde Logs Ficam
[IMPLEMENTADO]
```
logs/
├── app.log                    (pipeline principal)
├── tokens/
│   ├── tokens_2026-02-05.jsonl
│   ├── tokens_2026-02-04.jsonl
│   ├── token_stats.json
│   └── token_debug.log
└── (rotação automática após 5MB)
```

### Logs Planejados Mas Não Implementados
[NÃO IDENTIFICADO]
- Perfil de performance (tempo por etapa)
- Auditoria de CTA removal (antes/depois)
- Monitoramento de saúde geral (uptime, erros)

### Métricas Existentes
[IMPLEMENTADO]
- **Dashboard Web**: 
  - Posts recentes
  - Contador: seen, published, failed
  - Uso de API (últimas 24h)
  - Próximo ciclo agendado
  - Tópicos de trending
  
- **Scripts de Análise** (`scripts/`):
  - `seo_audit_articles.py` - Score SEO dos posts
  - `token_logs_viewer.py` - Visualização de tokens
  - `show_full_post_data.py` - Detalhes com tokens
  - `find_json.py` - Procura JSON por slug

---

## 8) INTEGRAÇÕES

### Serviços Externos Integrados
[IMPLEMENTADO]
1. **Google Gemini 2.5-Flash-Lite**
   - Via `google-generativeai` SDK
   - Múltiplas chaves com fallback
   - Rate limiting: 6s mínimo, 429 retry com backoff
   - Resposta: JSON estruturado

2. **WordPress REST API v2**
   - Autenticação via app password
   - POST `/posts` com metadados completos
   - Upload de mídia via `/media`
   - Categorias/tags/meta Yoast

3. **Google News Sitemap**
   - XML gerado por WordPress/plugin
   - Consumido por Google News
   - Inclui: artigo, título, URL, data, imagem

### APIs Integradas Mas Não Ativas
[PARCIAL]
1. **The Movie Database (TMDb) v3**
   - Classe `TMDbClient` 100% funcional
   - Endpoints: search_movie, search_tv, get_trending, get_upcoming
   - Integrado em `MovieHubManager`
   - **Status**: `TMDB_ENABLED=false` por default
   - **Nunca acionado**: não há chamada em pipeline.py

### Integrações Descartadas
[DESCARTADO]
- **Synthetic RSS** - módulo `app/synthetic_rss.py` para extrair links via JSON-LD; não está no pipeline
- **Movie Hub Pages** - geração de páginas de catálogo de filmes; código 100% pronto, nunca usado

### Dependências Críticas
[IMPLEMENTADO]
- **feedparser 6.0.11+** (RSS parsing)
- **trafilatura 2.0.0+** (content extraction)
- **google-generativeai** (Gemini API)
- **requests** (HTTP)
- **beautifulsoup4 4.13.4+** (HTML parsing)
- **apscheduler 3.11.0+** (scheduling)
- **flask 3.1.1+** (dashboard)
- **sqlalchemy** (ORM TMDb, não usado)
- **tmdbv3api** (TMDb client, não usado)
- **pytz** (timezone handling)

---

## 9) AUTOMAÇÃO E EXECUÇÃO

### Como É Executado Hoje
[IMPLEMENTADO]
```bash
# Produção - roda contínuo
python main.py

# Teste único
python main.py --once

# Dashboard
python dashboard.py
```

### Scheduler/Trigger
[IMPLEMENTADO] APScheduler com cron:
```python
scheduler.add_job(
    run_pipeline_cycle,
    'cron',
    minute='*/15',        # A cada 15 minutos
    hour='9-18',          # 9h até 18h:59
    timezone='America/Sao_Paulo'
)
```

### O Que Roda Automaticamente
[IMPLEMENTADO]
- Leitura de feeds RSS
- Extração de conteúdo
- Chamada à IA
- Publicação no WordPress
- Rastreamento de tokens
- Limpeza de dados antigos (após 72h)

### O Que Exige Ação Humana
[IMPLEMENTADO]
- Configurar `.env` com credenciais
- Instalar WPCode snippet para news-sitemap.xml
- Monitorar dashboard para erros
- Adicionar posts pilares em `PILAR_POSTS` para linkagem interna
- Atualizar feeds em `RSS_FEEDS` se necessário

### Features Pensadas Mas Não Implementadas
[PLANEJADO]
- **Priorização inteligente**: baseada em trending/relevância
- **Machine learning**: para prever sucesso de CTR/SEO
- **Análise de concorrência**: monitorar o que outros sites publicam
- **Feedback loop**: ajustar prompt com base em performance
- **Dashboard mobile**: app responsivo para mobile

---

## 10) DÍVIDA TÉCNICA E HISTÓRICO

### Trechos Comentados
[NÃO IDENTIFICADO] - código está bem organizado, poucos comentários "mortos"

### TODOs No Código
[IMPLEMENTADO]
```python
# app/movie_hub_manager.py:266
'genres': [],  # TODO: carregar gêneros relacionados
```
- Única instância encontrada; refere-se a feature TMDB não implementada

### Hacks Temporários
[IMPLEMENTADO]
- **BUG_FIX_LANCA_SUFFIX.py**: Script que desativa lógica de adicionar " lança" a títulos (bug antigo)
- **ENGLISH_CAPTIONS_FILTERING.md**: Tentativa de bloquear captions em inglês, não integrada
- **Nested try/except**: Em alguns pontos há tratamento genérico de exceção

### Funções Duplicadas
[NÃO IDENTIFICADO] - modularização está boa, não há duplicação óbvia

### Arquivos Aparentemente Obsoletos
[DESCARTADO]
- **`app/models.py`**: ORM SQLAlchemy 100% completo, nunca usado
- **`app/movies_repository.py`**: CRUD para filmes, nunca acionado
- **`app/movie_hub_manager.py`**: Orquestrador de TMDb, nunca usado
- **`app/page_generator.py`**: Gerador de HTML para catálogo, nunca usado
- **`app/tmdb_client.py`**: Cliente TMDb, funcional mas inativo
- **`app/tmdb_extended.py`**: Versão estendida de TMDb, inativa
- **`app/synthetic_rss.py`**: Extração JSON-LD, não integrada
- **`app/rss_builder.py`**: Construtor de RSS dinâmico, não usado
- **`app/batch_processor.py`**: Processamento em batch, não usado em pipeline.py
- **`app/task_queue.py`**: Fila de tarefas, classe existe mas não usada

### Decisões que Indicam Mudança de Rumo
[PARCIAL]
- **V1**: Provavelmente era projeto TVHub (toda a estrutura TMDB pronta)
- **V2**: Pivotar para RSS→WordPress (código atual)
- **Evidência**: 40%+ do código é TMDb/Movie que nunca é acionado
- **Timeline**: Documentação de 2025 (último ano) foca em RSS, não TMDb

### Refatorações Recentes
[IMPLEMENTADO]
1. **CTA Removal** (multiple dates)
   - 5 camadas de proteção implementadas
   - 27+ padrões de detecção
   - Changelog_CTA_REMOVAL.md (198 linhas)
   
2. **SEO Title Optimizer** (recent)
   - Módulo novo `app/seo_title_optimizer.py` (280 linhas)
   - Integrado em pipeline.py
   - Score 0-100 implementado

3. **Image Fixing** (recent)
   - Funções em `app/html_utils.py` novas
   - `unescape_html_content()`, `validate_and_fix_figures()`
   - Testes: test_image_fix.py, test_integrated_seo_images.py

4. **Token Tracking** (recent)
   - Sistema completo: `TokenTracker`, `TokenGuarantee`
   - Logs JSONL diários implementados
   - Rastreamento por WP post ID

5. **JSON Correlação** (recent)
   - JSONs salvos com slug no nome
   - Associados a `wp_post_id`
   - Scripts: find_json.py, reorganize_jsons.py

### Code Quality Issues
[IMPLEMENTADO]
- **Logging**: Bem estruturado, mas emojis em logs críticos (pode quebrar alguns parsers)
- **Error handling**: Genérico em alguns pontos (bare except)
- **Type hints**: Presentes em módulos novos, ausentes em código legado
- **Documentation**: Excelente (120+ KB em docs/), sparse em código

---

## 11) LIMITAÇÕES CONHECIDAS

### Gargalos Evidentes
[IMPLEMENTADO]
1. **Rate Limiting IA**: 6s mínimo entre requisições = máximo ~10 artigos/minuto
   - Em ciclo de 15 min: ~150 artigos teoricamente, mas delays entre feeds (15s) reduzem drasticamente
   - Na prática: ~3-10 artigos publicados por ciclo

2. **Dependência de Quota Gemini**: Free tier quota se esgota rapidamente
   - Sem tratamento de "quota reset" automático
   - Sistema aguarda ciclo inteiro se quota esgotada
   - Documentação menciona "reset todos os dias ao meio-dia UTC"

3. **Deduplicação Fraca**: 
   - Apenas por URL/external_id
   - Não há "fuzzy matching" de títulos
   - Se mesmo artigo publicado com títulos diferentes = duplicação

4. **Ordem Fixa de Feeds**:
   - Não há priorização por trending/relevância
   - Feeds processados sempre na mesma ordem
   - Algum feed lento bloqueia os seguintes

### Pontos Frágeis
[IMPLEMENTADO]
1. **Dependência de Chaves de API**: Se todas as 3 chaves Gemini estiverem em backoff, sistema inteiro trava
  
2. **WordPress Connectivity**: Sem retry automático sofisticado
   - 429/500 tem retry, mas timeout 20s é curto
   - Se WordPress cair, posts saem de PROCESSING mas não voltam para PENDING

3. **CTA Detection**: Regex baseado em normalização de texto
   - Pode falhar com variações criativas
   - Não tem ML/NLP, apenas pattern matching

4. **Database Locking**: SQLite com concorrência pode ter issues
   - Threads não usadas, mas se alguém adicionar, pode haver race conditions

5. **Image Validation**: Apenas verifica tamanho/domínio, não conteúdo real
   - Imagem pode estar morta (erro 404) e ainda ser adicionada

### O Que Claramente Não Escala
[IMPLEMENTADO]
1. **SQLite Database**: Sem índices em campos críticos
   - Busca por `url` em `seen_articles` pode ser lenta se milhões de registros
   - **Solução**: PostgreSQL para produção

2. **Sequential Processing**: Python síncrono, bloqueante
   - Cada etapa aguarda a anterior
   - Não aproveita multi-core ou I/O async
   - **Solução**: Asyncio + worker threads/processes

3. **Storage JSON em `debug/`**: Sem limpeza automática
   - JSONs acumulam indefinidamente
   - Documentação menciona rotação, não implementada

4. **Logging via Arquivo**: Sem logrotate integrado
   - Arquivos de log podem ficar gigantes
   - Configurado com maxBytes (5-10MB), mas controle manual

### Dependência de Ordem/Timing
[IMPLEMENTADO]
1. **Extracto antes da IA**: conteúdo extraído precisa estar bem formado
   - Se Trafilatura falhar, qualidade cai drasticamente
   - Fallback para BeautifulSoup simples não é robusto

2. **CTA Removal ordem**: 5 camadas dependem de cada uma
   - Se Layer 4 falhar, Layer 5 depende dela
   - Sem garantia de que todas as camadas rodam

3. **Newsletter Cleanup**: Agendada para 72h após publicação
   - Se sistema cair, limpeza não roda
   - Dados antigos podem ficar no banco indefinidamente

### Dependência de Sorte/Configuração
[IMPLEMENTADO]
1. **Feeds RSS Bem-Formados**: Teste assume feedparser consegue parsear
   - Feeds malformados/corrompidos quebram sem fallback claro
   
2. **URLs Acessíveis**: Browser bloqueado/rate-limited pode fazer sistema aguardar
   - Sem proxy rotation
   - User-Agent estatístico, mas simples

3. **WordPress Sempre Disponível**: Nenhum cache local de posts
   - Se publicação falha, post não fica em rascunho para retry
   - Status fica PROCESSING indefinidamente

---

## RESUMO EXECUTIVO - MATRIZ DE IMPLEMENTAÇÃO

| Seção | Status | % | Observação |
|-------|--------|---|-----------|
| 1. Visão Geral | [IMPLEMENTADO] | 100% | Totalmente funcional |
| 2. Fontes de Dados | [IMPLEMENTADO] 60% + [PARCIAL] 40% | 80% | TMDb estruturado, não ativo |
| 3. Pipeline/Fluxo | [IMPLEMENTADO] | 100% | 16 etapas completas |
| 4. Lógica Decisão | [IMPLEMENTADO] 90% + [DESCARTADO] 10% | 85% | Sufixo " lança" removido |
| 5. Estrutura Dados | [IMPLEMENTADO] 50% + [PARCIAL] 50% | 75% | Core OK, TMDb unused |
| 6. Configuração | [IMPLEMENTADO] | 100% | .env + config.py completos |
| 7. Logs/Monitore | [IMPLEMENTADO] 95% + [NÃO ID] 5% | 90% | Tokens track é robusto |
| 8. Integrações | [IMPLEMENTADO] 70% + [PARCIAL] 30% | 85% | TMDb pronto, offline |
| 9. Automação | [IMPLEMENTADO] | 100% | APScheduler funcional |
| 10. Dívida Técnica | [DESCARTADO] 40% + [IMPLEMENTADO] 60% | 60% | ~40% do código "morto" |
| 11. Limitações | [IMPLEMENTADO] | 100% | Bem documentadas |

---

## CÓDIGO MORTO (Arquivos Que Existem Mas Não São Usados)

```
app/
├── models.py                    [40% funções não usadas]
├── movie_hub_manager.py         [100% não acionado]
├── movie_repository.py          [100% não acionado] 
├── page_generator.py            [100% não acionado]
├── tmdb_client.py               [100% não acionado]
├── tmdb_extended.py             [100% não acionado]
├── synthetic_rss.py             [100% não integrado]
├── rss_builder.py               [100% não usado]
├── batch_processor.py           [100% definido, importado mas não chamado]
└── task_queue.py                [100% classe existe, nunca instanciada]
```

**Estimativa**: ~15% do código é "morto" (não executado em produção).

---

## STATUS FINAL POR OBJETIVO

| Objetivo | Status | Pronto Produção |
|----------|--------|-----------------|
| Ler RSS | ✅ [IMPLEMENTADO] | SIM |
| Extrair conteúdo | ✅ [IMPLEMENTADO] | SIM |
| Remover CTA | ✅ [IMPLEMENTADO] | SIM (5 camadas) |
| Otimizar título | ✅ [IMPLEMENTADO] | SIM |
| Chamar IA (Gemini) | ✅ [IMPLEMENTADO] | SIM |
| Publicar WordPress | ✅ [IMPLEMENTADO] | SIM |
| Rastrear tokens | ✅ [IMPLEMENTADO] | SIM |
| Dashboard | ✅ [IMPLEMENTADO] | SIM |
| TMDB Integration | ⚠️ [PARCIAL] | NÃO (desativado) |
| Synthetic RSS | ❌ [DESCARTADO] | NÃO |
| Movie Hub | ❌ [DESCARTADO] | NÃO |

**Conclusão**: **Sistema está 100% funcional para core RSS→WordPress. Features TMDb/Hub são estrutura pronta, propositalmente offline.**

---

## Próximos Passos Recomendados (Após Análise)

1. **Limpeza de Código Morto** (opcional)
   - Remover `models.py`, TMDb client, movie_hub, etc. (~1500 linhas)
   - Libera espaço, reduz complexidade

2. **Otimização de Performance**
   - Adicionar índices SQLite em campos críticos
   - Considerar PostgreSQL se escala crescer

3. **Melhorias de Resiliência**
   - Implementar cache local de posts (fallback se WP cair)
   - Melhorar retry de WordPress (exponential backoff)

4. **Expansão de Features** (if needed)
   - Ativar TMDB para enriquecimento de dados
   - Implementar machine learning para CTR prediction
   - Adicionar feedback loop automático

5. **Monitoramento Contínuo**
   - Expandir métricas (perfil de performance)
   - Alertas de falha (email/Slack)
   - Dashboard mobile-friendly
