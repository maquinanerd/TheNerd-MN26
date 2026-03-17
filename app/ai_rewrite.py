# app/ai_rewrite.py
"""
Phase 2 of the 3-phase AI pipeline: editorial rewrite.

Transforms sanitized HTML into an original Máquina Nerd article written
in journalistic Português-Brasil, injecting internal links and videos.
"""
import logging
import os
from typing import TYPE_CHECKING, Dict, Any, List

if TYPE_CHECKING:
    from .ai_client_gemini import AIClient

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
Você é um jornalista digital sênior do portal Máquina Nerd, especialista em cinema, séries, TV e games.

Reescreva o conteúdo abaixo como uma reportagem original do Máquina Nerd.

REGRAS OBRIGATÓRIAS:
- Português-Brasil natural. Mantenha em inglês apenas nomes oficiais de obras, personagens, empresas ou termos sem tradução natural (ex: showrunner, spin-off, season finale).
- Verbos no presente: "chega", "confirma", "revela" — NUNCA infinitivo.
- Parágrafos com no máximo 4 frases. Quebre ideias complexas em múltiplos <p>.
- Não mencione outros portais.
- O texto deve soar como reportagem original, não como tradução ou agregação mecânica.
- NUNCA use <h1>. Máximo 6 <h2> (exceto listicles com mais itens).
- Sem padding genérico ("os fãs podem esperar...", "a série tem potencial...").
- Negrito (<b>) na primeira ocorrência em cada parágrafo: nomes de séries/filmes/jogos, plataformas de streaming, franquias, personagens, atores, diretores, produtoras.
- Imagens em <figure> com <figcaption> descritivo. Nunca duas imagens seguidas sem <p> entre elas.
- Links internos (máx 4): <a href="https://{domain}/tag/tag-aqui">Texto âncora</a> — sempre com https://. Âncora = nome de franquia, série, filme ou ator. NUNCA "clique aqui" ou "saiba mais".

ESTRUTURA PARA NOTÍCIA (anúncio, trailer, lançamento, bilheteria, renovação):
1. Lead forte: O quê, Quem, Quando, Por quê — com dados reais.
2. <h2>O que você precisa saber</h2> com <ul> de 3 fatos verificáveis.
   — Use APENAS em notícias quentes com contexto suficiente. Omita em notícias curtas.
3. 2–4 <h2>s de desenvolvimento com dados reais (números, nomes, fatos). Proibido headings genéricos.
   — Use <h3> filho apenas quando o volume justificar. Não force em notícias curtas.

ESTRUTURA PARA LISTICLE (lista de títulos/filmes/jogos/séries):
1. Parágrafo introdutório de contexto.
2. Cada item da lista original vira <h2> ou <h3> — mantendo todos os itens e a ordem original.
3. Para cada item: preservar descrição, imagem e dados.
4. Parágrafo de fechamento opcional.

LINKS INTERNOS DISPONÍVEIS (use 1 a 3 contextualmente):
{link_block}

VÍDEOS DISPONÍVEIS (incorpore no máximo 3, no formato abaixo):
<figure class="video-container"><iframe src="URL_AQUI" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></figure>
{videos_list}

DOMÍNIO PARA LINKS INTERNOS: {domain}

CONTEÚDO PARA REESCREVER:
{content}

Retorne apenas o HTML final, sem texto adicional, sem JSON, sem marcadores markdown."""


def rewrite(html_clean: str, meta: Dict[str, Any], client: "AIClient") -> str:
    """
    Phase 2: transform clean HTML into original Máquina Nerd journalism.

    Args:
        html_clean: Sanitized HTML from phase 1.
        meta:       Dict with keys: domain, link_block, videos (list of dicts with embed_url).
        client:     Shared AIClient instance.

    Returns:
        Rewritten HTML string. Falls back to html_clean on AI failure.
    """
    if not html_clean or not html_clean.strip():
        return html_clean

    domain = meta.get("domain", "")
    link_block = meta.get("link_block", "Nenhum")
    videos: List[Dict[str, Any]] = meta.get("videos", [])
    videos_list = "\n".join(
        v.get("embed_url", "") for v in videos if isinstance(v, dict) and v.get("embed_url")
    ) or "Nenhum"

    prompt = _PROMPT_TEMPLATE.format(
        domain=domain,
        link_block=link_block,
        videos_list=videos_list,
        content=html_clean,
    )

    generation_config = {
        "temperature": 0.4,
        "max_output_tokens": 16000,
    }

    try:
        response_data = client.generate_text(prompt, generation_config=generation_config)

        if isinstance(response_data, tuple):
            response_text, tokens_info = response_data
        else:
            response_text = response_data
            tokens_info = {}

        _log_phase_tokens(tokens_info, phase="rewrite")

        if not response_text or not response_text.strip():
            logger.warning("[REWRITE] AI returned empty response — using sanitized HTML")
            return html_clean

        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]).rstrip("`").strip()

        logger.info(f"[REWRITE] OK — {len(html_clean)} → {len(text)} chars")
        return text

    except Exception as exc:
        logger.error(f"[REWRITE] AI call failed: {exc} — using sanitized HTML", exc_info=True)
        return html_clean


def _log_phase_tokens(tokens_info: dict, phase: str) -> None:
    try:
        from .token_tracker import log_tokens
        prompt_tokens = int(tokens_info.get("prompt_tokens", 0))
        completion_tokens = int(tokens_info.get("completion_tokens", 0))
        if prompt_tokens + completion_tokens > 0:
            log_tokens(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                api_type="gemini",
                model=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite"),
                metadata={"operation": f"3phase_{phase}"},
            )
    except Exception as exc:
        logger.debug(f"[REWRITE] token logging skipped: {exc}")
