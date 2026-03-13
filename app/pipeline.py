# app/pipeline.py
import logging
import time
import json
import re
import os
import threading
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

from .config import (
    PIPELINE_ORDER,
    RSS_FEEDS,
    WORDPRESS_CONFIG,
    WORDPRESS_CATEGORIES,
    CATEGORY_ALIASES,
    PIPELINE_CONFIG,
    SOURCE_CATEGORY_MAP,
    AI_API_KEYS,
)
from .store import Database
from .feeds import FeedReader
from .extractor import ContentExtractor
from .ai_processor import AIProcessor
from .wordpress import WordPressClient
from .seo_title_optimizer import optimize_title
from .title_validator import TitleValidator
from .html_utils import (
    unescape_html_content,
    validate_and_fix_figures,
    merge_images_into_content,
    rewrite_img_srcs_with_wp,
    strip_credits_and_normalize_youtube,
    remove_broken_image_placeholders,
    strip_naked_internal_links,
    strip_ai_tag_links,
    downgrade_h1_to_h2,
    remove_source_domain_schemas,
    strip_forbidden_cta_sentences,
    detect_forbidden_cta,
    html_to_gutenberg_blocks,
)
from .internal_linking import add_internal_links
from .link_store import save_article as ls_save_article, get_related as ls_get_related, format_for_prompt as ls_format_links, get_link_map as ls_get_link_map
from .task_queue import ArticleQueue
from bs4 import BeautifulSoup
from .cleaners import clean_html_for_globo_esporte

logger = logging.getLogger(__name__)

# --- Global instances ---
article_queue = ArticleQueue()
ai_processor = AIProcessor()

# --- Environment variables for pipeline control ---
MAX_PER_FEED_CYCLE = int(os.getenv('MAX_PER_FEED_CYCLE', 3))
MAX_PER_CYCLE = int(os.getenv('MAX_PER_CYCLE', 10))
ARTICLE_SLEEP_S = int(os.getenv('ARTICLE_SLEEP_S', 120))  # 2 minutos entre ciclos
BETWEEN_BATCH_DELAY_S = int(os.getenv('BETWEEN_BATCH_DELAY_S', 30))  # 30s entre batches (rápido)
BETWEEN_PUBLISH_DELAY_S = int(os.getenv('BETWEEN_PUBLISH_DELAY_S', 30))  # 30s entre publicações

CLEANER_FUNCTIONS = {
    'globo.com': clean_html_for_globo_esporte,
}


def assess_content_quality(content_html: str) -> dict:
    """
    Score multifatorial de qualidade — decide indexação.
    Fatores: palavras, estrutura H2/H3, links internos, bloco editorial.
    Score >= 45 → indexar.  Score < 45 → noindex.
    """
    soup  = BeautifulSoup(content_html, "html.parser")
    text  = soup.get_text(separator=" ", strip=True)
    words = len(text.split())

    score = 0
    # 1. Volume de palavras
    if   words >= 600: score += 30
    elif words >= 400: score += 15

    # 2. Estrutura hierárquica (H3 dentro de H2 = profundidade real)
    if soup.find("h3"): score += 20
    if soup.find("h2"): score += 10

    # 3. Links internos (distribuem PageRank, ajudam cluster)
    int_links = [a for a in soup.find_all("a", href=True)
                 if "maquinanerd.com.br" in a["href"]]
    if   len(int_links) >= 2: score += 20
    elif len(int_links) >= 1: score += 10

    should_index = score >= 45
    reason = (
        f"score={score} | {words}w | h3={'sim' if soup.find('h3') else 'não'}"
        f" | links_int={len(int_links)} → {'INDEX' if should_index else 'NOINDEX'}"
    )
    return {"should_index": should_index, "word_count": words,
            "score": score, "reason": reason}


def semantic_qa_flash(title: str, content_html: str) -> dict:
    """
    Avaliação semântica via Gemini 2.5 Flash Lite — Camada 2 do QA.
    Custo: ~$0.24/mês. Latência: +0.5-1.5s por artigo.
    Ativada APENAS para artigos com score borderline (35-50).
    Detecta: CTA residual, valor informacional, tipo de conteúdo.
    """
    import json as _json
    import requests as _requests

    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)[:2000]

    prompt = f"""Avalie em 4 critérios. Responda APENAS em JSON, sem explicação.
Título: {title}
Texto: {text}
Retorne exatamente:
{{
  "has_original_value": true,
  "has_cta_residual": false,
  "content_type": "news",
  "quality_note": "observação em uma linha"
}}
has_original_value: true se o texto tem informação factual única (não é só repasse genérico)
has_cta_residual: true se houver qualquer frase promoção/CTA do texto original (subscribe, clique, etc)
content_type: "news" (notícia quente), "analysis" (análise/opinião), ou "evergreen" (guia atemporal)
quality_note: observação editorial em uma linha"""

    try:
        if not AI_API_KEYS:
            raise ValueError("Nenhuma chave de API disponível")
        api_key = AI_API_KEYS[0]
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256},
        }
        resp = _requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # remover marcadores de bloco de código se presentes
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return _json.loads(raw)
    except Exception as exc:
        logger.warning(f"[QA-LLM] Falha na avaliação semântica: {exc}")
        return {"has_original_value": True, "has_cta_residual": False,
                "content_type": "news", "quality_note": "erro_avaliação"}


def _get_article_url(article_data: Dict[str, Any]) -> Optional[str]:
    """Get article URL from various possible fields."""
    url = article_data.get("url") or article_data.get("link") or article_data.get("id")
    if not url:
        return None
    try:
        p = urlparse(url)
        if p.scheme in ("http", "https"):
            return url
    except Exception:
        return None
    return None

BAD_HOSTS = {"sb.scorecardresearch.com", "securepubads.g.doubleclick.net"}
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

def is_valid_upload_candidate(url: str) -> bool:
    """Check if a URL points to a valid image for upload."""
    if not url:
        return False
    try:
        lower_url = url.lower()
        p = urlparse(lower_url)
        
        if not p.scheme.startswith("http"):
            return False
        if p.netloc in BAD_HOSTS:
            return False
        if not p.path.endswith(IMG_EXTS):
            return False
        
        if "author" in lower_url or "avatar" in lower_url:
            return False
            
        dims = re.findall(r'[?&](?:w|width|h|height)=(\d+)', lower_url)
        if any(int(d) <= 100 for d in dims):
            return False
            
        return True
    except Exception:
        return False

def process_batch(articles: List[Dict[str, Any]], link_map: Dict[str, Any]):
    """Process a batch of articles."""
    if not articles:
        return

    db = Database()
    extractor = ContentExtractor()
    wp_client = WordPressClient(config=WORDPRESS_CONFIG, categories_map=WORDPRESS_CATEGORIES)

    try:
        # Extract content for all articles first
        extracted_articles = []
        for article_data in articles:
            article_db_id = article_data['db_id']
            source_id = article_data['source_id']
            feed_config = RSS_FEEDS.get(source_id, {})
            category = feed_config.get('category', 'Notícias')

            try:
                article_url = _get_article_url(article_data)
                if not article_url:
                    logger.warning(f"Skipping article {article_data.get('id')} - missing/invalid URL")
                    db.update_article_status(article_db_id, 'FAILED', reason="Missing/invalid URL")
                    continue

                logger.info(f"Processing article: {article_data.get('title', 'N/A')} (DB ID: {article_db_id}) from {source_id}")
                logger.info(f"  Original URL: {article_url}")
                db.update_article_status(article_db_id, 'PROCESSING')

                # Extract content
                html_content = extractor._fetch_html(article_url)
                if not html_content:
                    db.update_article_status(article_db_id, 'FAILED', reason="Failed to fetch HTML")
                    continue

                # Apply cleaners if needed
                soup = BeautifulSoup(html_content, 'lxml')
                domain = urlparse(article_url).netloc.lower()
                for cleaner_domain, cleaner_func in CLEANER_FUNCTIONS.items():
                    if cleaner_domain in domain:
                        soup = cleaner_func(soup)
                        logger.info(f"Applied cleaner for {cleaner_domain}")
                        break

                # Extract data
                extracted_data = extractor.extract(str(soup), url=article_url)
                if not extracted_data or not extracted_data.get('content'):
                    logger.warning(f"Failed to extract content from {article_url}")
                    db.update_article_status(article_db_id, 'FAILED', reason="Extraction failed")
                    continue

                # Add to batch
                extracted_articles.append({
                    'db_id': article_db_id,
                    'url': article_url,
                    'source_id': source_id,
                    'category': category,
                    'extracted': extracted_data,
                    'feed_config': feed_config,
                    'title': article_data.get('title', '')
                })

            except Exception as e:
                logger.error(f"Error extracting article {article_data.get('title', 'N/A')}: {e}", exc_info=True)
                db.update_article_status(article_db_id, 'FAILED', reason=str(e))

        # Process all extracted articles individually via AI (batch size 1)
        batch_count = 0
        for batch in [extracted_articles[i:i+1] for i in range(0, len(extracted_articles), 1)]:
            # Aguardar entre batches para garantir qualidade SEO
            if batch_count > 0:
                logger.info(f"Aguardando {BETWEEN_BATCH_DELAY_S}s entre batches (garantindo processamento de qualidade)...")
                time.sleep(BETWEEN_BATCH_DELAY_S)
            
            batch_data = []
            for art in batch:
                extracted = art['extracted']
                main_text = extracted.get('content', '')
                body_images_html = extracted.get('images', [])
                content_for_ai = main_text + "\n".join(body_images_html)

                # Detectar entidade do conteúdo fonte para sugestão de links
                from .cluster_engine import score_event as _score_event_pre
                _pre_event = _score_event_pre({
                    "title": extracted.get('title', ''),
                    "content": main_text,
                    "tags": [],
                })
                _related = ls_get_related(
                    entity=_pre_event.get("entity", ""),
                    category=art['category'],
                    limit=3,
                )
                _link_block = ls_format_links(_related)

                batch_data.append({
                    'title': extracted.get('title'),
                    'content_html': content_for_ai,
                    'source_url': art['url'],
                    'category': art['category'],
                    'videos': extracted.get('videos', []),
                    'images': extracted.get('images', []),
                    'source_name': art['feed_config'].get('source_name', ''),
                    'domain': wp_client.get_domain(),
                    'schema_original': extracted.get('schema_original'),
                    'link_block': _link_block,
                })

            try:
                # Process all articles in batch with one API call
                batch_results = ai_processor.rewrite_batch(batch_data)
                batch_count += 1

                # Process results in same order
                for art_data, (rewritten_data, failure_reason) in zip(batch, batch_results):
                    try:
                        if not rewritten_data:
                            reason = failure_reason or "AI processing failed"
                            logger.warning(f"Article '{art_data['title']}' - Marking as QUEUED for retry (Reason: {reason})")
                            # Mark as QUEUED instead of FAILED so it retries in next cycle (quota-friendly)
                            db.update_article_status(art_data['db_id'], 'QUEUED', reason=reason)
                            continue

                        # Process content
                        raw_content_html = rewritten_data.get("conteudo_final", "").strip()
                        title = rewritten_data.get("titulo_final", "").strip()

                        if not title or not raw_content_html:
                            db.update_article_status(art_data['db_id'], 'FAILED', reason="AI output missing required fields")
                            continue

                        cta_removal_log = []

                        raw_cta_match = detect_forbidden_cta(raw_content_html)
                        if raw_cta_match:
                            logger.error(f"🚨 CTA detectado na resposta bruta da IA: {raw_cta_match}")
                            cta_removal_log.append(f"RAW: {raw_cta_match}")

                        content_html, preclean_removed = strip_forbidden_cta_sentences(raw_content_html)
                        if preclean_removed:
                            logger.info("✅ CTA removido no pré-processamento (strip_forbidden_cta_sentences)")
                            cta_removal_log.append("PRE: strip_forbidden_cta_sentences")
                        else:
                            content_html = raw_content_html

                        # 🚨 NUCLEAR LIMPEZA: Remover "Thank you for reading..." DEFINITIVAMENTE
                        original_html = raw_content_html
                        
                        # CAMADA 1: Remover a frase EXATA (literal search)
                        nuclear_phrases = [
                            "Thank you for reading this post, don't forget to subscribe!",
                            "thank you for reading this post, don't forget to subscribe!",
                            "Thank you for reading this post, don't forget to subscribe",
                            "thank you for reading this post, don't forget to subscribe",
                        ]
                        
                        for phrase in nuclear_phrases:
                            if phrase in content_html:
                                logger.error(f"🔥 LAYER 1 (LITERAL): CTA encontrado: '{phrase[:50]}...'")
                                cta_removal_log.append(f"LITERAL: {phrase[:60]}")
                                content_html = content_html.replace(phrase, "")
                                logger.info("✅ Removido com sucesso")

                        # CAMADA 1.5: Remover variações com formatação inline ou apóstrofos diferentes
                        cta_sentence_patterns = [
                            r"(?is)(?:<p[^>]*>\s*)?(?:<[^>]+>\s*)*thank\s+you\s+for\s+reading(?:\s|&nbsp;|<[^>]+>)*?(?:this\s+post)?(?:\s|&nbsp;|<[^>]+>)*?don['’]t\s+forget\s+to\s+subscribe(?:\s|&nbsp;|<[^>]+>)*?(?:</p>)?",
                            r"(?is)(?:<p[^>]*>\s*)?(?:<[^>]+>\s*)*thanks\s+for\s+reading(?:\s|&nbsp;|<[^>]+>)*?(?:this\s+post)?(?:\s|&nbsp;|<[^>]+>)*?don['’]t\s+forget\s+to\s+subscribe(?:\s|&nbsp;|<[^>]+>)*?(?:</p>)?",
                            r"(?is)thank\s+you\s+for\s+reading[^<\n\r]*don['’]t\s+forget\s+to\s+subscribe[^<\n\r]*",
                        ]

                        for pattern in cta_sentence_patterns:
                            content_html, removed_count = re.subn(pattern, '', content_html)
                            if removed_count:
                                logger.error("🔥 LAYER 1.5 (SENTENCE REGEX): CTA removido via regex flexível")
                                cta_removal_log.append(f"SENTENCE_PATTERN: {pattern[:40]}...")

                        # CAMADA 2: Remover parágrafos INTEIROS que contêm padrões de CTA
                        cta_patterns = [
                            r'<p[^>]*>.*?thank you for reading this post.*?don\'t forget to subscribe.*?</p>',
                            r'<p[^>]*>.*?thank you for reading.*?don\'t forget.*?</p>',
                            r'<p[^>]*>.*?thank you for reading.*?</p>',
                            r'<p[^>]*>.*?thanks for reading.*?</p>',
                            r'<p[^>]*>.*?thanks for visiting.*?</p>',
                            r'<p[^>]*>.*?don\'t forget to subscribe.*?</p>',
                            r'<p[^>]*>.*?subscribe now.*?</p>',
                            r'<p[^>]*>.*?please subscribe.*?</p>',
                            r'<p[^>]*>.*?subscribe to our.*?</p>',
                            r'<p[^>]*>.*?stay tuned.*?</p>',
                            r'<p[^>]*>.*?follow us.*?</p>',
                            r'<p[^>]*>.*?if you enjoyed.*?</p>',
                            r'<p[^>]*>.*?found this helpful.*?</p>',
                            r'<p[^>]*>.*?click here.*?</p>',
                            r'<p[^>]*>.*?read more.*?</p>',
                            r'<p[^>]*>.*?sign up.*?</p>',
                            r'<p[^>]*>.*?obrigado por ler.*?</p>',
                            r'<p[^>]*>.*?obrigada por ler.*?</p>',
                            r'<p[^>]*>.*?não esqueça de se inscrever.*?</p>',
                            r'<p[^>]*>.*?se inscreva.*?</p>',
                            r'<p[^>]*>.*?clique aqui.*?</p>',
                            r'<p[^>]*>.*?leia mais.*?</p>',
                            r'<p[^>]*>.*?cadastre-se.*?</p>',
                            r'<p[^>]*>.*?fique atento.*?</p>',
                            r'<p[^>]*>.*?nos siga.*?</p>',
                            r'<p[^>]*>.*?mantenha-se atualizado.*?</p>',
                            r'<p[^>]*>.*?este artigo foi.*?</p>',
                            r'<p[^>]*>.*?se você gostou.*?</p>',
                        ]
                        
                        for pattern in cta_patterns:
                            original_length = len(content_html)
                            matches = re.findall(pattern, content_html, flags=re.IGNORECASE | re.DOTALL)
                            if matches:
                                logger.debug(f"REGEX: Encontrado {len(matches)} paragrafos com CTA")
                                for match in matches[:2]:  # Log dos 2 primeiros matches
                                    cta_removal_log.append(f"REGEX: {match[:80]}")
                            content_html = re.sub(pattern, '', content_html, flags=re.IGNORECASE | re.DOTALL)
                            if len(content_html) < original_length:
                                logger.debug(f"REMOVIDO: Paragrafo com CTA via regex")
                        
                        # CAMADA 3: Remover tags vazias deixadas para trás
                        content_html = re.sub(r'<(p|div|span|article)[^>]*>\s*</\1>', '', content_html, flags=re.IGNORECASE)
                        content_html = re.sub(r'<p[^>]*>\s*<br[^>]*>\s*</p>', '', content_html, flags=re.IGNORECASE)
                        
                        # CAMADA 4: Verificação FINAL - se ainda houver "thank you", REJEITA
                        if 'thank you for reading' in content_html.lower():
                            logger.error("CTA CRITICO: Ainda presente após limpeza! Rejeitando artigo")
                            db.update_article_status(art_data['db_id'], 'FAILED', reason="CTA persisted after cleaning - CRITICAL FAILURE")
                            continue
                        
                        # Log se houve remoção significativa
                        if len(content_html) < len(original_html):
                            chars_removed = len(original_html) - len(content_html)
                            logger.info(f"CTA removido: {chars_removed} chars. Prosseguindo com publicação")
                        
                        # VALIDAR TÍTULO CONFORME REGRAS EDITORIAIS
                        title_validator = TitleValidator()
                        validation_result = title_validator.validate(title)
                        
                        if validation_result['status'] == 'ERRO':
                            errors = validation_result.get('erros', [])
                            errs_joined = ' '.join(errors).lower()

                            def shorten_title(t: str, max_len: int = 65) -> str:
                                """Encurta o título de forma limpa tentando preservar sentido.
                                1) Tenta cortar em separadores (":", "-", "–", "—")
                                2) Se ainda estiver longo, corta sem quebrar palavras e adiciona reticências
                                """
                                import re
                                if len(t) <= max_len:
                                    return t
                                parts = re.split(r'[:\-–—]\s*', t)
                                for p in parts:
                                    if len(p) <= max_len:
                                        return p.strip()
                                trimmed = t[:max_len].rsplit(' ', 1)[0]
                                if not trimmed:
                                    trimmed = t[:max_len]
                                return trimmed.strip() + '…'

                            if 'muito longo' in errs_joined:
                                corrected_title = shorten_title(title, max_len=65)
                                if corrected_title != title:
                                    logger.info(f"TITULO ENCURTADO: '{corrected_title}'")
                                    title = corrected_title
                                    validation_result = title_validator.validate(title)
                                else:
                                    logger.warning(f"TITULO LONGO: Não foi possível encurtar. Prosseguindo")
                            elif 'muito curto' in errs_joined:
                                suggested = title_validator.suggest_correction(title)
                                if suggested and len(suggested) > len(title):
                                    logger.info(f"TITULO EXPANDIDO: '{suggested}'")
                                    title = suggested
                                    validation_result = title_validator.validate(title)
                                else:
                                    logger.warning(f"TITULO CURTO: Sem sugestão útil. Prosseguindo: {title}")

                            if validation_result['status'] == 'ERRO':
                                logger.warning(f"⚠️ Prosseguindo com título mesmo com erros editoriais: {title}")
                                for error in validation_result.get('erros', []):
                                    logger.warning(f"   {error}")
                                validation_result.setdefault('avisos', [])
                                validation_result['avisos'].extend(validation_result.get('erros', []))
                                validation_result['erros'] = []
                                validation_result['status'] = 'AVISO'
                        
                        if validation_result['status'] == 'AVISO':
                            logger.debug(f"TITULO AVISO: {title[:60]}")
                            for warning in validation_result['avisos']:
                                logger.debug(f"  {warning}")
                            # Tentar corrigir automaticamente
                            corrected_title = title_validator.suggest_correction(title)
                            if corrected_title != title:
                                logger.info(f"TITULO CORRIGIDO: {corrected_title[:60]}")
                                title = corrected_title
                        
                        # Otimizar título para Google News & Discovery
                        title, title_optimization_report = optimize_title(title, content_html)
                        logger.debug(f"TITULO SEO: {title_optimization_report['original_score']:.1f} > {title_optimization_report['optimized_score']:.1f}")
                        
                        # IMPORTANTE: Desescapar HTML que pode ter vindo escapado da IA
                        content_html = unescape_html_content(content_html)
                        
                        # Validar e corrigir estruturas de figura
                        content_html = validate_and_fix_figures(content_html)
                        
                        # Process images
                        extracted = art_data['extracted']
                        content_html = remove_broken_image_placeholders(content_html)
                        content_html = downgrade_h1_to_h2(content_html)
                        content_html = strip_ai_tag_links(content_html)
                        content_html = strip_naked_internal_links(content_html)
                        content_html = merge_images_into_content(content_html, extracted.get('images', []))

                        # Upload images
                        urls_to_upload = []
                        featured_image_url = extracted.get('featured_image_url')
                        featured_media_id = None
                        
                        if featured_image_url and is_valid_upload_candidate(featured_image_url):
                            # Try to upload featured image
                            media = wp_client.upload_media_from_url(featured_image_url, title)
                            if media and media.get("id"):
                                featured_media_id = media["id"]
                                logger.info(f"FEATURED OK: ID {featured_media_id}")

                        content_html = strip_credits_and_normalize_youtube(content_html)
                        # Remove schemas JSON-LD originais do domínio fonte (evita conflito de SEO)
                        content_html = remove_source_domain_schemas(content_html)

                        # Add credit line
                        source_name = art_data['feed_config'].get('source_name', urlparse(art_data['url']).netloc)
                        credit_line = f'<p><strong>Fonte:</strong> <a href="{art_data["url"]}" target="_blank" rel="noopener noreferrer">{source_name}</a></p>'
                        content_html += f"\n{credit_line}"

                        # Process categories
                        final_category_ids = {WORDPRESS_CATEGORIES['Notícias']}  # Default
                        if source_specific_names := SOURCE_CATEGORY_MAP.get(art_data['source_id']):
                            for name in source_specific_names:
                                if cat_id := WORDPRESS_CATEGORIES.get(name):
                                    final_category_ids.add(cat_id)

                        if suggested_categories := rewritten_data.get('categorias', []):
                            suggested_names = [cat['nome'] for cat in suggested_categories if isinstance(cat, dict) and 'nome' in cat]
                            normalized_names = [CATEGORY_ALIASES.get(name.lower(), name) for name in suggested_names]
                            if dynamic_category_ids := wp_client.resolve_category_names_to_ids(normalized_names):
                                final_category_ids.update(dynamic_category_ids)

                        # Add internal links
                        if link_map:
                            content_html = add_internal_links(
                                html_content=content_html,
                                link_map_data=link_map,
                                current_post_categories=list(final_category_ids)
                            )


                        # SEO meta
                        yoast_meta = rewritten_data.get('yoast_meta', {})
                        # canonical OMITIDO: Yoast gera self-referencing canonical automaticamente.
                        # A URL da fonte é citada editorialmente no corpo do artigo.
                        if related_kws := rewritten_data.get('related_keyphrases'):
                            yoast_meta['_yoast_wpseo_keyphrases'] = json.dumps([{"keyword": kw} for kw in related_kws])

                        # ─── QA Score — Camada 1: estrutural (sempre) ─────────────────────────────────
                        quality = assess_content_quality(content_html)
                        logger.info(f"[QA] {title[:50]} | {quality['reason']}")
                        noindex_value = "0" if quality["should_index"] else "1"

                        # ─── QA Score — Camada 2: semântica (apenas borderline 35–50) ─────────────
                        if 35 <= quality["score"] < 50:
                            qa2 = semantic_qa_flash(title, content_html)
                            logger.info(
                                f"[QA-LLM] type={qa2['content_type']} | "
                                f"original={qa2['has_original_value']} | "
                                f"cta={qa2['has_cta_residual']} | "
                                f"{qa2['quality_note'][:60]}"
                            )
                            if qa2["has_cta_residual"]:
                                logger.warning(f"[QA-LLM] CTA residual detectado: {title[:50]}")
                            if qa2["content_type"] == "evergreen" and qa2["has_original_value"]:
                                noindex_value = "0"  # forçar INDEX para evergreen com valor
                                logger.info(f"[QA-LLM] Forçando INDEX por tipo evergreen: {title[:50]}")
                            elif not qa2["has_original_value"]:
                                noindex_value = "1"  # confirmar NOINDEX sem valor original
                                logger.info(f"[QA-LLM] Confirmando NOINDEX sem valor original: {title[:50]}")

                        # VERIFICAÇÃO FINAL: CTA CHECK ANTES DE PUBLICAR
                        final_cta_match = detect_forbidden_cta(content_html)
                        if final_cta_match:
                            logger.error(f"CTA FINAL: Detectado '{final_cta_match}' - bloqueando publicação")
                            db.update_article_status(art_data['db_id'], 'FAILED', reason="FINAL CHECK: CTA detected before WordPress publishing - Article blocked")
                            continue

                        logger.debug("CTA OK: Nenhum CTA detectado. Pronto para publicar.")
                        
                        # Converter conteúdo para formato de blocos Gutenberg (WordPress padrão)
                        gutenberg_content = html_to_gutenberg_blocks(content_html)
                        
                        # Log qual chave de API foi usada para processar este artigo
                        api_key_used = ai_processor._ai_client.get_last_used_key() if ai_processor and ai_processor._ai_client else "UNKNOWN"
                        
                        # Publish to WordPress immediately (but processing was done in batch of 3)
                        post_payload = {
                            'title': title,
                            'slug': rewritten_data.get('slug'),
                            'content': gutenberg_content,  # ← Usando formato Gutenberg
                            'excerpt': rewritten_data.get('meta_description', ''),
                            'categories': list(final_category_ids),
                            'tags': rewritten_data.get('tags_sugeridas', []),
                            'featured_media': featured_media_id,
                            'meta': yoast_meta,
                        }

                        wp_post_id = wp_client.create_post(post_payload)
                        if wp_post_id and wp_post_id > 0:  # Verificar que é ID válido
                            try:
                                # ✅ UPDATE YOAST SEO METADATA (força OG:Image para imagem do site + metadados)
                                seo_meta = {
                                    'title': rewritten_data.get('seo_title', title)[:70],
                                    'description': rewritten_data.get('meta_description', '')[:160],
                                    'focuskw': rewritten_data.get('focus_keyword', rewritten_data.get('tags_sugeridas', [''])[0])[:30],
                                    'title_pt': title[:70],
                                    'description_pt': rewritten_data.get('meta_description', '')[:160],
                                    'noindex': noindex_value,
                                    'nofollow': '0',
                                }
                                yoast_ok = wp_client.update_post_yoast_seo(wp_post_id, featured_media_id, seo_meta)
                                if not yoast_ok:
                                    logger.warning(f"⚠️  Falha ao atualizar Yoast SEO para post {wp_post_id}, continuando anyway...")
                                
                                # ✅ ADD GOOGLE NEWS META TAGS (otimização para Google News)
                                news_meta = {
                                    'keywords': rewritten_data.get('tags_sugeridas', []),
                                    'genres': 'Blog, News',
                                    'standout': False,
                                    'access': 'Free',
                                }
                                news_ok = wp_client.add_google_news_meta(wp_post_id, news_meta)
                                if not news_ok:
                                    logger.debug(f"Google News meta tags não foram adicionados (não crítico)")
                                
                                sanitized_ok = wp_client.sanitize_published_post(wp_post_id)
                                if sanitized_ok:
                                    wp_post_url = f"https://www.maquinanerd.com.br/?p={wp_post_id}"
                                    logger.info(f"PUBLICADO: Post {wp_post_id} | {title[:70]}")
                                    logger.info(f"  URL no WordPress: {wp_post_url}")
                                    logger.info(f"  Categorias: {final_category_ids}")
                                    logger.info(f"  Tags: {rewritten_data.get('tags_sugeridas', [])}")
                                    logger.debug(f"  API Key: {api_key_used}")
                                    
                                    # ✅ SALVAR JSON COM SLUG (para fácil localização)
                                    slug = rewritten_data.get('slug', 'sem-slug')
                                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                                    json_filename = f"debug/ai_response_batch_{slug}_{timestamp}.json"
                                    json_path = Path(json_filename)
                                    
                                    # Salvar o rewritten_data como JSON
                                    with open(json_path, 'w', encoding='utf-8') as f:
                                        json.dump(rewritten_data, f, indent=2, ensure_ascii=False)
                                    logger.info(f"  JSON salvo em: {json_filename}")
                                    
                                    # ✅ REGISTRAR wp_post_id NOS TOKENS
                                    from .token_tracker import log_tokens
                                    log_tokens(
                                        prompt_tokens=0,
                                        completion_tokens=0,
                                        api_type="publishing",
                                        model="wordpress",
                                        metadata={"operation": "published", "original_url": art_data.get('url', 'N/A'), "slug": slug},
                                        source_url=art_data.get('url', 'N/A'),
                                        wp_post_id=wp_post_id,
                                        article_title=title
                                    )

                                    # ✅ EVENT SCORING — desabilitado temporariamente (evergreen pausado)
                                    from .cluster_engine import score_event
                                    event = score_event({
                                        "title":   title,
                                        "content": content_html,
                                        "tags":    rewritten_data.get("tags_sugeridas", []),
                                    })
                                    # schedule_cluster_pages desabilitado — evergreen pausado

                                    # ✅ LINK STORE — salvar artigo publicado para links internos futuros
                                    ls_save_article(
                                        title=title,
                                        url=f"https://www.maquinanerd.com.br/{rewritten_data.get('slug', 'sem-slug')}/",
                                        category=art_data['category'],
                                        entity=event.get("entity", ""),
                                    )
                                    logger.debug(f"[LINKS] Salvo no link_store: {title[:50]}")
                                else:
                                    logger.warning(f"Post {wp_post_id} criado mas sanitation falhou")
                            except Exception as e:
                                logger.error(f"Erro sanitizando post {wp_post_id}: {e}")

                            db.save_processed_post(art_data['db_id'], wp_post_id)
                            
                            # Small delay between posts
                            logger.info(f"Aguardando {BETWEEN_PUBLISH_DELAY_S}s para proximo...")
                            time.sleep(BETWEEN_PUBLISH_DELAY_S)
                        else:
                            logger.error(f"FALHA PUBLICACAO: {title[:70]}")
                            db.update_article_status(art_data['db_id'], 'FAILED', reason="WordPress publishing failed")

                    except Exception as e:
                        logger.error(f"Error processing article result {art_data['title']}: {e}", exc_info=True)
                        db.update_article_status(art_data['db_id'], 'FAILED', reason=str(e))

            except Exception as e:
                logger.error(f"Error processing batch: {e}", exc_info=True)
                # Se o lote falhar (ex: JSON malformado da IA), tente processar individualmente
                logger.warning("Batch processing failed. Attempting to process articles individually.")
                for art in batch:
                    try:
                        logger.info(f"Retrying article individually: {art['title']}")
                        # Recriar o payload para um único artigo
                        single_batch_data = [{
                            'title': art['extracted'].get('title'),
                            'content_html': art['extracted'].get('content', '') + "\n".join(art['extracted'].get('images', [])),
                            'source_url': art['url'], 'category': art['category'], 'videos': art['extracted'].get('videos', []),
                            'images': art['extracted'].get('images', []), 'source_name': art['feed_config'].get('source_name', ''),
                            'domain': wp_client.get_domain(), 'schema_original': art['extracted'].get('schema_original')
                        }]
                        # Chame o processador de IA com um único item
                        single_results = ai_processor.rewrite_batch(single_batch_data)
                        # A lógica de processamento do resultado já está dentro do loop, então podemos reusá-la
                        # (Esta é uma simplificação; uma refatoração maior poderia extrair a lógica de publicação)
                    except Exception as individual_e:
                        logger.error(f"Individual retry for article {art['title']} also failed: {individual_e}", exc_info=True)
                        db.update_article_status(art['db_id'], 'FAILED', reason=f"Individual retry failed: {individual_e}")

    finally:
        db.close()
        wp_client.close()

def worker_loop():
    """Continuously process articles from the queue in batches.
    
    Respects:
    - Max 10 AI requests per cycle (to avoid RPM violations)
    - 5-minute pause after hitting request limit
    """
    # Carregar link_map estático (fallback) + dados dinâmicos do SQLite
    static_link_map = {}
    try:
        with open('data/internal_links.json', 'r', encoding='utf-8') as f:
            static_link_map = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # JSON vazio é esperado; DB é a fonte primária

    def _refresh_link_map() -> dict:
        """Monta link_map fresco: SQLite (primário) + JSON estático (fallback)."""
        db_map = ls_get_link_map()
        json_posts = static_link_map.get('posts', [])
        db_urls = {p['link'] for p in db_map['posts']}
        extra = [p for p in json_posts if p['link'] not in db_urls]
        all_posts = db_map['posts'] + extra
        logger.info(f"[LINKS] link_map atualizado: {len(db_map['posts'])} do DB + {len(extra)} do JSON = {len(all_posts)} total")
        return {'posts': all_posts}

    link_map = _refresh_link_map()
    requests_in_cycle = 0
    MAX_REQUESTS_PER_CYCLE = 10
    PAUSE_ON_LIMIT_S = 300  # 5 minutos
    last_pause_time = time.time()
    QUEUE_TIMEOUT_S = 30  # 30 segundos timeout para esperar artigo

    while True:
        # Get articles from queue (batch size 1)
        articles = []
        start_wait = time.time()
        
        # Wait up to QUEUE_TIMEOUT_S for an article to appear in queue
        while time.time() - start_wait < QUEUE_TIMEOUT_S:
            if article := article_queue.pop():
                articles.append(article)
                break
            else:
                # Esperar um pouco antes de tentar novamente
                time.sleep(1)

        if not articles:
            # Still no articles after timeout, reset cycle counter and continue
            logger.debug("[WORKER] Nenhum artigo na fila após timeout de 30s")
            
            # Reset cycle counter after quiet period (2 minutos sem processar)
            if time.time() - last_pause_time > 120:
                logger.info("[RPM PROTECTION] Período de inatividade detectado. Resetando contador de requisições.")
                requests_in_cycle = 0
                last_pause_time = time.time()
            
            time.sleep(5)  # Esperar 5s antes de tentar novamente
            continue
        
        # Check if we've hit request limit BEFORE processing
        if requests_in_cycle >= MAX_REQUESTS_PER_CYCLE:
            logger.warning(
                f"[RPM PROTECTION] Atingido limite de {MAX_REQUESTS_PER_CYCLE} requisições por ciclo. "
                f"Pausando pipeline por {PAUSE_ON_LIMIT_S}s (5 minutos)."
            )
            # Retornar o artigo à fila para processar depois da pausa
            article_queue.push(articles[0])
            last_pause_time = time.time()
            time.sleep(PAUSE_ON_LIMIT_S)
            requests_in_cycle = 0
            logger.info("[RPM PROTECTION] Resumindo pipeline após pausa de 5 minutos.")
            continue

        # Refresh link_map before processing to pick up articles published this session
        link_map = _refresh_link_map()

        # Process batch and count requests
        process_batch(articles, link_map)
        requests_in_cycle += len(articles)
        last_pause_time = time.time()  # Atualizar timestamp de última atividade
        
        logger.info(
            f"Worker: {len(articles)} artigos processados. "
            f"Total requisições neste ciclo: {requests_in_cycle}/{MAX_REQUESTS_PER_CYCLE}. "
            f"Dormindo por {ARTICLE_SLEEP_S}s."
        )
        time.sleep(ARTICLE_SLEEP_S)

def run_pipeline_cycle():
    """Read feeds and enqueue articles for the worker."""
    logger.info("Starting new pipeline ingestion cycle.")

    # EVERGREEN: pausado temporariamente
    # from .evergreen_publisher import process_evergreen_queue
    # ev_count = process_evergreen_queue(max_per_cycle=2)
    # if ev_count:
    #     logger.info(f"[CYCLE] {ev_count} evergreen(s) publicado(s) neste ciclo")
    logger.debug("[CYCLE] Evergreen pausado.")

    db = Database()
    feed_reader = FeedReader(user_agent=PIPELINE_CONFIG.get('publisher_name', 'Bot'))
    
    processed_total_in_cycle = 0

    for source_id in PIPELINE_ORDER:
        if processed_total_in_cycle >= MAX_PER_CYCLE:
            logger.info(f"Max articles per cycle ({MAX_PER_CYCLE}) reached. Ending ingestion cycle.")
            break

        consecutive_failures = db.get_consecutive_failures(source_id)
        if consecutive_failures >= 3:
            logger.warning(f"Circuit open for feed {source_id} ({consecutive_failures} fails) -> skipping.")
            db.reset_consecutive_failures(source_id)
            continue

        feed_config = RSS_FEEDS.get(source_id)
        if not feed_config:
            logger.warning(f"No configuration found for feed source: {source_id}")
            continue

        logger.info(f"Ingesting feed: {source_id}")
        try:
            feed_items = feed_reader.read_feeds(feed_config, source_id)
            new_articles = db.filter_new_articles(source_id, feed_items)

            if not new_articles:
                logger.info(f"No new articles found for {source_id}.")
                continue
            
            # Apply per-feed and per-cycle limits
            limit = min(MAX_PER_FEED_CYCLE, MAX_PER_CYCLE - processed_total_in_cycle)
            articles_to_enqueue = new_articles[:limit]
            
            for article in articles_to_enqueue:
                article['source_id'] = source_id

            article_queue.push_many(articles_to_enqueue)
            
            processed_total_in_cycle += len(articles_to_enqueue)
            logger.info(f"Enqueued {len(articles_to_enqueue)} articles from {source_id}. Total in cycle: {processed_total_in_cycle}.")

            db.reset_consecutive_failures(source_id)

        except Exception as e:
            logger.error(f"Error processing feed {source_id}: {e}", exc_info=True)
            db.increment_consecutive_failures(source_id)
        
        # Stagger feed processing
        time.sleep(int(os.getenv('FEED_STAGGER_S', 45)))

    db.close()
    logger.info("Pipeline ingestion cycle finished.")

# Start the background worker thread
worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()