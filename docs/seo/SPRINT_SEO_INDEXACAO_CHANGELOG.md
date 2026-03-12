# CHANGELOG — Sprint SEO Indexação

**Data:** 12/03/2026  
**Base:** commit `529feb7`  
**Objetivo:** Reduzir páginas "Crawled — currently not indexed" e construir infraestrutura de clusters evergreen.

---

## Itens implementados

| Item | Descrição | Arquivos |
|---|---|---|
| 12 | Quality Score estrutural + noindex automático | `pipeline.py`, `wordpress.py` |
| 13 | Prompt upgrade: estrutura de headings obrigatória | `universal_prompt.txt` |
| 15 | Cluster Engine: event scoring automático | `app/cluster_engine.py` (NEW) |
| 16 | Evergreen Publisher: fila SQLite + geração + publicação | `app/evergreen_publisher.py` (NEW) |
| 17 | QA Semântico Camada 2 via Gemini 2.5 Flash | `app/pipeline.py` |
| 18/19 | Links Internos Automáticos via link_store | `app/link_store.py` (NEW), `app/pipeline.py`, `app/ai_processor.py`, `universal_prompt.txt` |

---

## Detalhes por item

### Item 12 — Quality Score + Noindex Automático

**Arquivo:** `app/pipeline.py` — função `assess_content_quality(content_html)`  
**Arquivo:** `app/wordpress.py` — campo `_yoast_wpseo_meta-robots-noindex`

#### O que faz

Avalia estrutura do artigo gerado **antes de publicar** e decide se deve ser indexado:

| Critério | Pontos |
|---|---|
| ≥ 700 palavras | +30 |
| ≥ 1 tag `<h3>` | +20 |
| Seção "Nossa Análise" presente | +15 |
| ≥ 2 links internos (`maquinanerd.com.br`) | +20 |
| Sem CTA residual detectado | +15 |

- Score ≥ 50 → `noindex=0` (INDEX)
- Score < 50 → `noindex=1` (NOINDEX)
- Borderline 35–49 → passa para Camada 2 (item 17)

#### Log gerado
```
[QA] Batman 4 tem estreia confirmada... | score=70 | 812w | h3=sim | links_int=2 → INDEX
```

---

### Item 13 — Prompt Upgrade: Estrutura de Headings

**Arquivo:** `universal_prompt.txt`

#### O que mudou

1. **Bloco novo** entre as regras SEO e o JSON template:
   - Mínimo 700 palavras (notícia) / 1.000 (análise)
   - Máximo 6 `<h2>`, cada um com pelo menos um `<h3>` filho
   - Primeiro H2 fixo: "O que você precisa saber" com `<ul>` de 3 pontos
   - Último H2 fixo: "Nossa Análise" com perspectiva editorial

2. **CHECKLIST FINAL** atualizado — 4 itens específicos substituem o genérico "Mínimo 3 subtítulos H2":
   - `□ Primeiro H2 é "O que você precisa saber"?`
   - `□ Último H2 é "Nossa Análise"?`
   - `□ Cada H2 tem pelo menos um H3 filho?`
   - `□ Máximo 6 tags <h2>?`

---

### Item 15 — Cluster Engine

**Arquivo:** `app/cluster_engine.py` (NOVO)

#### O que faz

Analisa cada artigo publicado e atribui um score de 0–100. Se score ≥ 60 **e** entidade detectada → `should_cluster=True` → aciona o `evergreen_publisher`.

#### Critérios de scoring

| Critério | Pontos |
|---|---|
| Entidade high-value detectada no título/conteúdo | +30 |
| Tags de alta demanda (trailer, confirmado, estreia...) | +25 |
| Templates evergreen aplicáveis ao tema | +20 |
| Keywords de profundidade (origem, história, poderes...) | +15 |
| Múltiplas fontes / cobertura ampla | +10 |

#### Constantes principais
- `HIGH_VALUE_ENTITIES`: ~60 franquias/personagens PT-BR + EN
- `EVERGREEN_TEMPLATES`: timeline, cast_guide, villains, ending_explained, easter_eggs, powers
- `HIGH_DEMAND_TAGS`: trailer, confirmado, estreia, temporada, sequel...

#### Log gerado
```
[SCORE] Batman 4 tem estreia confirmada... | score=65 entity=batman cluster=True
[CLUSTER] Score 65 | entity=batman | templates=['timeline', 'cast_guide', 'villains'] | post_id=12345
```

---

### Item 16 — Evergreen Publisher

**Arquivo:** `app/evergreen_publisher.py` (NOVO)  
**Tabela SQLite:** `evergreen_queue` em `data/app.db`

#### O que faz

1. `schedule_cluster_pages()`: recebe o resultado do `score_event()` e insere até 3 entradas na fila `evergreen_queue` com timestamps escalonados (T+1h, T+6h, T+24h)
2. `process_evergreen_queue()`: roda no início de cada ciclo do pipeline; consome entradas com `scheduled_for ≤ now`, gera conteúdo via Gemini e publica no WordPress

#### Schema da fila

```sql
CREATE TABLE evergreen_queue (
    id           INTEGER PRIMARY KEY,
    entity       TEXT,
    template     TEXT,
    source_post_id INTEGER,
    source_title TEXT,
    category_ids TEXT,
    scheduled_for INTEGER,
    status       TEXT DEFAULT 'pending',
    wp_post_id   INTEGER,
    created_at   INTEGER
)
```

#### Delays de publicação
| Posição | Template | Delay |
|---|---|---|
| 1 | timeline | T + 1h |
| 2 | cast_guide | T + 6h |
| 3 | villains / ending_explained / ... | T + 24h |

#### Integração em `pipeline.py`
- `schedule_cluster_pages()` chamado dentro do bloco `[CLUSTER]` após publicação
- `process_evergreen_queue(max_per_cycle=2)` chamado no início de `run_pipeline_cycle()`

---

### Item 17 — QA Semântico Camada 2

**Arquivo:** `app/pipeline.py` — função `semantic_qa_flash(title, content_html)`

#### O que faz

Segunda camada de QA, executada **apenas** para artigos com score entre 35–49 (borderline da Camada 1). Usa `gemini-2.5-flash` diretamente com `AI_API_KEYS[0]`.

#### Output da função
```python
{
    "has_original_value": True,
    "has_cta_residual": False,
    "content_type": "evergreen",  # "news" | "analysis" | "evergreen"
    "quality_note": "análise aprofundada sobre Frank Castle no MCU"
}
```

#### Lógica de decisão
| Score C1 | Condição C2 | Resultado final |
|---|---|---|
| ≥ 50 | não roda | INDEX |
| 35–49 | evergreen + original | **INDEX** (forçado) |
| 35–49 | sem valor original | NOINDEX (confirmado) |
| < 35 | não roda | NOINDEX |

#### Nota de operação (429)
Por não passar pelo `RateLimiter`/`KeyPool`, pode retornar erro 429 se o pipeline estiver no limite de RPM. O `try/except` interno aciona o fallback seguro — artigo não é bloqueado.

#### Log gerado
```
[QA-LLM] type=evergreen | original=True | cta=False | análise sobre o personagem
[QA-LLM] Forçando INDEX por tipo evergreen: Punisher tem futuro no MCU...
```

---

### Item 18/19 — Links Internos Automáticos

**Arquivo:** `app/link_store.py` (NOVO)  
**Arquivo:** `app/pipeline.py` — 3 pontos modificados  
**Arquivo:** `app/ai_processor.py` — campo `link_block` adicionado ao `fields`  
**Arquivo:** `universal_prompt.txt` — regra de âncora + placeholder `{link_block}`

#### O que faz

Mantém um banco SQLite dos últimos 200 artigos publicados. Antes de cada chamada ao Gemini, consulta artigos relacionados por entidade/categoria e injeta os URLs no prompt como instrução de texto âncora descritivo.

#### Fluxo
```
título bruto → score_event() PREVIEW (content="") → entity detectada
→ get_related(entity, category) → format_for_prompt()
→ {link_block} no prompt do Gemini
→ Gemini insere 1–3 links contextuais com âncora descritiva
→ artigo publicado → save_article() → link_store atualizado
```

#### Ponto de atenção: duas execuções do score_event
- **Preview** (antes do Gemini): `content=""`, `tags=[]` → só detecta entidade, custo zero
- **Completo** (após publicação): `content=content_html` → score real para decisão de cluster

#### Impacto no quality score
`links_int=0` → `links_int=2` = **+20 pontos** no `assess_content_quality()` — pode cruzar threshold de INDEX sem nenhuma outra mudança no conteúdo.

#### Cold start
Primeiras ~10 publicações: `link_store` vazio, `{link_block}` silencioso. A partir do 11º artigo, links contextuais começam a aparecer.

---

## Arquivos de documentação criados

| Arquivo | Cobre |
|---|---|
| `docs/seo/CRAWL_BUDGET_NOINDEX_QUALITY_SCORE.md` | Itens 12 + teoria |
| `docs/seo/PROMPT_UPGRADE_ESTRUTURA_CONTEUDO.md` | Item 13 |
| `docs/seo/CLUSTER_ENGINE_EVERGREEN_PUBLISHER.md` | Itens 15 + 16 |
| `docs/seo/QA_SEMANTICO_GEMINI_FLASH.md` | Item 17 |
| `docs/seo/LINKS_INTERNOS_AUTOMATICOS.md` | Itens 18 + 19 |

---

## Verificação rápida pós-deploy

```powershell
# 1. QA Camada 1
Get-Content logs\app.log | Where-Object { $_ -match "\[QA\]" } | Select-Object -Last 10

# 2. QA Camada 2 (semântico)
Get-Content logs\app.log | Where-Object { $_ -match "\[QA-LLM\]" }

# 3. Cluster + Evergreen
Get-Content logs\app.log | Where-Object { $_ -match "\[CLUSTER\]|\[QUEUE\]|\[EVERGREEN\]|\[CYCLE\]" }

# 4. Link store preenchendo
Get-Content logs\app.log | Where-Object { $_ -match "\[LINKS\]" }

# 5. Fila evergreen (SQLite)
py -c "import sqlite3; c=sqlite3.connect('data/app.db'); [print(r) for r in c.execute('SELECT id,entity,template,status,scheduled_for FROM evergreen_queue ORDER BY id DESC LIMIT 10').fetchall()]"

# 6. Link store (SQLite)
py -c "import sqlite3; c=sqlite3.connect('data/app.db'); [print(r) for r in c.execute('SELECT id,substr(title,1,50),entity,category FROM link_store ORDER BY published DESC LIMIT 10').fetchall()]"
```
