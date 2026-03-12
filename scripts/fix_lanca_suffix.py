#!/usr/bin/env python3
"""
Script para remover o sufixo "lança" dos títulos dos posts no WordPress.
Corrige o bug do SEO Title Optimizer que estava adicionando "lança" incorretamente.
"""

import requests
import json
from typing import List, Dict, Optional

# Configuração
WP_SITE_URL = "https://www.maquinanerd.com.br"
WP_API_URL = f"{WP_SITE_URL}/wp-json/wp/v2/posts"

# Credenciais (você precisa adicionar aqui)
WP_USERNAME = "seu_usuario_aqui"
WP_PASSWORD = "sua_senha_aqui"

def get_posts_with_lanca_suffix() -> List[Dict]:
    """Busca todos os posts que terminam com ' lança'."""
    try:
        response = requests.get(WP_API_URL, params={"per_page": 100})
        response.raise_for_status()
        posts = response.json()
        
        problematic_posts = []
        for post in posts:
            title = post.get("title", {}).get("rendered", "")
            if title.endswith(" lança"):
                problematic_posts.append(post)
        
        return problematic_posts
    except Exception as e:
        print(f"❌ Erro ao buscar posts: {e}")
        return []


def fix_post_title(post_id: int, new_title: str) -> bool:
    """Corrige o título de um post no WordPress."""
    try:
        auth = (WP_USERNAME, WP_PASSWORD)
        data = {"title": new_title}
        
        response = requests.post(
            f"{WP_API_URL}/{post_id}",
            json=data,
            auth=auth
        )
        response.raise_for_status()
        print(f"✅ Post {post_id} corrigido: '{new_title}'")
        return True
    except Exception as e:
        print(f"❌ Erro ao corrigir post {post_id}: {e}")
        return False


def main():
    """Função principal."""
    print("=" * 80)
    print("🔧 CORRIGINDO TÍTULOS COM SUFIXO 'lança' INCORRETO")
    print("=" * 80)
    print()
    
    # Buscar posts problemáticos
    print("🔍 Buscando posts com sufixo ' lança'...")
    problematic_posts = get_posts_with_lanca_suffix()
    
    if not problematic_posts:
        print("✅ Nenhum post com sufixo ' lança' encontrado!")
        return
    
    print(f"\n⚠️  Encontrados {len(problematic_posts)} posts com sufixo ' lança':")
    print()
    
    for post in problematic_posts:
        post_id = post["id"]
        title = post["title"]["rendered"]
        new_title = title[:-6]  # Remove " lança" (6 caracteres)
        
        print(f"Post ID {post_id}:")
        print(f"  Antes:  {title}")
        print(f"  Depois: {new_title}")
        print()
    
    print("=" * 80)
    print("ℹ️  INSTRUÇÕES:")
    print("=" * 80)
    print("""
1. Edite este script e adicione suas credenciais do WordPress:
   - WP_USERNAME: seu nome de usuário admin
   - WP_PASSWORD: sua senha ou token de autenticação

2. Ou, se preferir fazer manualmente:
   - Acesse o WordPress admin
   - Vá para Posts
   - Edite cada post e remova " lança" do final do título
   - Clique em "Atualizar"

Posts a corrigir:
""")
    
    for post in problematic_posts:
        post_id = post["id"]
        title = post["title"]["rendered"]
        print(f"  - [{post_id}] {title}")


if __name__ == "__main__":
    main()
