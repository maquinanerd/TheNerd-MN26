# Integração TMDb (The Movie Database) - Máquina Nerd

## O que é TMDb?

**The Movie Database (TMDb)** é um banco de dados comunitário de filmes e séries com API pública gratuita.

### Características:
- ✅ **API Gratuita**: Sem custos iniciais
- ✅ **Rate Limit Generoso**: 40 requisições/10 segundos (muito mais que Gemini!)
- ✅ **Dados Ricos**: Metadados, imagens, elenco, trailers, ratings
- ✅ **Suporte Multi-idioma**: Português, inglês, etc.
- ✅ **Imagens de Qualidade**: Posters e backdrops em múltiplos tamanhos

---

## 🚀 Como Configurar

### Passo 1: Obter Chave API

1. Acesse: https://www.themoviedb.org/settings/api
2. Crie uma conta gratuita (se não tiver)
3. Clique em "Create" para criar uma nova app
4. Preencha:
   - App name: "Máquina Nerd"
   - App Type: "Personal Use"
   - Terms: Aceite
5. Copie a **API Key (v3 auth)**

### Passo 2: Configurar Variáveis de Ambiente

Adicione ao seu arquivo `.env`:

```env
# Habilita integração com TMDb
TMDB_ENABLED=true

# Sua chave API v3
TMDB_API_KEY=sua_chave_aqui

# Máximo de filmes/séries a adicionar por artigo
TMDB_MAX_ENRICHMENTS=3

# Recursos adicionais (opcional)
TMDB_EXTRACT_TRENDING=true      # Adiciona filmes em tendência
TMDB_EXTRACT_UPCOMING=true      # Adiciona próximos lançamentos
```

### Passo 3: Instalar Dependência

```bash
pip install tmdbv3api
# ou se usar o requirements.txt
pip install -r requirements.txt
```

---

## 📚 Arquivos Criados

### 1. `app/tmdb_client.py`
Cliente base para a API TMDb. Fornece métodos para:
- Buscar filmes/séries
- Obter detalhes completos
- Acessar tendências
- Gerar URLs de imagens

**Principais métodos:**
```python
client = TMDbClient(api_key)

# Buscar
movies = client.search_movie("Inception")
tvs = client.search_tv("Breaking Bad")

# Detalhes
movie_details = client.get_movie_details(movie_id)

# Tendências
trending = client.get_trending('movie', 'week')
upcoming = client.get_upcoming_movies()

# Formatação
formatted = client.format_movie_data(raw_data)
image_url = client.get_image_url(path, size='w500')
```

### 2. `app/content_enricher.py`
Enriquecedor de conteúdo. Extrai títulos de filmes/séries dos artigos e adiciona widgets.

**Principais métodos:**
```python
enricher = ContentEnricher()

# Buscar e enriquecer
movie = enricher.search_and_enrich_movie("Oppenheimer")
tv = enricher.search_and_enrich_tv("The Last of Us")

# Tendências
trending = enricher.get_trending_movies(limit=5)
upcoming = enricher.get_upcoming_movies(limit=5)

# Gerar widgets HTML
html = enricher.generate_movie_widget_html(movie)
html = enricher.generate_tv_widget_html(tv)

# Enriquecer artigo inteiro
content, media = enrich_article_with_tmdb(title, content)
```

---

## 💡 Casos de Uso

### 1. Enriquecer Artigos Automaticamente

Integrar no pipeline principal para adicionar widgets de filmes mencionados:

```python
from app.content_enricher import enrich_article_with_tmdb

# Após reescrever com IA
enriched_content, media_list = enrich_article_with_tmdb(
    article_title="O Melhor Filme de 2024",
    article_content=article_html
)

# Agora enriched_content tem widgets dos filmes mencionados
```

### 2. Criar Seções de Trending

Adicionar seção de filmes/séries em tendência:

```python
from app.content_enricher import ContentEnricher

enricher = ContentEnricher()
trending = enricher.get_trending_movies(limit=5)

for movie in trending:
    # Gerar cards ou widgets
    widget = enricher.generate_movie_widget_html(movie)
```

### 3. Posts Automáticos sobre Lançamentos

Criar artigos sobre próximos lançamentos:

```python
enricher = ContentEnricher()
upcoming = enricher.get_upcoming_movies(limit=3)

# Criar artigo: "3 Filmes que Você NÃO PODE Perder em Fevereiro"
for movie in upcoming:
    # Adicionar ao artigo
```

---

## 🎨 Widgets HTML

Os widgets gerados têm design responsivo e integram bem com WordPress:

### Widget de Filme:
```html
<div class="tmdb-movie-widget" style="border-left: 4px solid #F5A623; ...">
    <div style="display: flex; gap: 15px;">
        <img src="poster.jpg" alt="Filme" style="width: 100px;">
        <div>
            <h3>Titulo do Filme</h3>
            <p>⭐ 8.5/10 | 📅 2024-01-01</p>
            <p>Descrição do filme...</p>
        </div>
    </div>
</div>
```

### Widget de Série:
Semelhante, mas com informações de temporadas.

---

## 📊 Rate Limits

**TMDb é muito mais generoso que Gemini:**

| API | Limite | Comentário |
|-----|--------|-----------|
| **TMDb** | 40 req/10s | ✅ Muito generoso |
| **Gemini** | 15 req/min | ⚠️ Bem restritivo |

Você pode fazer muitas buscas na TMDb sem preocupação com rate limiting!

---

## 🔧 Exemplos Práticos

### Exemplo 1: Enriquecer um Artigo

```python
from app.tmdb_client import get_tmdb_client
from app.content_enricher import ContentEnricher

# Inicializar
enricher = ContentEnricher()

# Buscar um filme mencionado
movie = enricher.search_and_enrich_movie("Dune: Part Two")

if movie:
    # Gerar widget
    widget = enricher.generate_movie_widget_html(movie)
    
    # Adicionar ao conteúdo
    article_html += widget
```

### Exemplo 2: Criar Post sobre Tendências

```python
enricher = ContentEnricher()
trending = enricher.get_trending_movies(limit=5)

content = "<h2>Filmes em Tendência essa Semana</h2>"

for movie in trending:
    widget = enricher.generate_movie_widget_html(movie)
    content += widget

# Publicar no WordPress com este conteúdo
```

### Exemplo 3: Integração no Pipeline

No arquivo `app/pipeline.py`, após reescrever o conteúdo com IA:

```python
from app.content_enricher import enrich_article_with_tmdb
from app.config import TMDB_CONFIG

# ... código de reescrita com IA ...

# Se TMDb está habilitado
if TMDB_CONFIG['enabled']:
    try:
        article_content, media = enrich_article_with_tmdb(
            article_title=article['title'],
            article_content=article_content,
            max_enrichments=TMDB_CONFIG['max_enrichments_per_article']
        )
        logger.info(f"[TMDb] Enriquecido com {len(media)} mídia(s)")
    except Exception as e:
        logger.error(f"[TMDb] Erro no enriquecimento: {e}")
```

---

## 🐛 Troubleshooting

### Problema: "Nenhuma chave de API configurada"
**Solução**: Verifique se `TMDB_API_KEY` está no `.env` e se `TMDB_ENABLED=true`

### Problema: "Filme não encontrado"
**Solução**: O nome pode estar diferentes. A API busca por relevância. Tente variações.

### Problema: "Rate limit atingido"
**Solução**: Improvável com TMDb (limite é muito alto), mas se acontecer:
- Adicionar delay entre requisições
- Implementar fila/cache de buscas

### Problema: Imagens não aparecem
**Solução**: Verifique se `TMDB_API_KEY` é válido e se o tamanho de imagem existe

---

## 📖 Documentação Oficial

- **Getting Started**: https://developer.themoviedb.org/docs/getting-started
- **API Reference**: https://developer.themoviedb.org/reference
- **Rate Limiting**: https://developer.themoviedb.org/docs/rate-limiting
- **Image Guide**: https://developer.themoviedb.org/docs/image-basics

---

## ✅ Próximos Passos

1. **Obter API Key** no site da TMDb
2. **Adicionar ao .env**: `TMDB_ENABLED=true` e `TMDB_API_KEY=xxx`
3. **Instalar dependência**: `pip install tmdbv3api`
4. **Testar**: Rodas exemplos acima
5. **Integrar**: Adicionar ao pipeline principal

---

**Criado para Máquina Nerd | Fevereiro 2026**
