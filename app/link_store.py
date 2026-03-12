"""
link_store.py — Banco local de artigos publicados para links internos automáticos.
Mantém os últimos 200 artigos. O pipeline consulta antes de gerar cada artigo
para sugerir links contextuais ao Gemini.
"""
import sqlite3
import os
import logging

_DB = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")
logger = logging.getLogger(__name__)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS link_store (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        url         TEXT NOT NULL UNIQUE,
        category    TEXT DEFAULT '',
        entity      TEXT DEFAULT '',
        published   INTEGER DEFAULT (strftime('%s','now'))
    )""")
    c.commit()
    return c


def save_article(title: str, url: str, category: str = "", entity: str = "") -> None:
    """Salva artigo publicado. Mantém apenas os 200 mais recentes."""
    try:
        with _conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO link_store (title, url, category, entity) VALUES (?, ?, ?, ?)",
                (title, url, category or "", entity or ""),
            )
            # Manter apenas os 200 mais recentes
            c.execute("""DELETE FROM link_store WHERE id NOT IN (
                SELECT id FROM link_store ORDER BY published DESC LIMIT 200
            )""")
    except Exception as e:
        logger.warning(f"[LINKS] Erro ao salvar no link_store: {e}")


def get_related(entity: str = "", category: str = "", limit: int = 3) -> list:
    """
    Retorna artigos relacionados por entidade ou categoria.
    Prioriza mesma entidade; fallback para mesma categoria.
    """
    try:
        with _conn() as c:
            results = []
            if entity:
                rows = c.execute(
                    "SELECT title, url FROM link_store WHERE entity = ? ORDER BY published DESC LIMIT ?",
                    (entity, limit),
                ).fetchall()
                results = [{"title": r[0], "url": r[1]} for r in rows]

            if len(results) < limit and category:
                needed = limit - len(results)
                existing_urls = {r["url"] for r in results}
                rows = c.execute(
                    "SELECT title, url FROM link_store WHERE category = ? ORDER BY published DESC LIMIT ?",
                    (category, needed * 2),
                ).fetchall()
                for r in rows:
                    if r[1] not in existing_urls:
                        results.append({"title": r[0], "url": r[1]})
                    if len(results) >= limit:
                        break

            return results[:limit]
    except Exception as e:
        logger.warning(f"[LINKS] Erro ao consultar link_store: {e}")
        return []


def format_for_prompt(links: list) -> str:
    """
    Formata links como instrução legível para o prompt do Gemini.
    Retorna string vazia se não há links disponíveis.
    """
    if not links:
        return ""
    lines = ["LINKS INTERNOS DISPONÍVEIS — use 1 a 3 destes no corpo do artigo com texto âncora descritivo:"]
    for lk in links:
        lines.append(f'- URL: {lk["url"]} | Título: "{lk["title"]}"')
    lines.append(
        "REGRA DO TEXTO ÂNCORA: escolha palavras do TEMA do artigo de destino "
        "(ex: 'todos os filmes do Batman em ordem'). "
        "PROIBIDO: 'clique aqui', 'saiba mais', 'leia também', 'veja mais'."
    )
    return "\n".join(lines)
