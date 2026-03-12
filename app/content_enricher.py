"""
Enriquecedor de conteúdo com dados da TMDb
Adiciona informações sobre filmes/séries mencionadas nos artigos.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from app.tmdb_client import get_tmdb_client, TMDbClient

logger = logging.getLogger(__name__)


class ContentEnricher:
    """Enriquece artigos com dados da TMDb"""
    
    def __init__(self, tmdb_client: Optional[TMDbClient] = None):
        """
        Inicializa o enriquecedor
        
        Args:
            tmdb_client: Cliente TMDb (cria novo se None)
        """
        self.tmdb_client = tmdb_client or get_tmdb_client()
    
    def extract_movie_titles(self, text: str) -> List[str]:
        """
        Extrai possíveis títulos de filmes/séries do texto
        
        Usa heurísticas para identificar títulos
        
        Args:
            text: Texto para analisar
            
        Returns:
            Lista de possíveis títulos
        """
        # Procura por padrões como: "filme" entre aspas ou em CAPS
        patterns = [
            r'"([^"]{3,})"',  # Texto entre aspas duplas
            r"'([^']{3,})'",  # Texto entre aspas simples
            r'\b([A-Z][A-Za-z\s]{2,})\s*\(',  # CAPS seguido de parêntesis
        ]
        
        titles = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            titles.update(matches)
        
        return list(titles)
    
    def search_and_enrich_movie(self, title: str) -> Optional[Dict]:
        """
        Busca um filme na TMDb e retorna dados enriquecidos
        
        Args:
            title: Título do filme
            
        Returns:
            Dicionário com dados do filme ou None
        """
        if not self.tmdb_client:
            return None
        
        try:
            results = self.tmdb_client.search_movie(title)
            
            if not results:
                logger.debug(f"[TMDb] Filme '{title}' não encontrado")
                return None
            
            # Pega o primeiro resultado (mais relevante)
            movie = results[0]
            
            # Obtém detalhes completos
            details = self.tmdb_client.get_movie_details(movie['id'])
            if details:
                formatted = self.tmdb_client.format_movie_data(details)
                logger.info(f"[TMDb] Enriquecido: {formatted['title']} ({formatted['rating']}/10)")
                return formatted
            
        except Exception as e:
            logger.error(f"[TMDb] Erro ao buscar filme '{title}': {str(e)}")
        
        return None
    
    def search_and_enrich_tv(self, title: str) -> Optional[Dict]:
        """
        Busca uma série na TMDb e retorna dados enriquecidos
        
        Args:
            title: Título da série
            
        Returns:
            Dicionário com dados da série ou None
        """
        if not self.tmdb_client:
            return None
        
        try:
            results = self.tmdb_client.search_tv(title)
            
            if not results:
                logger.debug(f"[TMDb] Série '{title}' não encontrado")
                return None
            
            # Pega o primeiro resultado
            tv = results[0]
            
            # Obtém detalhes completos
            details = self.tmdb_client.get_tv_details(tv['id'])
            if details:
                formatted = self.tmdb_client.format_tv_data(details)
                logger.info(f"[TMDb] Enriquecido: {formatted['title']} (S{formatted['total_seasons']})")
                return formatted
            
        except Exception as e:
            logger.error(f"[TMDb] Erro ao buscar série '{title}': {str(e)}")
        
        return None
    
    def get_trending_movies(self, limit: int = 5) -> List[Dict]:
        """
        Obtém filmes em tendência para usar como conteúdo relacionado
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de filmes em tendência
        """
        if not self.tmdb_client:
            return []
        
        try:
            results = self.tmdb_client.get_trending('movie', 'week')
            
            enriched = []
            for movie in results[:limit]:
                details = self.tmdb_client.get_movie_details(movie['id'])
                if details:
                    enriched.append(self.tmdb_client.format_movie_data(details))
            
            return enriched
        except Exception as e:
            logger.error(f"[TMDb] Erro ao buscar trending: {str(e)}")
            return []
    
    def get_upcoming_movies(self, limit: int = 5) -> List[Dict]:
        """
        Obtém próximos lançamentos de filmes
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de filmes em breve
        """
        if not self.tmdb_client:
            return []
        
        try:
            results = self.tmdb_client.get_upcoming_movies()
            
            enriched = []
            for movie in results[:limit]:
                details = self.tmdb_client.get_movie_details(movie['id'])
                if details:
                    enriched.append(self.tmdb_client.format_movie_data(details))
            
            return enriched
        except Exception as e:
            logger.error(f"[TMDb] Erro ao buscar upcoming: {str(e)}")
            return []
    
    def generate_movie_widget_html(self, movie: Dict) -> str:
        """
        Gera HTML de widget para exibir filme no artigo
        
        Args:
            movie: Dados do filme
            
        Returns:
            HTML do widget
        """
        if not movie:
            return ''
        
        html = f"""
<!-- TMDb Movie Widget -->
<div class="tmdb-movie-widget" style="border-left: 4px solid #F5A623; padding: 15px; background: #f9f9f9; margin: 20px 0;">
    <div style="display: flex; gap: 15px;">
        <div style="flex-shrink: 0;">
            <img src="{movie['poster_url']}" alt="{movie['title']}" style="width: 100px; height: auto; border-radius: 4px;">
        </div>
        <div style="flex: 1;">
            <h3 style="margin: 0 0 5px 0;">{movie['title']}</h3>
            <p style="margin: 0; color: #666; font-size: 0.9em;">
                ⭐ {movie['rating']}/10 | 📅 {movie['release_date']}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 0.9em; line-height: 1.5;">
                {movie['overview'][:200]}...
            </p>
        </div>
    </div>
</div>
<!-- End TMDb Widget -->
"""
        return html
    
    def generate_tv_widget_html(self, tv: Dict) -> str:
        """
        Gera HTML de widget para exibir série no artigo
        
        Args:
            tv: Dados da série
            
        Returns:
            HTML do widget
        """
        if not tv:
            return ''
        
        html = f"""
<!-- TMDb TV Widget -->
<div class="tmdb-tv-widget" style="border-left: 4px solid #4169E1; padding: 15px; background: #f9f9f9; margin: 20px 0;">
    <div style="display: flex; gap: 15px;">
        <div style="flex-shrink: 0;">
            <img src="{tv['poster_url']}" alt="{tv['title']}" style="width: 100px; height: auto; border-radius: 4px;">
        </div>
        <div style="flex: 1;">
            <h3 style="margin: 0 0 5px 0;">{tv['title']}</h3>
            <p style="margin: 0; color: #666; font-size: 0.9em;">
                ⭐ {tv['rating']}/10 | 📺 {tv['total_seasons']} temporadas | 📅 {tv['first_air_date']}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 0.9em; line-height: 1.5;">
                {tv['overview'][:200]}...
            </p>
        </div>
    </div>
</div>
<!-- End TMDb Widget -->
"""
        return html


def enrich_article_with_tmdb(
    article_title: str,
    article_content: str,
    max_enrichments: int = 3
) -> Tuple[str, List[Dict]]:
    """
    Função auxiliar para enriquecer um artigo inteiro
    
    Args:
        article_title: Título do artigo
        article_content: Conteúdo do artigo (HTML)
        max_enrichments: Máximo de filmes/séries a adicionar
        
    Returns:
        Tupla (conteúdo enriquecido, lista de mídia adicionada)
    """
    enricher = ContentEnricher()
    
    if not enricher.tmdb_client:
        logger.warning("[TMDb] Cliente não disponível, skipping enrichment")
        return article_content, []
    
    # Extrai possíveis títulos
    titles = enricher.extract_movie_titles(article_title + ' ' + article_content)
    
    enriched_media = []
    enhanced_content = article_content
    
    for title in titles[:max_enrichments]:
        # Tenta buscar como filme primeiro
        movie = enricher.search_and_enrich_movie(title)
        if movie:
            widget = enricher.generate_movie_widget_html(movie)
            enhanced_content += f"\n{widget}"
            enriched_media.append(movie)
            continue
        
        # Se não for filme, tenta série
        tv = enricher.search_and_enrich_tv(title)
        if tv:
            widget = enricher.generate_tv_widget_html(tv)
            enhanced_content += f"\n{widget}"
            enriched_media.append(tv)
    
    return enhanced_content, enriched_media
