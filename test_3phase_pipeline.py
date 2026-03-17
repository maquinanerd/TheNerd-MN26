#!/usr/bin/env python3
"""
test_3phase_pipeline.py
-----------------------
Teste isolado do pipeline de IA em 3 fases (ai_sanitize → ai_rewrite → ai_seo_pack).

Uso:
    python test_3phase_pipeline.py [URL]

Se URL não for informada, busca o artigo mais recente do feed ScreenRant.
"""
import sys
import os
import json
import logging
import time
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("3phase_test")

# ── Raiz do projeto no path ───────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Importações do projeto ────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.config import AI_API_KEYS, RSS_FEEDS
from app.ai_client_gemini import AIClient
from app.extractor import ContentExtractor
from app.feeds import FeedReader
from app.ai_sanitize import sanitize
from app.ai_rewrite import rewrite
from app.ai_seo_pack import seo_pack


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_url() -> tuple[str, str]:
    """Return (url, title) — from argv or from ScreenRant RSS."""
    if len(sys.argv) > 1:
        return sys.argv[1], "Artigo via CLI"

    logger.info("Buscando artigo recente no ScreenRant RSS...")
    feed_config = RSS_FEEDS.get("screenrant_movie_news") or RSS_FEEDS.get("screenrant_tv")
    reader = FeedReader(user_agent="MaquinaNerd-Test/1.0")
    items = reader.read_feeds(feed_config, "screenrant_movie_news")
    if not items:
        raise RuntimeError("Nenhum item no RSS — verifique conexão ou feed.")
    article = items[0]
    url = article.get("link") or article.get("url") or article.get("id")
    title = article.get("title", "Sem título")
    logger.info(f"Artigo escolhido: {title[:80]}")
    logger.info(f"URL: {url}")
    return url, title


def _char_count_html(html: str) -> int:
    from bs4 import BeautifulSoup
    return len(BeautifulSoup(html, "html.parser").get_text())


def _word_count(html: str) -> int:
    from bs4 import BeautifulSoup
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    return len(text.split())


def _count_tag(html: str, tag: str) -> int:
    from bs4 import BeautifulSoup
    return len(BeautifulSoup(html, "html.parser").find_all(tag))


def _has_cta(html: str) -> bool:
    lowered = html.lower()
    cta_markers = [
        "subscribe", "inscreva", "clique aqui", "click here",
        "thank you for reading", "obrigado por ler", "sign up",
        "stay tuned", "follow us",
    ]
    return any(m in lowered for m in cta_markers)


def _has_competitor(html: str) -> bool:
    lowered = html.lower()
    return any(name in lowered for name in ["omelete", "jovem nerd", "ign brasil", "adorocinema"])


def _title_quality(title: str) -> list[str]:
    issues = []
    if not title:
        issues.append("❌ Título vazio")
        return issues
    if len(title) > 65:
        issues.append(f"❌ Título longo: {len(title)} chars (máx 65)")
    elif len(title) < 40:
        issues.append(f"⚠️  Título curto: {len(title)} chars (ideal 55-65)")
    else:
        issues.append(f"✅ Comprimento OK: {len(title)} chars")

    if title.endswith("?"):
        issues.append("❌ Título em forma de pergunta")
    else:
        issues.append("✅ Não é pergunta")

    # Verbs (rough check)
    import re
    verbs_present = ["chega", "confirma", "revela", "anuncia", "lança", "estreia",
                     "tem", "recebe", "ganha", "retorna", "volta", "apresenta",
                     "mostra", "começa", "termina", "publica", "divulga"]
    if any(v in title.lower() for v in verbs_present):
        issues.append("✅ Contém verbo no presente")
    else:
        issues.append("⚠️  Verbo no presente não detectado")

    if title != title.upper():
        issues.append("✅ Sem caixa-alta excessiva")

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not AI_API_KEYS:
        print("ERRO: Nenhuma chave GEMINI_ encontrada no .env")
        sys.exit(1)

    client = AIClient(
        keys=AI_API_KEYS,
        min_interval_s=float(os.getenv("AI_MIN_INTERVAL_S", 6)),
        backoff_base=20,
        backoff_max=120,
    )

    url, original_title = _pick_url()
    extractor = ContentExtractor()

    # ── Extração ─────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("EXTRAÇÃO")
    logger.info("=" * 60)
    t0 = time.perf_counter()
    raw_html = extractor._fetch_html(url)
    if not raw_html:
        print("ERRO: Não foi possível buscar o HTML da URL.")
        sys.exit(1)
    extracted = extractor.extract(raw_html, url=url)
    if not extracted or not extracted.get("content"):
        print("ERRO: Extração falhou — sem conteúdo.")
        sys.exit(1)

    html_raw = extracted["content"] + "\n".join(extracted.get("images", []))
    t_extract = time.perf_counter() - t0
    logger.info(f"Extração: {_word_count(html_raw)} palavras, {len(html_raw)} chars — {t_extract:.1f}s")

    # ── Fase 1: Sanitização ───────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("FASE 1 — SANITIZAÇÃO")
    logger.info("=" * 60)
    t1 = time.perf_counter()
    html_clean = sanitize(html_raw, client)
    t_sanitize = time.perf_counter() - t1
    logger.info(f"Sanitização: {_word_count(html_raw)} → {_word_count(html_clean)} palavras — {t_sanitize:.1f}s")

    # ── Fase 2: Reescrita ─────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("FASE 2 — REESCRITA EDITORIAL")
    logger.info("=" * 60)
    t2 = time.perf_counter()
    html_rewritten = rewrite(html_clean, {
        "domain": "maquinanerd.com.br",
        "link_block": "",
        "videos": extracted.get("videos", []),
    }, client)
    t_rewrite = time.perf_counter() - t2
    logger.info(f"Reescrita: {_word_count(html_clean)} → {_word_count(html_rewritten)} palavras — {t_rewrite:.1f}s")

    # ── Fase 3: SEO Pack ──────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("FASE 3 — SEO PACK")
    logger.info("=" * 60)
    t3 = time.perf_counter()
    result = seo_pack(html_rewritten, original_title, {"domain": "maquinanerd.com.br"}, client)
    t_seo = time.perf_counter() - t3

    if result is None:
        print("\n❌ FASE 3 FALHOU — seo_pack retornou None")
        sys.exit(1)

    t_total = time.perf_counter() - t0

    # ── Avaliação Final ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  AVALIAÇÃO FINAL DO ARTIGO GERADO PELO PIPELINE 3 FASES")
    print("=" * 70)

    titulo = result.get("titulo_final", "")
    conteudo = result.get("conteudo_final", "")
    meta_desc = result.get("meta_description", "")
    slug = result.get("slug", "")
    focus_kw = result.get("focus_keyphrase", "")
    tags = result.get("tags_sugeridas", [])
    categorias = result.get("categorias", [])

    print(f"\n📰 TÍTULO FINAL: {titulo}")
    print(f"   Original:     {original_title[:80]}")
    print()

    # Título
    print("── CHECKLIST DO TÍTULO ──────────────────────────────────────")
    for item in _title_quality(titulo):
        print(f"   {item}")

    # Conteúdo
    print()
    print("── CHECKLIST DO CONTEÚDO ────────────────────────────────────")
    print(f"   Palavras:     {_word_count(conteudo)}")
    print(f"   <h2>:         {_count_tag(conteudo, 'h2')}")
    print(f"   <h3>:         {_count_tag(conteudo, 'h3')}")
    print(f"   <figure>:     {_count_tag(conteudo, 'figure')}")
    print(f"   <h1>:         {'❌ ENCONTRADO' if _count_tag(conteudo, 'h1') else '✅ Ausente'}")
    print(f"   CTA:          {'❌ DETECTADO' if _has_cta(conteudo) else '✅ Limpo'}")
    print(f"   Concorrentes: {'❌ DETECTADOS' if _has_competitor(conteudo) else '✅ Limpo'}")

    # SEO
    print()
    print("── CHECKLIST SEO ────────────────────────────────────────────")
    meta_len = len(meta_desc)
    if 140 <= meta_len <= 155:
        print(f"   Meta desc: ✅ {meta_len} chars")
    elif meta_len:
        print(f"   Meta desc: ⚠️  {meta_len} chars (ideal 140-155)")
    else:
        print("   Meta desc: ❌ Vazia")

    print(f"   Slug:      {'✅' if slug else '❌ Vazio'} {slug}")
    print(f"   Focus KW:  {'✅' if focus_kw else '❌ Vazio'} {focus_kw}")
    kw_in_lead = focus_kw.lower() in conteudo[:500].lower() if focus_kw else False
    print(f"   KW no lead: {'✅ Sim' if kw_in_lead else '⚠️  Não detectada'}")
    print(f"   Tags:      {len(tags)} — {tags}")
    print(f"   Categorias: {[c.get('nome','?') for c in categorias]}")

    # Tempos
    print()
    print("── TEMPOS ───────────────────────────────────────────────────")
    print(f"   Extração:     {t_extract:.1f}s")
    print(f"   Fase 1 (sanitize): {t_sanitize:.1f}s")
    print(f"   Fase 2 (rewrite):  {t_rewrite:.1f}s")
    print(f"   Fase 3 (seo_pack): {t_seo:.1f}s")
    print(f"   TOTAL:        {t_total:.1f}s")

    # Prévia do conteúdo
    print()
    print("── PRÉVIA DO CONTEÚDO (primeiros 600 chars de texto) ────────")
    from bs4 import BeautifulSoup
    preview_text = BeautifulSoup(conteudo, "html.parser").get_text(separator=" ", strip=True)[:600]
    print(f"   {preview_text}")

    # Meta description
    print()
    print("── META DESCRIPTION ─────────────────────────────────────────")
    print(f"   {meta_desc}")

    # Salvar resultado
    out_path = ROOT / "debug" / f"test_3phase_{int(time.time())}.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "url": url,
            "original_title": original_title,
            "result": result,
            "timings": {
                "extract": round(t_extract, 2),
                "sanitize": round(t_sanitize, 2),
                "rewrite": round(t_rewrite, 2),
                "seo_pack": round(t_seo, 2),
                "total": round(t_total, 2),
            }
        }, f, indent=2, ensure_ascii=False)
    print()
    print(f"✅  Resultado completo salvo em: {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
