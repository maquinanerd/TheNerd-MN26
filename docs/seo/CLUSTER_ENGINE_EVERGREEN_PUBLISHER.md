# 15 e 16 — Cluster Engine + Evergreen Publisher

**Implementado em:** 12/03/2026  
**Arquivos criados:** `app/cluster_engine.py`, `app/evergreen_publisher.py`  
**Arquivo editado:** `app/pipeline.py` (3 pontos)  
**Custo adicional:** zero — análise local no item 15; mesmo AIClient/WordPressClient no item 16

---

## Item 15 — cluster_engine.py: Event Scoring Automático

### O que faz

Após cada publicação bem-sucedida, avalia a notícia com base em entidades, tags e profundidade narrativa. Decide se a notícia merece gerar um cluster de páginas evergreen.

**Zero custo de API** — análise puramente local em texto.

### Arquivo

`app/cluster_engine.py`

### Três estruturas de dados

| Nome | Tipo | Conteúdo |
|---|---|---|
| `HIGH_VALUE_ENTITIES` | `set` | Franquias/IPs de alto potencial (Marvel, DC, Star Wars, animes, games AAA...) |
| `EVERGREEN_TEMPLATES` | `dict` | 6 templates disponíveis com descrição |
| `HIGH_DEMAND_TAGS` | `set` | Tags que indicam alta demanda (trailer, estreia, temporada, remake...) |

### Função `score_event(article_data)`

**Input:** `dict` com `title`, `content` (HTML), `tags` (list), `source_count` (opcional)

**Critérios de pontuação:**

| Critério | Pontos | Verificação |
|---|---|---|
| Entidade em HIGH_VALUE_ENTITIES | +30 | `ent in (title + content[:500]).lower()` |
| Tag em HIGH_DEMAND_TAGS | +25 | `tags_lower & HIGH_DEMAND_TAGS` |
| Entidade encontrada → templates disponíveis | +20 | `entity is not None` |
| Palavras de profundidade narrativa no texto | +15 | saga, universo, temporada, trilogia... |
| Cobertura multi-fonte | +10 | `source_count > 1` |
| **Máximo teórico** | **100** | |

**Threshold:** `score >= 60 AND entity not None` → `should_cluster = True`

**Output:**
```python
{
  "score": 75,
  "should_cluster": True,
  "entity": "batman",
  "templates": ["timeline", "cast_guide", "villains", "ending_explained", "easter_eggs", "powers"],
  "reason": "entidade=batman | tag_demanda_alta | 6_templates | franchise_depth"
}
```

### Integração em pipeline.py

Localização: dentro de `if sanitized_ok:`, após `log_tokens()`.

```python
from .cluster_engine import score_event
from .evergreen_publisher import schedule_cluster_pages

event = score_event({
    "title":   title,
    "content": content_html,
    "tags":    rewritten_data.get("tags_sugeridas", []),
})
if event["should_cluster"]:
    logger.info(f"[CLUSTER] Score {event['score']} | entity={event['entity']} | ...")
    schedule_cluster_pages(
        entity=event["entity"],
        source_post_id=wp_post_id,
        source_title=title,
        templates=event["templates"],
        category_ids=list(final_category_ids),
    )
```

### Log esperado

```
[SCORE] Batman: Novo Filme Confirmado pela DC | score=75 entity=batman cluster=True
[CLUSTER] Score 75 | entity=batman | templates=['timeline', 'cast_guide', 'villains'] | post_id=75612
[QUEUE] batman/timeline → T+1h (post 75612)
[QUEUE] batman/cast_guide → T+6h (post 75612)
[QUEUE] batman/villains → T+24h (post 75612)
```

---

## Item 16 — evergreen_publisher.py: Gerador + Fila de Publicação

### O que faz

Gerencia a geração e publicação gradual das páginas evergreen. Usa uma tabela SQLite no banco local (`data/app.db`) como fila de agendamento. Sem dependências externas além do que o projeto já usa.

### Arquivo

`app/evergreen_publisher.py`

### Tabela SQLite: `evergreen_queue`

Criada automaticamente na primeira execução em `data/app.db`:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | Auto-incremento |
| `entity` | TEXT | Nome da entidade (ex: "batman") |
| `template_key` | TEXT | Chave do template (ex: "timeline") |
| `prompt` | TEXT | Prompt completo para o Gemini |
| `title` | TEXT | Título calculado do post evergreen |
| `category_ids` | TEXT | JSON com IDs de categoria da notícia-gatilho |
| `source_post_id` | INTEGER | ID WordPress da notícia que gerou o cluster |
| `scheduled_for` | INTEGER | Unix timestamp — quando publicar |
| `status` | TEXT | `pending` → `done` ou `error` |
| `wp_post_id` | INTEGER | ID WordPress do post evergreen publicado |

### Templates disponíveis

| Chave | Título gerado | Tamanho alvo |
|---|---|---|
| `timeline` | `{Entity}: Timeline Completa e Ordem Cronológica` | 900-1200 palavras |
| `cast_guide` | `{Entity}: Elenco Completo e Guia de Personagens` | 900-1200 palavras |
| `villains` | `{Entity}: Todos os Vilões Explicados e Ranqueados` | 900-1200 palavras |
| `ending_explained` | `{Entity}: Final Explicado em Detalhes` | 900-1200 palavras |
| `easter_eggs` | `{Entity}: Todos os Easter Eggs e Referências Escondidas` | 900-1200 palavras |

Cada prompt já inclui as regras do portal:
- Estrutura `O que você precisa saber` como primeiro H2
- `Nossa Análise` como último H2
- H3 obrigatório em cada H2
- Retorna apenas HTML sem tags de documento

### Scheduling gradual

| Posição na fila | Delay | Template padrão |
|---|---|---|
| 1º a publicar | T+1h | timeline |
| 2º a publicar | T+6h | cast_guide |
| 3º a publicar | T+24h | villains |

Publicação gradual evita spike de conteúdo similar que pode disparar alertas de duplicidade no Google Search Console.

### Função `schedule_cluster_pages(...)`

Insere até 3 entradas na fila. Seleciona apenas templates presentes em `EVERGREEN_PROMPTS` (ignora templates sem prompt definido).

### Função `process_evergreen_queue(max_per_cycle=2)`

- Lê entradas com `status='pending'` e `scheduled_for <= now()`
- Por entrada: chama `ai_proc._ai_client.generate_text(prompt)` → retorna `(html, tokens_info)`
- Valida que o conteúdo tem mais de 200 chars antes de publicar
- Publica via `wp_client.create_post(payload)` com `noindex="0"` e `nofollow="0"`
- Atualiza status para `done` (com `wp_post_id`) ou `error`
- Retorna contagem de publicados

**Não aceita parâmetros de cliente** — cria internamente suas instâncias `AIProcessor` e `WordPressClient` (que são singletons/stateless no contexto das configurações).

### Integração em pipeline.py — 2 pontos

**Ponto 1 — início de `run_pipeline_cycle()`:**
```python
def run_pipeline_cycle():
    from .evergreen_publisher import process_evergreen_queue
    ev_count = process_evergreen_queue(max_per_cycle=2)
    if ev_count:
        logger.info(f"[CYCLE] {ev_count} evergreen(s) publicado(s) neste ciclo")
    db = Database()
    ...
```

**Ponto 2 — dentro de `if event["should_cluster"]:` (após item 15):**
```python
schedule_cluster_pages(
    entity=event["entity"],
    source_post_id=wp_post_id,
    source_title=title,
    templates=event["templates"],
    category_ids=list(final_category_ids),
)
```

### Log esperado (publicação ~1h depois da notícia)

```
[EVERGREEN] Gerando batman/timeline...
[EVERGREEN] ✓ Batman: Timeline Completa e Ordem Cronológica → WP ID 75615
[CYCLE] 1 evergreen(s) publicado(s) neste ciclo
```

---

## Fluxo completo: notícia → cluster

```
Notícia publicada (post_id=75612)
    ↓
score_event() → score=75, entity=batman, should_cluster=True
    ↓
schedule_cluster_pages() → 3 entradas na evergreen_queue
    ↓
    T+1h:  status=pending → process_evergreen_queue() → Batman: Timeline → WP ID 75615
    T+6h:  status=pending → process_evergreen_queue() → Batman: Elenco  → WP ID 75618
    T+24h: status=pending → process_evergreen_queue() → Batman: Vilões  → WP ID 75621
```

---

## Verificação

```powershell
# Ver logs de scoring
Get-Content logs\app.log | Where-Object { $_ -match "\[SCORE\]|\[CLUSTER\]|\[QUEUE\]|\[EVERGREEN\]" }

# Inspecionar fila SQLite
python -c "
import sqlite3
conn = sqlite3.connect('data/app.db')
for r in conn.execute('SELECT id,entity,template_key,status,wp_post_id,scheduled_for FROM evergreen_queue ORDER BY id DESC LIMIT 20'):
    print(r)
"
```

---

## Personalização futura

- **Adicionar templates:** criar nova entrada em `EVERGREEN_PROMPTS` e `TITLES` em `evergreen_publisher.py`
- **Alterar threshold de score:** mudar `score >= 60` em `cluster_engine.py` linha 88
- **Alterar delays:** editar `DELAYS_H = [1, 6, 24]` em `evergreen_publisher.py`
- **Throttle de publicação:** ajustar `max_per_cycle=2` na chamada em `run_pipeline_cycle()`
- **Novas entidades:** adicionar ao conjunto `HIGH_VALUE_ENTITIES` em `cluster_engine.py`
