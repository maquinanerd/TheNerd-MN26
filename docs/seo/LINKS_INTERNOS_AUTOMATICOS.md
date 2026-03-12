# 18/19 — Links Internos Automáticos

**Implementado em:** 12/03/2026  
**Arquivos criados:** `app/link_store.py`  
**Arquivos alterados:** `app/pipeline.py`, `app/ai_processor.py`, `universal_prompt.txt`

---

## 1. Por que isso foi necessário

Artigos sem links internos são tratados pelo Google como **páginas órfãs**: sem hierarquia, sem contexto temático, sem PageRank entrante. Isso é responsável diretamente pelo status "Crawled — currently not indexed" que afeta grande parte do portal.

O pipeline publicava artigos com zero links internos para outros artigos do site. A `assess_content_quality()` já penalizava isso (`links_int=0` → +0 pontos), mas sem a infra, não havia links para colocar.

---

## 2. Arquitetura da solução

```
[Título bruto do artigo]
        │
        ▼
score_event() PREVIEW      ← sem content_html, custo zero, só detecta entidade
        │
        ▼
get_related(entity, category)   ← consulta link_store (SQLite)
        │
        ▼
format_for_prompt(links)   ← gera instrução com URLs + regra de âncora
        │
        ▼
Gemini recebe link_block no prompt   ← insere 1–3 links contextuais no artigo
        │
        ▼
[Artigo publicado com links internos]
        │
        ▼
save_article()   ← salva no link_store para futuros artigos

```

---

## 3. Módulo `app/link_store.py`

### Tabela SQLite (`data/app.db`)

```sql
CREATE TABLE IF NOT EXISTS link_store (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    url       TEXT NOT NULL UNIQUE,
    category  TEXT DEFAULT '',
    entity    TEXT DEFAULT '',
    published INTEGER DEFAULT (strftime('%s','now'))
)
```

Mantém os **200 artigos mais recentes**. Entries mais antigas são deletadas automaticamente após cada `save_article()`.

### Funções

| Função | Parâmetros | Retorno |
|---|---|---|
| `save_article(title, url, category, entity)` | dados do artigo publicado | `None` |
| `get_related(entity, category, limit=3)` | entidade e categoria do artigo atual | `list[dict]` com `title` + `url` |
| `format_for_prompt(links)` | lista retornada por `get_related()` | `str` para injetar no prompt |

### Lógica de `get_related()`

1. Busca primeiro por **entidade** (`entity = ?`) — mesma franquia/personagem
2. Se retornar menos que `limit`, completa com artigos da mesma **categoria** como fallback
3. Evita duplicar URLs já encontradas na etapa 1

---

## 4. Integração em `pipeline.py`

### Ponto de atenção: preview antes do Gemini

O `score_event()` completo (com `content_html`) roda **após** a publicação para decidir se gera evergreen. Mas o `get_related()` precisa rodar **antes** do Gemini, quando `content_html` ainda não existe.

**Solução:** score preview do título bruto — passa `content=""` e `tags=[]`, que tem custo zero (só analisa o título para detectar a entidade):

```python
# PONTO 1 — ANTES do Gemini (dentro do loop batch_data)
from .cluster_engine import score_event as _score_event_pre
_pre_event = _score_event_pre({
    "title": extracted.get('title', ''),
    "content": "",   # ← vazio, custo zero
    "tags": [],
})
_related = ls_get_related(
    entity=_pre_event.get("entity", ""),
    category=art['category'],
    limit=3,
)
_link_block = ls_format_links(_related)

batch_data.append({
    ...
    'link_block': _link_block,   # ← passado para o AIProcessor
})
```

> O score completo com `content_html` ainda roda normalmente após a publicação (no bloco `[CLUSTER]`). O preview é descartado — serve apenas para detectar a entidade antes de gerar o conteúdo.

### Ponto 2 — APÓS publicação bem-sucedida

Dentro do bloco `if sanitized_ok:`, após o `[CLUSTER]` block:

```python
ls_save_article(
    title=title,
    url=f"https://www.maquinanerd.com.br/{rewritten_data.get('slug', 'sem-slug')}/",
    category=art_data['category'],
    entity=event.get("entity", ""),
)
```

O `event` aqui é o score completo (já calculado no bloco anterior), então a entidade detectada com `content_html` é usada para salvar.

---

## 5. Integração em `ai_processor.py`

O campo `link_block` é adicionado ao dict `fields` que alimenta `_safe_format_prompt()`:

```python
fields = {
    ...
    "link_block": data.get("link_block", ""),
}
```

`_safe_format_prompt()` já lida com campos ausentes via `_SafeDict` — se `link_block` for vazio, o placeholder `{link_block}` é substituído por string vazia, sem efeito no prompt.

---

## 6. Instrução no `universal_prompt.txt`

### Regra adicionada ao bloco `conteudo_final`

```
- Se houver links na seção "LINKS INTERNOS DISPONÍVEIS", USE 1 a 3 deles
  inserindo-os contextualmente no corpo do artigo. O texto âncora DEVE descrever o conteúdo
  de destino com as palavras-chave do tema. NUNCA use "clique aqui", "saiba mais" ou "leia também"
  como texto âncora. Links externos (fontes): adicione rel="nofollow". Links internos: nunca nofollow.
```

### Placeholder no final

```
{link_block}
```

Aparece ao final do bloco de dados, depois de `{content}`. Quando há artigos relacionados no banco, o Gemini recebe algo como:

```
LINKS INTERNOS DISPONÍVEIS — use 1 a 3 destes no corpo do artigo com texto âncora descritivo:
- URL: https://www.maquinanerd.com.br/batman-cavaleiro-das-trevas-4/ | Título: "Batman 4 tem estreia confirmada pela DC"
- URL: https://www.maquinanerd.com.br/batman-dc-studios-2025/ | Título: "DC Studios revela planos para Batman no DCU"
REGRA DO TEXTO ÂNCORA: escolha palavras do TEMA do artigo de destino. PROIBIDO: 'clique aqui', 'saiba mais', 'leia também'.
```

---

## 7. Impacto no quality score

A `assess_content_quality()` já atribuía pontos por links internos:

| `links_int` no artigo | Pontos adicionados |
|---|---|
| 0 | +0 |
| 1 | +10 |
| 2+ | +20 |

Com links internos automáticos, artigos que antes ficavam em NOINDEX por `links_int=0` ganham +10 a +20 pontos — podendo cruzar o threshold de INDEX **sem nenhuma outra mudança no conteúdo**.

---

## 8. Comportamento inicial (cold start)

Nas primeiras publicações após o deploy, o `link_store` está vazio — `get_related()` retorna lista vazia, `format_for_prompt()` retorna string vazia, `{link_block}` some do prompt sem impacto. O banco começa a ser preenchido a cada artigo publicado com sucesso via `save_article()`.

**Estimativa:** após ~10 artigos publicados, os primeiros links contextuais já começam a aparecer no conteúdo.

---

## 9. Verificação após restart

```powershell
# Confirmar que link_store está sendo preenchido
py -c "
import sqlite3
c = sqlite3.connect('data/app.db')
rows = c.execute('SELECT id, substr(title,1,50), entity, category FROM link_store ORDER BY published DESC LIMIT 10').fetchall()
for r in rows: print(r)
"

# Confirmar nos logs que os links foram salvos
Get-Content logs\app.log | Where-Object { $_ -match "\[LINKS\]" }
```

Log esperado após publicação:
```
[LINKS] Salvo no link_store: Batman 4 tem estreia confirmada pela DC
```
