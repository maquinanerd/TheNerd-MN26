#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google News SEO Validator
Valida news-sitemap.xml e gera relatório de otimização
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlparse
import sys
import io

# Fix encoding no Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def validate_news_sitemap(sitemap_url: str = "https://www.maquinanerd.com.br/news-sitemap.xml"):
    """
    Valida o news-sitemap.xml e gera relatório detalhado
    """
    
    print("=" * 100)
    print("[GOOGLE NEWS SITEMAP VALIDATOR v1.0]")
    print("=" * 100)
    print(f"\nURL: {sitemap_url}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. FETCH do sitemap
    print("[1/5] 📥 Buscando news-sitemap.xml...")
    try:
        response = requests.get(sitemap_url, timeout=15)
        response.raise_for_status()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Size: {len(response.content) / 1024:.2f} KB")
    except requests.RequestException as e:
        print(f"❌ ERRO ao buscar sitemap: {e}")
        return None
    
    # 2. PARSE XML
    print("\n[2/5] 🔨 Analisando XML...")
    try:
        root = ET.fromstring(response.content)
        ns = {'news': 'http://www.google.com/schemas/sitemap-news/0.9',
              'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = root.findall('.//sitemap:url', ns)
        print(f"✅ URLs encontradas: {len(urls)}")
    except ET.ParseError as e:
        print(f"❌ ERRO ao parsear XML: {e}")
        return None
    
    # 3. VALIDAR ESTRUTURA
    print("\n[3/5] ✔️  Validando estrutura...")
    
    stats = {
        'total_urls': len(urls),
        'with_keywords': 0,
        'with_access': 0,
        'with_image': 0,
        'with_title': 0,
        'with_publication_date': 0,
        'recent_posts': 0,  # Últimos 30 dias
        'errors': [],
        'warnings': [],
        'details': []
    }
    
    cutoff_date = datetime.now() - timedelta(days=30)
    
    for idx, url_elem in enumerate(urls, 1):
        url_loc = url_elem.find('sitemap:loc', ns)
        news_elem = url_elem.find('news:news', ns)
        
        if url_loc is None:
            stats['errors'].append(f"URL #{idx}: Falta <loc>")
            continue
        
        url_text = url_loc.text
        post_number = idx
        
        if news_elem is None:
            stats['errors'].append(f"Falta <news:news> em: {url_text}")
            continue
        
        # Subtítulos
        title = news_elem.find('news:title', ns)
        pub_date_elem = news_elem.find('news:publication_date', ns)
        keywords = news_elem.find('news:keywords', ns)
        access = news_elem.find('news:access', ns)
        image = news_elem.find('news:image', ns)
        
        # Contar campos
        if title is not None and title.text:
            stats['with_title'] += 1
        else:
            stats['warnings'].append(f"#{post_number}: Falta ou vazio <news:title>")
        
        if pub_date_elem is not None and pub_date_elem.text:
            stats['with_publication_date'] += 1
            try:
                # Parse ISO format com timezone
                date_str = pub_date_elem.text.replace('Z', '+00:00')
                pub_date = datetime.fromisoformat(date_str)
                # Fazer comparação robusta
                now = datetime.now()
                if pub_date.replace(tzinfo=None) > cutoff_date:
                    stats['recent_posts'] += 1
            except ValueError:
                stats['warnings'].append(f"#{post_number}: Data inválida: {pub_date_elem.text}")
        
        if keywords is not None and keywords.text:
            stats['with_keywords'] += 1
            keyword_count = len(keywords.text.split(','))
            if keyword_count > 10:
                stats['warnings'].append(f"#{post_number}: Muitas keywords ({keyword_count} > 10)")
        else:
            stats['errors'].append(f"#{post_number}: ❌ FALTA <news:keywords>")
        
        if access is not None and access.text:
            stats['with_access'] += 1
        else:
            stats['warnings'].append(f"#{post_number}: Falta <news:access>")
        
        if image is not None:
            stats['with_image'] += 1
        else:
            stats['warnings'].append(f"#{post_number}: Falta <news:image>")
        
        # Detalhes do post
        stats['details'].append({
            'position': idx,
            'url': url_text,
            'title': title.text if title is not None else "N/A",
            'has_keywords': keywords is not None,
            'keywords': keywords.text[:50] if keywords is not None and keywords.text else "N/A",
            'has_image': image is not None,
            'published': pub_date_elem.text if pub_date_elem is not None else "N/A"
        })
    
    # 4. RELATÓRIO
    print("\n[4/5] 📊 Compilando relatório...")
    
    print("\n" + "="*100)
    print("📈 RESUMO DE OTIMIZAÇÃO")
    print("="*100)
    
    # Score de keywords (CRÍTICO)
    keyword_compliance = (stats['with_keywords'] / stats['total_urls'] * 100) if stats['total_urls'] > 0 else 0
    print(f"\n🔑 Keywords (CRÍTICO):")
    print(f"   URLs com <news:keywords>: {stats['with_keywords']}/{stats['total_urls']} ({keyword_compliance:.1f}%)")
    if keyword_compliance == 100:
        print(f"   Status: ✅ PERFEITO")
    elif keyword_compliance >= 80:
        print(f"   Status: ⚠️  BOM (mas {stats['total_urls'] - stats['with_keywords']} ainda faltam)")
    else:
        print(f"   Status: ❌ CRÍTICO - Implementar WPCode snippet!")
    
    # Score de images
    image_compliance = (stats['with_image'] / stats['total_urls'] * 100) if stats['total_urls'] > 0 else 0
    print(f"\n🖼️  Imagens:")
    print(f"   URLs com <news:image>: {stats['with_image']}/{stats['total_urls']} ({image_compliance:.1f}%)")
    print(f"   Status: {'✅ EXCELENTE' if image_compliance == 100 else '⚠️  BOM' if image_compliance >= 80 else '❌ MELHORAR'}")
    
    # Score de access
    access_compliance = (stats['with_access'] / stats['total_urls'] * 100) if stats['total_urls'] > 0 else 0
    print(f"\n🔓 Access Type:")
    print(f"   URLs com <news:access>: {stats['with_access']}/{stats['total_urls']} ({access_compliance:.1f}%)")
    
    # Posts recentes
    print(f"\n📅 Posts Recentes (< 30 dias):")
    print(f"   Contagem: {stats['recent_posts']}/{stats['total_urls']}")
    print(f"   Status: {'✅ FRESH' if stats['recent_posts'] > 0 else '⚠️  Publicar mais frequentemente'}")
    
    # OVERALL SCORE
    overall_score = (keyword_compliance * 0.5 + image_compliance * 0.3 + access_compliance * 0.2)
    print(f"\n🏆 SCORE GERAL DO NEWS SEO: {overall_score:.1f}%")
    if overall_score >= 90:
        print("   Avaliação: ✅ EXCELENTE - Pronto para Google News!")
    elif overall_score >= 75:
        print("   Avaliação: ⚠️  BOM - Algumas melhorias recomendadas")
    else:
        print("   Avaliação: ❌ PRECISA DE AÇÃO - Implementar WPCode snippet")
    
    # 5. ERROS E AVISOS
    if stats['errors'] or stats['warnings']:
        print("\n" + "="*100)
        print("⚠️  ERROS & AVISOS")
        print("="*100)
        
        if stats['errors']:
            print(f"\n❌ ERROS ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:  # Mostrar apenas 10
                print(f"   • {error}")
            if len(stats['errors']) > 10:
                print(f"   ... e {len(stats['errors']) - 10} erros mais")
        
        if stats['warnings']:
            print(f"\n⚠️  AVISOS ({len(stats['warnings'])}):")
            for warning in stats['warnings'][:10]:
                print(f"   • {warning}")
            if len(stats['warnings']) > 10:
                print(f"   ... e {len(stats['warnings']) - 10} avisos mais")
    
    # Detalhes dos primeiros 3 posts
    print("\n" + "="*100)
    print("📄 AMOSTRA DOS PRIMEIROS 3 POSTS")
    print("="*100)
    
    for detail in stats['details'][:3]:
        print(f"\n#{detail['position']}: {detail['title'][:60]}...")
        print(f"   URL: {detail['url']}")
        print(f"   Keywords: {'✅' if detail['has_keywords'] else '❌'} {detail['keywords']}")
        print(f"   Image: {'✅' if detail['has_image'] else '❌'}")
        print(f"   Published: {detail['published']}")
    
    # Instruções de ação
    print("\n" + "="*100)
    print("🚀 PRÓXIMAS AÇÕES")
    print("="*100)
    
    actions = []
    if keyword_compliance < 100:
        actions.append("1. ❌ Instalar WPCode snippet (CRÍTICO)")
        actions.append("   → Arquivo: WPCODE_NEWS_SITEMAP_ENHANCEMENT.php")
        actions.append("   → WordPress → WPCode → Add Snippet")
    
    if image_compliance < 100:
        actions.append("2. ⚠️  Garantir Featured Image em todos posts")
        actions.append("   → Verificar posts sem imagem destacada")
    
    actions.append("3. ✅ Enviar News Sitemap ao Google News Publisher Center")
    actions.append("   → https://newscenter.google.com/")
    actions.append("   → Adicionar: https://www.maquinanerd.com.br/news-sitemap.xml")
    
    actions.append("4. ✅ Submeter ao Google Search Console")
    actions.append("   → https://search.google.com/search-console/")
    actions.append("   → Sitemaps → Adicionar: news-sitemap.xml")
    
    actions.append("5. 📊 Monitorar Performance")
    actions.append("   → Google News Publisher Center → Analytics (48-72h)")
    actions.append("   → Google Search Console → Performance → Filter by 'News'")
    
    for action in actions:
        print(f"   {action}")
    
    # SALVAR RELATÓRIO JSON
    report_file = f"reports/google_news_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("reports").mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'sitemap_url': sitemap_url,
            'overall_score': overall_score,
            'stats': stats,
            'recommendations': actions
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório salvo: {report_file}")
    print("\n" + "="*100)
    print(f"✅ Validação concluída em {datetime.now().strftime('%H:%M:%S')}")
    print("="*100)
    
    return stats

if __name__ == "__main__":
    validate_news_sitemap()
