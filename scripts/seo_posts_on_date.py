#!/usr/bin/env python3
"""
Extrai URLs dos sitemaps cujo <lastmod> começa com a data alvo.
Salva em 'posts_2025-10-30.txt'.
"""
import requests
from xml.etree import ElementTree as ET
from urllib.parse import urljoin

SITE = "https://maquinanerd.com.br"
TARGET_DATE = "2025-10-30"
HEADERS = {'User-Agent':'Mozilla/5.0'}


def get_sitemap_index():
    url = f"{SITE}/sitemap.xml"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    sitemaps = [elem.find('sm:loc', ns).text for elem in root.findall('sm:sitemap', ns) if elem.find('sm:loc', ns) is not None]
    return sitemaps


def urls_from_sitemap(sitemap_url):
    resp = requests.get(sitemap_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    out = []
    for url_elem in root.findall('sm:url', ns):
        loc = url_elem.find('sm:loc', ns)
        lastmod = url_elem.find('sm:lastmod', ns)
        if loc is None:
            continue
        loc_text = loc.text
        lastmod_text = lastmod.text if lastmod is not None else None
        out.append((loc_text, lastmod_text))
    return out


def main():
    print(f"Procurando posts com lastmod {TARGET_DATE}...\n")
    sitemaps = get_sitemap_index()
    print(f"Encontrados {len(sitemaps)} sitemaps na index\n")
    matched = []
    
    for s in sitemaps:
        print(f"Processando {s.split('/')[-1]}")
        try:
            pairs = urls_from_sitemap(s)
        except Exception as e:
            print(f"Erro ao ler {s}: {e}")
            continue
        for loc, lastmod in pairs:
            if lastmod and lastmod.startswith(TARGET_DATE):
                matched.append((loc, lastmod))

    print(f"\nTotal de URLs com lastmod {TARGET_DATE}: {len(matched)}")

    # Salva
    with open('posts_2025-10-30.txt', 'w', encoding='utf-8') as f:
        for loc, lastmod in matched:
            f.write(f"{loc}\t{lastmod}\n")

    print("Salvo em posts_2025-10-30.txt")

    # Escreve resumo simples
    types = {'ARTIGO':0, 'OUTRO':0}
    for loc, _ in matched:
        path = loc.replace(SITE, '').lower()
        if '/posts/' in path or '/post-' in path or '/2025/' in path or '/2024/' in path:
            types['ARTIGO'] += 1
        else:
            types['OUTRO'] += 1
    print('\nDistribuição aproximada:')
    for k,v in types.items():
        print(f"  {k}: {v}")

if __name__ == '__main__':
    main()
