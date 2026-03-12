#!/usr/bin/env python3
"""
SEO Crawler - Extrai URLs do sitemap.xml
Muito mais rápido que crawling tradicional
"""

import requests
from xml.etree import ElementTree as ET
import time

SITE_URL = "https://maquinanerd.com.br"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_sitemaps():
    """Obtém lista de sitemaps"""
    try:
        url = f"{SITE_URL}/sitemap.xml"
        response = requests.get(url, headers=HEADERS, timeout=10)
        root = ET.fromstring(response.content)
        
        # Remove namespace
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        sitemaps = []
        for sitemap in root.findall('sm:sitemap', ns):
            loc = sitemap.find('sm:loc', ns)
            if loc is not None:
                sitemaps.append(loc.text)
        
        return sitemaps
    except Exception as e:
        print(f"❌ Erro ao obter sitemaps: {e}")
        return []

def get_urls_from_sitemap(sitemap_url):
    """Extrai URLs de um sitemap"""
    try:
        response = requests.get(sitemap_url, headers=HEADERS, timeout=10)
        root = ET.fromstring(response.content)
        
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        for url_elem in root.findall('sm:url', ns):
            loc = url_elem.find('sm:loc', ns)
            lastmod = url_elem.find('sm:lastmod', ns)
            
            if loc is not None:
                urls.append({
                    'url': loc.text,
                    'lastmod': lastmod.text if lastmod is not None else None
                })
        
        return urls
    except Exception as e:
        print(f"❌ Erro ao processar {sitemap_url}: {e}")
        return []

def main():
    print("\n🚀 EXTRAÇÃO DE URLs VIA SITEMAP\n")
    print("=" * 80)
    
    # Obtém lista de sitemaps
    print("📍 Obtendo lista de sitemaps...")
    sitemaps = get_sitemaps()
    print(f"✅ Encontrados {len(sitemaps)} sitemaps\n")
    
    all_urls = []
    
    # Processa cada sitemap
    for i, sitemap_url in enumerate(sitemaps, 1):
        print(f"[{i}/{len(sitemaps)}] Processando: {sitemap_url.split('/')[-1]}", end=' ')
        
        urls = get_urls_from_sitemap(sitemap_url)
        all_urls.extend(urls)
        
        print(f"✅ {len(urls)} URLs")
        time.sleep(0.5)  # Respeita o servidor
    
    print("\n" + "=" * 80)
    print(f"\n📊 RESUMO:")
    print(f"  Total de URLs encontradas: {len(all_urls)}")
    
    # Agrupa por tipo
    from collections import defaultdict
    types = defaultdict(int)
    
    for item in all_urls:
        url = item['url']
        path = url.replace(SITE_URL, "").lower()
        
        if '/post/' in path or '/article/' in path:
            types['ARTIGOS'] += 1
        elif '/category/' in path or '/categorias/' in path:
            types['CATEGORIAS'] += 1
        elif '/tag/' in path:
            types['TAGS'] += 1
        else:
            types['OUTROS'] += 1
    
    print("\n📈 Distribuição por tipo:")
    for tipo, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(all_urls)) * 100
        print(f"  {tipo:15} : {count:5} ({pct:5.1f}%)")
    
    # Salva em arquivo
    with open('sitemap_urls.txt', 'w', encoding='utf-8') as f:
        for item in all_urls:
            f.write(f"{item['url']}\n")
    
    print(f"\n✅ URLs salvas em: sitemap_urls.txt")
    
    # Tempo estimado
    avg_time = 1.5  # segundos por página
    total_time = len(all_urls) * avg_time / 60
    print(f"\n⏱️  Tempo estimado para análise SEO completa: {total_time:.1f} minutos")
    
    return all_urls

if __name__ == "__main__":
    main()
