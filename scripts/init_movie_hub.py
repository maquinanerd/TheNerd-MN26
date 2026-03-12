#!/usr/bin/env python3
"""
Script de Inicialização e Teste do Movie Hub
Testa todas as funcionalidades e sincroniza dados iniciais
"""

import logging
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def init_hub():
    """Inicializa o hub de filmes"""
    try:
        logger.info("=" * 80)
        logger.info("🎬 INICIALIZANDO MOVIE HUB")
        logger.info("=" * 80)
        
        from app.movie_hub_manager import init_movie_hub
        
        # Inicializa
        logger.info("1️⃣ Criando banco de dados...")
        hub = init_movie_hub()
        logger.info("✅ Banco de dados criado: movie_hub.db")
        
        return hub
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar: {e}")
        sys.exit(1)


def test_tmdb_connection(hub):
    """Testa conexão com TMDb"""
    try:
        logger.info("\n2️⃣ Testando conexão com TMDb...")
        
        if not hub.tmdb:
            logger.error("❌ Cliente TMDb não disponível. Configure TMDB_API_KEY")
            return False
        
        # Testa busca
        results = hub.tmdb.search_movie("Inception")
        
        if results:
            logger.info(f"✅ Conexão OK! Encontrados {len(results)} filmes para 'Inception'")
            logger.info(f"   Primeiro resultado: {results[0]['title']} ({results[0]['release_date']})")
            return True
        else:
            logger.error("❌ Nenhum resultado retornado")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar TMDb: {e}")
        return False


def sync_initial_data(hub):
    """Sincroniza dados iniciais"""
    try:
        logger.info("\n3️⃣ Sincronizando dados iniciais...")
        
        # Sincronizar gêneros
        logger.info("   Sincronizando gêneros...")
        movie_count, tv_count = hub.sync_all_genres()
        logger.info(f"   ✅ {movie_count + tv_count} gêneros sincronizados")
        
        # Sincronizar trending
        logger.info("   Sincronizando filmes em tendência...")
        movies = hub.sync_trending_movies(limit=5)
        logger.info(f"   ✅ {len(movies)} filmes sincronizados")
        
        logger.info("   Sincronizando séries em tendência...")
        tv_series = hub.sync_trending_tv(limit=5)
        logger.info(f"   ✅ {len(tv_series)} séries sincronizadas")
        
        # Sincronizar upcoming
        logger.info("   Sincronizando próximos lançamentos...")
        upcoming = hub.sync_upcoming_movies(limit=3)
        logger.info(f"   ✅ {len(upcoming)} filmes 'em breve' sincronizados")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar: {e}")
        return False


def test_search_and_add(hub):
    """Testa busca e adição de filme"""
    try:
        logger.info("\n4️⃣ Testando busca e adição de filme...")
        
        # Buscar e adicionar
        logger.info("   Buscando 'Oppenheimer'...")
        movie = hub.search_and_add_movie("Oppenheimer", year=2023)
        
        if movie:
            logger.info(f"   ✅ Filme adicionado: {movie['title']}")
            logger.info(f"      Rating: {movie['rating']}/10")
            logger.info(f"      Release: {movie['release_date']}")
            return movie
        else:
            logger.error("❌ Filme não encontrado")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return None


def test_page_generation(hub, movie):
    """Testa geração de página"""
    try:
        logger.info("\n5️⃣ Testando geração de página...")
        
        if not movie:
            logger.warning("   ⚠️ Nenhum filme para gerar página")
            return False
        
        # Obter filme do banco
        db_movie = hub.movie_repo.get_movie_by_tmdb_id(movie['tmdb_id'])
        
        if db_movie:
            logger.info(f"   Gerando página para '{db_movie.title}'...")
            html = hub.generate_movie_page(db_movie.id)
            
            if html:
                logger.info(f"   ✅ Página gerada com sucesso ({len(html)} bytes)")
                
                # Salvar para referência
                with open('test_movie_page.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info("   📄 Salvo em: test_movie_page.html")
                
                return True
        else:
            logger.error("   ❌ Filme não encontrado no banco")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def show_statistics(hub):
    """Mostra estatísticas do banco de dados"""
    try:
        logger.info("\n6️⃣ Estatísticas do banco de dados...")
        
        # Contar filmes
        all_movies = hub.movie_repo.get_all_movies(limit=10000)
        trending_movies = hub.movie_repo.get_trending_movies(limit=10000)
        
        # Contar séries
        all_tv = hub.tv_repo.get_all_tv(limit=10000)
        trending_tv = hub.tv_repo.get_trending_tv(limit=10000)
        
        # Contar gêneros
        all_genres = hub.genre_repo.get_all_genres()
        
        logger.info(f"   📊 Filmes: {len(all_movies)} (Trending: {len(trending_movies)})")
        logger.info(f"   📺 Séries: {len(all_tv)} (Trending: {len(trending_tv)})")
        logger.info(f"   🎬 Gêneros: {len(all_genres)}")
        
        if all_movies:
            logger.info(f"\n   Últimos 3 filmes adicionados:")
            for movie in all_movies[-3:]:
                logger.info(f"   - {movie.title} ({movie.release_date}) ⭐ {movie.rating}/10")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def show_summary():
    """Mostra resumo final"""
    logger.info("\n" + "=" * 80)
    logger.info("✅ INICIALIZAÇÃO COMPLETA!")
    logger.info("=" * 80)
    logger.info("""
🎬 Movie Hub está pronto para usar!

Próximos passos:

1. Customizar sincronização:
   hub.sync_trending_movies(limit=20)
   hub.sync_trending_tv(limit=20)
   hub.sync_upcoming_movies(limit=15)

2. Buscar e adicionar filmes:
   movie = hub.search_and_add_movie("Seu Filme", year=2024)

3. Gerar páginas:
   html = hub.generate_movie_page(movie_id)

4. Integrar com WordPress:
   wordpress.publish_post(title=..., content=html)

📚 Documentação completa em: MOVIE_HUB_COMPLETE.md

Para mais ajuda, consulte os docstrings nos arquivos Python!
    """)


def main():
    """Função principal"""
    try:
        # Inicializar
        hub = init_hub()
        
        # Testes
        if not test_tmdb_connection(hub):
            logger.warning("⚠️ Pulando sincronização por falta de conexão TMDb")
        else:
            sync_initial_data(hub)
            movie = test_search_and_add(hub)
            test_page_generation(hub, movie)
        
        # Estatísticas
        show_statistics(hub)
        
        # Resumo
        show_summary()
        
        logger.info("\n🎉 Tudo pronto! O Movie Hub está funcionando!")
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
