#!/usr/bin/env python3
"""
SEO Crawler Discovery - Reconhecimento do site maquinanerd.com.br
Descobre quantas páginas existem e estima tempo de análise completa.
"""

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from collections import defaultdict

SITE_URL = "https://maquinanerd.com.br"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Limites de segurança
MAX_PAGES = 1000
TIMEOUT = 10

def get_domain(url):
    """Extrai domínio de uma URL"""
    return urlparse(url).netloc

def discover_pages():
    """Descobre todas as páginas do site"""
    visited = set()
    to_visit = [SITE_URL]
    pages_by_type = defaultdict(list)
    
    print(f"🔍 Iniciando descoberta de páginas em: {SITE_URL}\n")
    print("=" * 70)
    
    while to_visit and len(visited) < MAX_PAGES:
        current_url = to_visit.pop(0)
        
        if current_url in visited:
            continue
        
        # Verifica se é do mesmo domínio
        if get_domain(current_url) != get_domain(SITE_URL):
            continue
        
        visited.add(current_url)
        
        try:
            print(f"📄 [{len(visited)}/{MAX_PAGES}] Analisando: {current_url}", end='\r')
            
            response = requests.get(current_url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Classifica a página
            page_type = classify_page(current_url, soup)
            pages_by_type[page_type].append(current_url)
            
            # Encontra links para visitar
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Converte para URL absoluta
                absolute_url = urljoin(current_url, href)
                
                # Remove fragmentos
                absolute_url = absolute_url.split('#')[0]
                
                # Evita query strings complexas
                if '?' in absolute_url and absolute_url not in visited:
                    base_url = absolute_url.split('?')[0]
                    if base_url not in visited and len(to_visit) < MAX_PAGES * 2:
                        to_visit.append(base_url)
                elif absolute_url not in visited and len(to_visit) < MAX_PAGES * 2:
                    to_visit.append(absolute_url)
        
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout: {current_url}")
        except requests.exceptions.ConnectionError:
            print(f"❌ Erro de conexão: {current_url}")
        except Exception as e:
            print(f"⚠️  Erro ao processar {current_url}: {str(e)[:50]}")
    
    print("\n" + "=" * 70 + "\n")
    return visited, pages_by_type

def classify_page(url, soup):
    """Classifica o tipo de página"""
    path = urlparse(url).path.lower()
    title = soup.find('title')
    title_text = title.string if title else ""
    
    # Home
    if path in ['/', '']:
        return 'HOME'
    
    # Posts/Artigos
    if '/posts/' in path or '/blog/' in path or '/article' in path:
        return 'ARTIGO'
    
    # Categorias
    if '/category/' in path or '/categorias/' in path:
        return 'CATEGORIA'
    
    # Tags
    if '/tag/' in path or '/tags/' in path:
        return 'TAG'
    
    # Páginas estáticas
    if '/sobre' in path or '/contato' in path or '/privacidade' in path or '/termos' in path:
        return 'ESTÁTICA'
    
    # Autor
    if '/author/' in path or '/autor/' in path:
        return 'AUTOR'
    
    # Arquivo (por data)
    if any(x in path for x in ['/2024/', '/2025/', '/2023/', '/2022/']):
        return 'ARQUIVO'
    
    # Admin/WP
    if '/wp-' in path or '/admin' in path:
        return 'ADMIN'
    
    return 'OUTRA'

def print_report(visited, pages_by_type):
    """Imprime relatório de descoberta"""
    
    print("📊 RELATÓRIO DE DESCOBERTA DE PÁGINAS")
    print("=" * 70)
    print(f"✅ Total de páginas encontradas: {len(visited)}\n")
    
    print("📈 Páginas por tipo:")
    print("-" * 70)
    
    total = 0
    for page_type in sorted(pages_by_type.keys()):
        count = len(pages_by_type[page_type])
        total += count
        percentage = (count / len(visited) * 100) if visited else 0
        print(f"  {page_type:15} : {count:4} páginas ({percentage:5.1f}%)")
    
    print("-" * 70)
    print(f"  {'TOTAL':15} : {total:4} páginas\n")
    
    # Estimativas de tempo
    print("⏱️  ESTIMATIVAS DE TEMPO DE ANÁLISE:")
    print("-" * 70)
    
    # Tempo médio por página: ~2 segundos (incluindo parsing + análise SEO)
    avg_time_per_page = 2.0
    estimated_time_seconds = len(visited) * avg_time_per_page
    estimated_time_minutes = estimated_time_seconds / 60
    estimated_time_hours = estimated_time_minutes / 60
    
    print(f"  Tempo médio por página: {avg_time_per_page:.1f}s")
    print(f"  Tempo total estimado: {estimated_time_hours:.1f}h ({int(estimated_time_minutes)}min)\n")
    
    # Primeiras páginas de cada tipo
    print("📋 EXEMPLOS DE PÁGINAS POR TIPO:")
    print("-" * 70)
    
    for page_type in sorted(pages_by_type.keys()):
        if pages_by_type[page_type]:
            print(f"\n{page_type}:")
            for url in pages_by_type[page_type][:3]:
                # Encurta a URL para exibição
                short_url = url.replace(SITE_URL, "")
                if len(short_url) > 60:
                    short_url = short_url[:57] + "..."
                print(f"  - {short_url}")
            
            if len(pages_by_type[page_type]) > 3:
                print(f"  ... e mais {len(pages_by_type[page_type]) - 3}")

def main():
    print("\n🚀 DESCOBERTA DE PÁGINAS - maquinanerd.com.br\n")
    
    start_time = time.time()
    
    try:
        visited, pages_by_type = discover_pages()
        
        elapsed = time.time() - start_time
        print(f"✅ Descoberta concluída em {elapsed:.1f}s\n")
        
        print_report(visited, pages_by_type)
        
        print("\n" + "=" * 70)
        print("💡 PRÓXIMOS PASSOS:")
        print("=" * 70)
        print("""
1. Se o número de páginas for aceitável (<500):
   - Execute: python seo_crawler_full.py
   - Vai gerar relatório completo de SEO

2. Se for muito grande (>500):
   - Execute com filtros: python seo_crawler_full.py --type ARTIGO
   - Vai analisar apenas um tipo de página

3. Resultado será salvo em: seo_audit_report.html
        """)
        
    except Exception as e:
        print(f"\n❌ Erro durante descoberta: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
