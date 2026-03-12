# 🎯 GOOGLE NEWS SEO - GUIA COMPLETO DE CONFIGURAÇÃO

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### ✅ PARTE 1: NEWS SITEMAP XML (JÁ FEITO)
- [x] news-sitemap.xml criado pelo Yoast SEO
- [x] Listado no sitemap_index.xml ✓
- [x] URLs com news:publication, news:publication_date, news:title

### 🔧 PARTE 2: ADICIONAR NEWS:KEYWORDS AO SITEMAP (AGORA)

**Arquivo:** `WPCODE_NEWS_SITEMAP_ENHANCEMENT.php`

#### Passo a Passo de Instalação:

1. **Acessar WordPress Dashboard**
   ```
   https://www.maquinanerd.com.br/wp-admin
   ```

2. **Instalar Plugin WPCode** (se não tiver)
   - Plugins → Add New
   - Buscar: "WPCode"
   - Instalar e ativar

3. **Adicionar Snippet**
   - WPCode → Code Snippets
   - Clique em "+ Add Snippet"
   - Escolha: "Create Your Own"

4. **Configurar Snippet**
   - Title: `Google News Sitemap Enhancement`
   - Description: `Adiciona news:keywords, news:access, news:image`
   - Language: **PHP**
   - Colar TODO o código de `WPCODE_NEWS_SITEMAP_ENHANCEMENT.php`

5. **Inserir Código**
   ```
   Copiar linhas 8-97 do arquivo
   (Do add_filter até o último comment)
   ```

6. **Settings do Snippet**
   - **Insertion Method:** Auto Insert
   - **Location:** Everywhere

7. **Salvar e Ativar**
   - Save & Activate
   - Você deve ver: "✓ Code snippet activated"

8. **Verificar News-Sitemap.xml**
   ```
   https://www.maquinanerd.com.br/news-sitemap.xml
   ```
   
   Deve conter NOVAS linhas como:
   ```xml
   <news:keywords>Netflix, Série, Ficção Científica, ...</news:keywords>
   <news:access>Free</news:access>
   <news:image>
       <news:url>https://...wordpress.../image.jpg</news:url>
       <news:title>Nome da imagem</news:title>
   </news:image>
   ```

---

## 🗂️ PARTE 3: VALIDAR NEWS-SITEMAP.XML

### Online Tools:

1. **Google News Sitemap Validator**
   ```
   https://tool.toolip.io/find/xml-sitemap-validator
   ```
   - Colar URL: `https://www.maquinanerd.com.br/news-sitemap.xml`
   - Validar

2. **Google Rich Results Test**
   ```
   https://search.google.com/test/rich-results
   ```
   - Copiar URL de um post: `https://www.maquinanerd.com.br/spider-noir-cat-hardy-interesse-amoroso/`
   - Verificar structured data

3. **XML Validator**
   ```
   https://www.xmlvalidation.com/
   ```
   - Validar syntax do XML

---

## 📱 PARTE 4: GOOGLE NEWS PUBLISHER CENTER

### Configuração Manual:

#### 4.1 Acessar Google News Publisher Center
```
https://newscenter.google.com/
```

1. **Login com Gmail/Google Account**
2. **Adicionar Publicação**
   - Clique em "+" 
   - Nome: `Máquina Nerd`
   - URL: `https://www.maquinanerd.com.br`
   - Categoria: Entertainment/Movies/TV
   - Idioma: Portuguese

#### 4.2 Verificar Propriedade (Choose 1)

**Opção A: DNS (Recomendado)**
1. Copiar TXT record fornecido
2. Acessar seu servidor DNS (GoDaddy, Cloudflare, etc.)
3. Adicionar TXT record: `google-site-verification=XXXXX...`
4. Esperar 24h-48h para verificação

**Opção B: HTML Tag**
1. Copiar meta tag
2. Adicionar a `<head>` do seu WordPress:
   - Ir ao WPCode → Add Snippet
   - Adicionar em <head>
   - Header Insertion

**Opção C: Google Search Console (Melhor)**
1. Já ter Property registrada em GSC
2. Clicar "Verify with Search Console"
3. Automático se GSC estiver verificado

#### 4.3 Configurar News-Sitemap
1. Em News Publisher Center:
   - Seção: "Sitemaps"
   - URL: `https://www.maquinanerd.com.br/news-sitemap.xml`
   - "Submit"

#### 4.4 Configurações Recomendadas
```
✅ Automatic updates: ON
✅ Allow Google to syndicate: OFF (para manter exclusividade)
✅ Language: Portuguese (pt-BR)
✅ Categories: Entertainment, Movies, TV Shows
✅ Geo-targeting: Brazil
```

#### 4.5 Analytics
- Esperar 48-72h para dados aparecerem
- Google News Publisher Center tem próprio analytics
- Revisar: Impressions, Clicks, Average Position

---

## 📊 PARTE 5: GOOGLE SEARCH CONSOLE SETUP

### 5.1 Adicionar Property (se não tiver)
```
https://search.google.com/search-console/
```

1. **Nova Property**
   - URL: `https://www.maquinanerd.com.br`
   - Tipo: Domain ou URL prefix
   - Verificar propriedade (DNS é melhor)

2. **Submeter Sitemap**
   - Left menu → Sitemaps
   - URL: `https://www.maquinanerd.com.br/sitemap_index.xml`
   - Submit

3. **Submeter News Sitemap**
   - Left menu → Sitemaps
   - URL: `https://www.maquinanerd.com.br/news-sitemap.xml`
   - Submit (especificamente para news)

### 5.2 Monitorar Performance
```
Left Menu → Performance
```

Filtros importantes para NOTÍCIAS:
```
✅ Query contains: "netflix", "série", "filme" (sem aspas)
✅ Search Type: News (importante!)
✅ Country: Brazil
✅ Date Range: Last 28 days (ou mais)
```

Métricas a acompanhar:
```
📈 Total Clicks: Número de cliques em resultados de notícias
📊 Impressions: Quantas vezes apareceu em Google News
📍 Average Position: Ranking médio (alvo: <3)
🏆 Click Through Rate (CTR): Taxa de cliques (alvo: >5%)
```

### 5.3 Cobertura / Indexação
```
Left Menu → Coverage
```

Checklist:
- [ ] 0 erros (Error = 0)
- [ ] Índice com sucesso: Maioria dos posts
- [ ] Excluídos: Mínimo ou zero
- [ ] Válido com avisos: Explicar avisos

### 5.4 Enhancements (Structured Data)
```
Left Menu → Enhancements
```

Validar:
- [ ] NewsArticle schema: ✓ Válido
- [ ] Article schema: ✓ Válido
- [ ] Image: Todas com imagens
- [ ] Breadcrumb: ✓ Correto

---

## 🚀 PARTE 6: OTIMIZAÇÕES AVANÇADAS

### 6.1 News Keywords Strategy
Para cada article publicado via pipeline, adicionar:

```python
# Em pipeline.py, adicionar ao AI processor:

keywords_strategy = {
    'focus_keyword': rewritten_data.get('focus_keyword'),
    'long_tail_keywords': [
        f"{focus_kw} netflix",
        f"{focus_kw} 2026",
        f"{focus_kw} review",
        f"{focus_kw} série",
    ],
    'seasonal_keywords': [
        "lançamentos 2026",
        "séries imprescindíveis",
    ]
}
```

### 6.2 Publication Date & Freshness
Google News prioriza:
- Publicações no últimas 30 dias
- atualizado recentemente (dateModified)
- Content fresco e relevante

**Garantir:**
```json
{
    "datePublished": "2026-02-12T20:02:46+00:00",
    "dateModified": "2026-02-12T20:02:50+00:00",
    "article:section": "Entertainment",
    "article:tag": ["Netflix", "Série", "Notícia"]
}
```

### 6.3 Imagens em Google News
Google News agora mostra imagens em resultados!

Otimizar:
- ✅ Featured image: Mínimo 1200x630
- ✅ Alt text: Descritivo e com keyword
- ✅ Image title: Relevante
- ✅ No watermarks: Evitar logos muito grandes

---

## 📈 PARTE 7: MONITORAMENTO & PERFORMANCE

### Métricas-Chave a Acompanhar

**Semanal:**
```
1. Visualizações em Google News
2. CTR (Click Through Rate)
3. Posição média em notícias
4. Novos artigos indexados
```

**Mensal:**
```
1. Crescimento de impressões
2. Trending keywords
3. Erros no GSC
4. Cobertura do news-sitemap
```

**Trimestral:**
```
1. SEO ranking geral
2. Referral traffic de Google News
3. Comparar com concorrentes
4. Ajustar estratégia de keywords
```

### Dashboard Recomendado
```
Google Data Studio (gratuito):
→ Conectar Google Search Console
→ Criar dashboard com:
  - Impressões vs Clicks (último 90 dias)
  - Top queries (news)
  - Top pages (news)
  - Posição média por página
  - CTR comparativo
```

---

## ✅ CHECKLIST FINAL

### Antes de Publicar
- [ ] WPCode snippet instalado e ativo
- [ ] News-sitemap.xml contém news:keywords
- [ ] Todas as imagens featured têm mínimo 1200x630
- [ ] Títulos otimizados (50-65 chars)
- [ ] Meta description (120-160 chars)
- [ ] Tags/categorias relevantes preenchidas

### Depois de Publicar
- [ ] Post aparece no news-sitemap.xml (dentro de 24h)
- [ ] GSC não mostra erros
- [ ] Rich Results Test valida NewsArticle schema
- [ ] Google News Publisher Center reconhece artigo (48-72h)

### Monitoramento Contínuo
- [ ] Revisar GSC semanalmente
- [ ] Acompanhar ranking em Google News
- [ ] Analisar clicks vs impressões
- [ ] Atualizar estratégia com trending topics

---

## 📞 SUPORTE & REFERÊNCIAS

### Documentação Oficial
```
1. Google News Sitemap Spec:
   https://developers.google.com/search/docs/crawling-indexing/news-sitemap

2. Google News Publisher Center:
   https://support.google.com/news/publisher-center

3. Yoast SEO News Sitemap:
   https://yoast.com/help/how-to-configure-yoast-seo-news-sitemaps/

4. Google Rich Results Test:
   https://search.google.com/test/rich-results

5. Google Search Console Help:
   https://support.google.com/webmasters/
```

### Scripts Python Úteis
```python
# Validar news-sitemap.xml
import requests
import xml.etree.ElementTree as ET

def validate_news_sitemap(url):
    response = requests.get(url)
    root = ET.fromstring(response.content)
    
    # Contar keywords
    keywords_count = len(root.findall('.//news:keywords'))
    print(f"URLs com keywords: {keywords_count}")
    
    # Validar estrutura
    for url_elem in root.findall('.//url'):
        if not url_elem.find('./news:keywords') is not None:
            print(f"⚠️  Falta keyword: {url_elem.find('loc').text}")
```

---

## 🎯 RESULTADOS ESPERADOS

**Timeframe: 48-72 horas**
- Posts aparecem em Google News
- Aumenta impressões orgânicas

**Timeframe: 2-4 semanas**
- Ranking melhora em news searches
- CTR aumenta com imagens
- Mais referral traffic via Google News

**Timeframe: 1-3 meses**
- Máquina Nerd pode virar "news source" oficial
- Maior autoridade em notícias de séries/filmes
- Potencial para featured snippets

---

**Data de Implementação:** 2026-02-12
**Última Atualização:** 2026-02-12
**Status:** ✅ COMPLETO E PRONTO PARA IMPLEMENTAÇÃO
