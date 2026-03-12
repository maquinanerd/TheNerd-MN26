import os
import logging
from dotenv import load_dotenv
from typing import Dict, List, Any

# Carrega variáveis de ambiente de um arquivo .env
load_dotenv(override=True)  # override=True garante que .env sobrescreve variaveis do sistema

logger = logging.getLogger(__name__)

# --- Ordem de processamento dos feeds ---
PIPELINE_ORDER: List[str] = [
    'screenrant_movie_lists',
    'screenrant_movie_news',
    'screenrant_tv',
]

# --- Feeds RSS (padronizados, sem "synthetic_from") ---
RSS_FEEDS: Dict[str, Dict[str, Any]] = {
    'screenrant_movie_lists': {
        'urls': ['https://screenrant.com/feed/movie-lists/'],
        'category': 'movies',
        'source_name': 'ScreenRant',
    },
    'screenrant_movie_news': {
        'urls': ['https://screenrant.com/feed/movie-news/'],
        'category': 'movies',
        'source_name': 'ScreenRant',
    },
    'screenrant_tv': {
        'urls': ['https://screenrant.com/feed/tv/'],
        'category': 'tv',
        'source_name': 'ScreenRant',
    },
}

# --- HTTP ---
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/91.0.4472.124 Safari/537.36'
)

# --- Configuração da IA ---
def _load_ai_keys() -> List[str]:
    """
    Lê todas as chaves GEMINI_* do ambiente e as retorna em uma lista única e ordenada.
    Procura por padrões: GEMINI_*, GEMINI_KEY*, GEMINI_API*
    """
    keys = {}
    
    # Procurar por todas as variáveis que contenham GEMINI e sejam chaves de API
    for key, value in os.environ.items():
        if value and 'GEMINI' in key.upper() and (key.upper().startswith('GEMINI_') or 'KEY' in key.upper() or 'API' in key.upper()):
            # Validar que é uma chave real (começa com AIza...)
            if str(value).startswith('AIza'):
                keys[key] = value
                logger.info(f"API KEY: {key}")
            else:
                logger.warning(f"VARIAVEL: {key} encontrada mas nao eh chave de API (nao comeca com AIza)")
    
    if not keys:
        logger.error("ERRO: NENHUMA CHAVE DE API GEMINI ENCONTRADA! Verificar .env")
    
    # Sort by key name for predictable order
    sorted_key_names = sorted(keys.keys())
    result = [keys[k] for k in sorted_key_names]
    
    logger.info(f"CARREGADAS {len(result)} chaves de API")
    for idx, key in enumerate(result, 1):
        logger.info(f"  [{idx}] {key[:15]}...{key[-4:]}")
    
    return result

AI_API_KEYS = _load_ai_keys()

# Caminho para o prompt universal na raiz do projeto
PROMPT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..',
    'universal_prompt.txt'
)

AI_MODEL = os.getenv('AI_MODEL', 'gemini-2.5-flash-lite')

AI_GENERATION_CONFIG = {
    'temperature': 0.7,
    'top_p': 1.0,
    'max_output_tokens': 4096,
}

# --- WordPress ---
WORDPRESS_CONFIG = {
    'url': os.getenv('WORDPRESS_URL'),
    'user': os.getenv('WORDPRESS_USER'),
    'password': os.getenv('WORDPRESS_PASSWORD'),
}

# --- Posts Pilares para Linkagem Interna ---
# Adicione aqui as URLs completas dos seus posts mais importantes.
# A lógica de linkagem interna dará prioridade máxima a links que apontam para estes artigos.
PILAR_POSTS: List[str] = [
    # Ex: "https://seusite.com/guia-completo-de-futebol",
    # Ex: "https://seusite.com/historia-das-copas-do-mundo",
]

# IDs das categorias no WordPress (ajuste os IDs conforme o seu WP)
WORDPRESS_CATEGORIES: Dict[str, int] = {
    'Notícias': 20,
    'Filmes': 24,
    'Séries': 21,  # ID correto de Séries (era 24 antes, mesmo ID de Filmes!)
    'Games': 73,
}

# Mapeia o source_id para uma lista de nomes de categorias
SOURCE_CATEGORY_MAP: Dict[str, List[str]] = {
    'screenrant_movie_lists': ['Filmes'],
    'screenrant_movie_news': ['Filmes'],
    'screenrant_tv': ['Séries'],
}


# --- Sinônimos de Categorias ---
# Mapeia nomes alternativos (em minúsculas) para o slug canônico em WORDPRESS_CATEGORIES
CATEGORY_ALIASES: Dict[str, str] = {}


# --- Agendador / Pipeline ---
SCHEDULE_CONFIG = {
    'check_interval_minutes': int(os.getenv('CHECK_INTERVAL_MINUTES', 15)),
    'max_articles_per_feed': int(os.getenv('MAX_ARTICLES_PER_FEED', 3)),
    'per_article_delay_seconds': int(os.getenv('PER_ARTICLE_DELAY_SECONDS', 8)),
    'per_feed_delay_seconds': int(os.getenv('PER_FEED_DELAY_SECONDS', 15)),
    'cleanup_after_hours': int(os.getenv('CLEANUP_AFTER_HOURS', 72)),
}

PIPELINE_CONFIG = {
    'images_mode': os.getenv('IMAGES_MODE', 'hotlink'),  # 'hotlink' ou 'download_upload'
    'attribution_policy': 'Fonte: {domain}',
    'publisher_name': 'MaquinaNerd',
    'publisher_logo_url': os.getenv(
        'PUBLISHER_LOGO_URL',
        'https://exemplo.com/logo.png'  # TODO: atualizar para a URL real do logo
    ),
}

# --- Configuração TMDb (The Movie Database) ---
TMDB_CONFIG = {
    'enabled': os.getenv('TMDB_ENABLED', 'false').lower() == 'true',
    'api_key': os.getenv('TMDB_API_KEY', ''),
    'max_enrichments_per_article': int(os.getenv('TMDB_MAX_ENRICHMENTS', 3)),
    'extract_trending': os.getenv('TMDB_EXTRACT_TRENDING', 'false').lower() == 'true',
    'extract_upcoming': os.getenv('TMDB_EXTRACT_UPCOMING', 'false').lower() == 'true',
}
