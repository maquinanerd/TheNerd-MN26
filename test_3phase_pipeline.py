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
from app.ai_rewrite import rewrite, has_editorial_block, count_padding_phrases, find_aggregator_residue
from app.ai_seo_pack import seo_pack


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_url() -> tuple[str, str]:
    """Return (url, title) — from argv or from ScreenRant RSS."""
    url_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if url_args:
        return url_args[0], "Artigo via CLI"

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
# Publicação no WordPress (acionada por --publish)
# ─────────────────────────────────────────────────────────────────────────────

def _publish_article(result: dict, extracted: dict, source_url: str) -> None:
    """Publica o artigo gerado no WordPress via REST API."""
    from urllib.parse import urlparse
    from app.html_utils import (
        unescape_html_content,
        validate_and_fix_figures,
        remove_broken_image_placeholders,
        downgrade_h1_to_h2,
        strip_ai_tag_links,
        strip_naked_internal_links,
        merge_images_into_content,
        strip_credits_and_normalize_youtube,
        remove_source_domain_schemas,
        detect_forbidden_cta,
        html_to_gutenberg_blocks,
    )
    from app.seo_title_optimizer import optimize_title
    from app.config import (
        WORDPRESS_CONFIG,
        WORDPRESS_CATEGORIES,
        CATEGORY_ALIASES,
    )
    from app.wordpress import WordPressClient

    print()
    print("=" * 70)
    print("  PUBLICANDO NO WORDPRESS")
    print("=" * 70)

    wp_client = WordPressClient(
        config=WORDPRESS_CONFIG,
        categories_map=WORDPRESS_CATEGORIES,
    )

    title = result.get("titulo_final", "")
    content_html = result.get("conteudo_final", "")

    # ── HTML cleaners (replicando pipeline.py) ────────────────────────────────
    content_html = unescape_html_content(content_html)
    content_html = validate_and_fix_figures(content_html)
    content_html = remove_broken_image_placeholders(content_html)
    content_html = downgrade_h1_to_h2(content_html)
    content_html = strip_ai_tag_links(content_html)
    content_html = strip_naked_internal_links(content_html)
    content_html = merge_images_into_content(content_html, extracted.get("images", []))

    # ── Otimização de título ──────────────────────────────────────────────────
    title, title_report = optimize_title(title, content_html)
    logger.info(f"Título final: {title}")

    # ── Upload imagem destacada ───────────────────────────────────────────────
    featured_media_id = None
    featured_image_url = extracted.get("featured_image_url")
    if featured_image_url:
        media = wp_client.upload_media_from_url(featured_image_url, title)
        if media and media.get("id"):
            featured_media_id = media["id"]
            logger.info(f"FEATURED OK: ID {featured_media_id}")

    content_html = strip_credits_and_normalize_youtube(content_html)
    content_html = remove_source_domain_schemas(content_html)

    # ── Linha de crédito ──────────────────────────────────────────────────────
    source_name = urlparse(source_url).netloc
    credit_line = (
        f'<p><strong>Fonte:</strong> '
        f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_name}</a>'
        f'</p>'
    )
    content_html += f"\n{credit_line}"

    # ── Categorias ────────────────────────────────────────────────────────────
    final_category_ids = {WORDPRESS_CATEGORIES.get("Notícias", 1)}
    if categorias := result.get("categorias", []):
        suggested_names = [
            cat["nome"] for cat in categorias if isinstance(cat, dict) and "nome" in cat
        ]
        normalized_names = [CATEGORY_ALIASES.get(n.lower(), n) for n in suggested_names]
        if dynamic_ids := wp_client.resolve_category_names_to_ids(normalized_names):
            final_category_ids.update(dynamic_ids)

    # ── CTA final check ───────────────────────────────────────────────────────
    cta_match = detect_forbidden_cta(content_html)
    if cta_match:
        logger.error(f"CTA detectado antes de publicar: '{cta_match}' — publicação bloqueada")
        print(f"\n❌ PUBLICAÇÃO BLOQUEADA — CTA detectado: '{cta_match}'")
        return

    # ── Gutenberg ─────────────────────────────────────────────────────────────
    gutenberg_content = html_to_gutenberg_blocks(content_html)

    # ── Yoast meta ────────────────────────────────────────────────────────────
    yoast_meta = result.get("yoast_meta", {})
    if related_kws := result.get("related_keyphrases"):
        yoast_meta["_yoast_wpseo_keyphrases"] = json.dumps(
            [{"keyword": kw} for kw in related_kws]
        )

    post_payload = {
        "title": title,
        "slug": result.get("slug"),
        "content": gutenberg_content,
        "excerpt": result.get("meta_description", ""),
        "categories": list(final_category_ids),
        "tags": result.get("tags_sugeridas", []),
        "featured_media": featured_media_id,
        "meta": yoast_meta,
    }

    # ── Publicar ──────────────────────────────────────────────────────────────
    wp_post_id = wp_client.create_post(post_payload)
    if not (wp_post_id and wp_post_id > 0):
        logger.error(f"create_post retornou ID inválido: {wp_post_id}")
        print(f"\n❌ FALHA NA PUBLICAÇÃO — create_post retornou: {wp_post_id}")
        return

    # ── Yoast SEO update ──────────────────────────────────────────────────────
    seo_meta = {
        "title": result.get("seo_title", title)[:70],
        "description": result.get("meta_description", "")[:160],
        "focuskw": result.get("focus_keyword", result.get("focus_keyphrase", ""))[:30],
        "title_pt": title[:70],
        "description_pt": result.get("meta_description", "")[:160],
        "noindex": "0",
        "nofollow": "0",
    }
    wp_client.update_post_yoast_seo(wp_post_id, featured_media_id, seo_meta)

    wp_post_url = f"https://www.maquinanerd.com.br/?p={wp_post_id}"
    print(f"\n✅ PUBLICADO COM SUCESSO!")
    print(f"   Post ID:  {wp_post_id}")
    print(f"   URL:      {wp_post_url}")
    print(f"   Título:   {title}")
    print(f"   Cats:     {final_category_ids}")
    print(f"   Tags:     {result.get('tags_sugeridas', [])}")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not AI_API_KEYS:
        print("ERRO: Nenhuma chave GEMINI_ encontrada no .env")
        sys.exit(1)

    publish_mode = "--publish" in sys.argv
    if publish_mode:
        logger.info("Modo --publish ativado: artigo será publicado no WordPress após geração.")

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

    # ── Checks editoriais (sobre html_rewritten) ──────────────────────────────
    editorial_ok = has_editorial_block(html_rewritten)
    padding_count = count_padding_phrases(html_rewritten)
    aggregator_residues = find_aggregator_residue(html_rewritten)

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

    # Checklist editorial
    print()
    print("── CHECKLIST EDITORIAL ──────────────────────────────────────")
    print(f"   Bloco editorial original: {'✅ OK' if editorial_ok else '❌ FALHOU'}")
    print(f"   Frases genéricas detectadas: {padding_count}{'  ⚠️' if padding_count >= 2 else ''}")
    agg_display = ', '.join(aggregator_residues) if aggregator_residues else 'NENHUM'
    print(f"   Resíduo de agregador: {'⚠️  ' + agg_display if aggregator_residues else '✅ NENHUM'}")

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
            "editorial_checks": {
                "editorial_block_present": editorial_ok,
                "padding_phrase_count": padding_count,
                "aggregator_residue": aggregator_residues,
            },
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

    # ── Publicação (somente com --publish) ────────────────────────────────────
    if publish_mode:
        _publish_article(result, extracted, url)


if __name__ == "__main__":
    main()
