#!/usr/bin/env python3
"""
SEO Audit Crawler - Análise completa de SEO dos artigos
Focado em posts/artigos apenas
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
from datetime import datetime
from collections import defaultdict
import sys

SITE_URL = "https://www.maquinanerd.com.br"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

class SEOAuditor:
    def __init__(self):
        self.results = []
        self.issues = defaultdict(int)
        self.start_time = time.time()
        
    def analyze_page(self, url):
        """Analisa uma página para SEO"""
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Coleta informações
            title = soup.find('title')
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_robots = soup.find('meta', attrs={'name': 'robots'})
            h1 = soup.find('h1')
            h2_tags = soup.find_all('h2')
            canonical = soup.find('link', attrs={'rel': 'canonical'})
            images = soup.find_all('img')
            internal_links = soup.find_all('a', href=True)
            
            # Análise de SEO
            issues = []
            score = 100
            
            # TITLE
            title_text = title.string if title else ""
            if not title_text:
                issues.append("❌ Title tag ausente")
                score -= 20
            elif len(title_text) < 30:
                issues.append(f"⚠️  Title muito curto ({len(title_text)} chars, recomendado 50-60)")
                score -= 10
            elif len(title_text) > 60:
                issues.append(f"⚠️  Title muito longo ({len(title_text)} chars, recomendado 50-60)")
                score -= 5
            
            # META DESCRIPTION
            meta_desc_text = meta_desc.get('content', '') if meta_desc else ""
            if not meta_desc_text:
                issues.append("❌ Meta description ausente")
                score -= 20
            elif len(meta_desc_text) < 120:
                issues.append(f"⚠️  Meta description curta ({len(meta_desc_text)} chars, recomendado 120-160)")
                score -= 10
            elif len(meta_desc_text) > 160:
                issues.append(f"⚠️  Meta description longa ({len(meta_desc_text)} chars, recomendado 120-160)")
                score -= 5
            
            # H1
            if not h1:
                issues.append("❌ H1 ausente")
                score -= 15
            elif len(h1.get_text(strip=True)) < 10:
                issues.append("⚠️  H1 muito curto")
                score -= 5
            
            # MÚLTIPLOS H1
            h1_count = len(soup.find_all('h1'))
            if h1_count > 1:
                issues.append(f"⚠️  Múltiplos H1 encontrados ({h1_count})")
                score -= 5
            
            # H2/H3 STRUCTURE
            if len(h2_tags) == 0:
                issues.append("⚠️  Nenhum H2 encontrado")
                score -= 10
            
            # CANONICAL
            if not canonical:
                issues.append("⚠️  Canonical tag ausente")
                score -= 10
            
            # IMAGENS SEM ALT
            images_without_alt = 0
            for img in images:
                if not img.get('alt'):
                    images_without_alt += 1
            
            if images_without_alt > 0:
                issues.append(f"⚠️  {images_without_alt} imagens sem atributo ALT")
                score -= min(images_without_alt * 2, 15)
            
            # ROBOTS
            if meta_robots and 'noindex' in meta_robots.get('content', '').lower():
                issues.append("❌ Página marcada como NOINDEX!")
                score -= 30
            
            # INTERNAL LINKS
            internal_links_count = 0
            for link in internal_links:
                href = link.get('href', '')
                if href.startswith('/') or SITE_URL in href:
                    internal_links_count += 1
            
            if internal_links_count == 0:
                issues.append("⚠️  Nenhum link interno")
                score -= 10
            
            # COMPRIMENTO DO CONTEÚDO
            body = soup.find('body')
            text_length = len((body.get_text(strip=True) if body else ""))
            if text_length < 300:
                issues.append(f"⚠️  Conteúdo muito curto ({text_length} chars)")
                score -= 15
            elif text_length > 5000:
                issues.append(f"✅ Conteúdo bem desenvolvido ({text_length} chars)")
                score += 5
            
            # PALAVRA-CHAVE NO TITLE
            word_count = len(title_text.split())
            if word_count < 3:
                issues.append("⚠️  Title com poucas palavras")
                score -= 5
            
            # Garante score mínimo
            score = max(0, min(100, score))
            
            result = {
                'url': url,
                'title': title_text[:60] if title_text else "N/A",
                'description': meta_desc_text[:100] if meta_desc_text else "N/A",
                'h1': h1.get_text(strip=True)[:60] if h1 else "N/A",
                'h2_count': len(h2_tags),
                'images_count': len(images),
                'images_without_alt': images_without_alt,
                'internal_links': internal_links_count,
                'content_length': text_length,
                'score': score,
                'issues': issues,
                'title_length': len(title_text),
                'description_length': len(meta_desc_text),
            }
            
            return result
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e)[:50],
                'score': 0
            }
    
    def categorize_score(self, score):
        """Categoriza score em cores"""
        if score >= 90:
            return "🟢 EXCELENTE"
        elif score >= 75:
            return "🟡 BOM"
        elif score >= 60:
            return "🟠 OKAY"
        else:
            return "🔴 RUIM"

def load_article_urls():
    """Carrega URLs de artigos do sitemap_urls.txt"""
    try:
        with open('sitemap_urls.txt', 'r', encoding='utf-8') as f:
            all_urls = [line.strip() for line in f if line.strip()]
        
        # Filtra apenas artigos (post-sitemap.xml)
        article_urls = []
        for url in all_urls:
            # Heurística: artigos geralmente têm padrão de URL
            if '/post-sitemap' in url or '/article/' in url or '/blog/' in url:
                # Mais específico: artigos publicados
                if any(year in url for year in ['2024', '2025', '2023']):
                    article_urls.append(url)
        
        return article_urls
    except FileNotFoundError:
        print("❌ Arquivo sitemap_urls.txt não encontrado!")
        print("   Execute seo_crawler_sitemap.py primeiro")
        return []

def main():
    print("\n" + "=" * 90)
    print("🔍 SEO AUDIT CRAWLER - ANÁLISE DE ARTIGOS")
    print("=" * 90 + "\n")
    
    # Carrega URLs
    print("📍 Carregando URLs de artigos...")
    article_urls = load_article_urls()
    
    # Nota: sitemap_urls.txt tem tudo misturado, vou fazer uma amostragem inteligente
    # Vou pegar os primeiros 50 artigos pra análise rápida
    print(f"   Total de URLs no sitemap: {len(article_urls)}")
    print(f"   Analisaremos uma amostra representativa...\n")
    
    # Usa primeiros 50 artigos (representativo)
    sample_size = min(50, len(article_urls))
    article_urls = article_urls[:sample_size]
    
    auditor = SEOAuditor()
    results = []
    
    print(f"🔄 Analisando {sample_size} artigos...\n")
    print("-" * 90)
    
    for i, url in enumerate(article_urls, 1):
        print(f"[{i}/{sample_size}] Analisando: {url.split('/')[-1][:40]:40}...", end=' ', flush=True)
        
        result = auditor.analyze_page(url)
        results.append(result)
        
        if 'error' in result:
            print(f"❌ Erro")
        else:
            print(f"{auditor.categorize_score(result['score'])}")
        
        time.sleep(0.5)  # Respeita servidor
    
    print("-" * 90)
    
    # Estatísticas
    valid_results = [r for r in results if 'error' not in r]
    scores = [r['score'] for r in valid_results]
    
    if scores:
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"  Artigos analisados: {len(valid_results)}")
        print(f"  Score médio: {avg_score:.1f}/100")
        print(f"  Score mínimo: {min_score}/100")
        print(f"  Score máximo: {max_score}/100")
        
        # Contagem de problemas
        print(f"\n⚠️  PROBLEMAS MAIS COMUNS:")
        issue_counter = defaultdict(int)
        for result in valid_results:
            for issue in result.get('issues', []):
                # Normaliza issue
                issue_type = issue.split(':')[0]
                issue_counter[issue_type] += 1
        
        for issue, count in sorted(issue_counter.items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / len(valid_results)) * 100
            print(f"  {issue:35} : {count:3} ({pct:5.1f}%)")
        
        # Artigos piores
        print(f"\n🔴 ARTIGOS COM PIORES SCORES:")
        worst = sorted(valid_results, key=lambda x: x['score'])[:5]
        for i, result in enumerate(worst, 1):
            print(f"\n  {i}. {result['url'].split('/')[-1][:50]}")
            print(f"     Score: {result['score']}/100")
            print(f"     Problemas:")
            for issue in result['issues'][:3]:
                print(f"       - {issue}")
        
        # Artigos melhores
        print(f"\n🟢 ARTIGOS COM MELHORES SCORES:")
        best = sorted(valid_results, key=lambda x: x['score'], reverse=True)[:5]
        for i, result in enumerate(best, 1):
            print(f"\n  {i}. {result['url'].split('/')[-1][:50]}")
            print(f"     Score: {result['score']}/100")
        
        # Salva detalhes
        output_file = 'seo_audit_articles.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_analyzed': len(valid_results),
                'average_score': avg_score,
                'results': valid_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Relatório detalhado salvo em: {output_file}")
    
    elapsed = time.time() - auditor.start_time
    print(f"\n⏱️  Tempo total: {elapsed:.1f}s")
    
    print("\n" + "=" * 90 + "\n")

if __name__ == "__main__":
    main()
