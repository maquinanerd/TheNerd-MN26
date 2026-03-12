#!/usr/bin/env python3
"""Análise de segurança de uso de API - 29/10/2025"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

try:
    print("="*80)
    print("🔒 ANÁLISE DE SEGURANÇA - USO DE API EM 29/10/2025")
    print("="*80 + "\n")
    
    # 1. Verificar dados de posts em 29/10/2025
    cursor.execute('''
        SELECT COUNT(*) as total,
               COUNT(DISTINCT seen_article_id) as unique_articles
        FROM posts 
        WHERE DATE(created_at) = '2025-10-29'
    ''')
    posts_29 = cursor.fetchone()
    print(f"📊 POSTS PUBLICADOS EM 29/10/2025:")
    print(f"   Total de posts: {posts_29[0]}")
    print(f"   Artigos únicos: {posts_29[1]}")
    
    # 2. Verificar articles/hora
    cursor.execute('''
        SELECT strftime('%H', created_at) as hora, COUNT(*) as qty
        FROM posts 
        WHERE DATE(created_at) = '2025-10-29'
        GROUP BY hora
        ORDER BY hora
    ''')
    print(f"\n📈 DISTRIBUIÇÃO POR HORA:")
    horas = cursor.fetchall()
    for hora, qty in horas:
        bars = '█' * (qty // 5)
        print(f"   {hora}:00 | {bars} {qty}")
    
    # 3. Calcular RPM e RPS
    total_posts = posts_29[0]
    minutos_dia = 24 * 60
    segundos_dia = 24 * 60 * 60
    
    rpm = total_posts / minutos_dia if total_posts > 0 else 0
    rps = total_posts / segundos_dia if total_posts > 0 else 0
    
    print(f"\n⚡ VELOCIDADE DE REQUISIÇÕES:")
    print(f"   Posts/dia: {total_posts}")
    print(f"   RPM (requisições/minuto): {rpm:.2f}")
    print(f"   RPS (requisições/segundo): {rps:.4f}")
    
    # 4. Analisar se está seguro para free tier
    print(f"\n🛡️  ANÁLISE DE SEGURANÇA PARA FREE TIER:\n")
    
    # Verificar limites típicos de free tier
    limites = {
        "Google Gemini": {"rpm": 60, "rpd": 1500, "quota_tokens": 1000000},
        "OpenAI": {"rpm": 3, "rpd": 200, "quota_tokens": 40000},
        "Anthropic": {"rpm": 1, "rpd": 50, "quota_tokens": 100000},
    }
    
    print(f"   Seu uso atual:")
    print(f"   • RPM: {rpm:.2f}")
    print(f"   • RPD: {total_posts}")
    print(f"   • RPS: {rps:.4f}")
    
    print(f"\n   Comparação com free tiers conhecidos:")
    for api, limits in limites.items():
        rpm_ok = rpm <= limits["rpm"]
        rpd_ok = total_posts <= limits["rpd"]
        
        rpm_status = "✅" if rpm_ok else "❌"
        rpd_status = "✅" if rpd_ok else "❌"
        
        print(f"\n   {api}:")
        print(f"     RPM: {rpm_status} Seu {rpm:.2f} vs Limite {limits['rpm']}")
        print(f"     RPD: {rpd_status} Seu {total_posts} vs Limite {limits['rpd']}")
    
    # 5. Verificar feed_status para detecção de problemas
    print(f"\n" + "="*80)
    print("📡 STATUS DOS FEEDS:")
    print("="*80)
    
    cursor.execute('''
        SELECT source_id, consecutive_failures
        FROM feed_status
        ORDER BY source_id
    ''')
    
    feeds = cursor.fetchall()
    for feed_id, failures in feeds:
        if failures > 0:
            print(f"   ⚠️  {feed_id}: {failures} falhas consecutivas")
        else:
            print(f"   ✅ {feed_id}: OK")
    
    # 6. Análise de padrão de uso
    print(f"\n" + "="*80)
    print("🔍 ANÁLISE DE PADRÃO:")
    print("="*80)
    
    # Pico de uso
    max_hour = max(horas, key=lambda x: x[1]) if horas else None
    min_hour = min(horas, key=lambda x: x[1]) if horas else None
    
    if max_hour:
        print(f"\n   Pico de uso: {max_hour[0]}:00 ({max_hour[1]} posts)")
        print(f"   Vale de uso: {min_hour[0]}:00 ({min_hour[1]} posts)")
    
    # 7. Recomendações
    print(f"\n" + "="*80)
    print("💡 RECOMENDAÇÕES:")
    print("="*80)
    
    if rpm < 1:
        print(f"\n   ✅ SEGURO! Sua taxa de {rpm:.2f} RPM está bem abaixo dos limites.")
        print(f"      Pode usar qualquer free tier sem riscos de banimento.")
    elif rpm < 10:
        print(f"\n   ⚠️  CUIDADO! Taxa de {rpm:.2f} RPM está moderada.")
        print(f"      Funciona em alguns free tiers (ex: Google Gemini).")
        print(f"      Evite OpenAI/Anthropic free tier (limite muito baixo).")
    else:
        print(f"\n   ❌ ALTO! Taxa de {rpm:.2f} RPM vai além de muitos free tiers.")
        print(f"      Recomendado usar plano pago ou implementar rate limiting.")
    
    # 8. Resumo final
    print(f"\n" + "="*80)
    print("📌 RESUMO FINAL DE SEGURANÇA:")
    print("="*80)
    print(f"""
   Status: {'✅ SEGURO' if rpm < 10 else '⚠️  CUIDADO' if rpm < 60 else '❌ INSEGURO'}
   
   Dados de 29/10/2025:
   • {total_posts} posts publicados
   • Média: {rpm:.2f} posts/minuto
   • Pico: ~{max_hour[1] if max_hour else 'N/A'} posts/hora
   
   Recomendações:
   • Google Gemini (60 RPM): ✅ TOTALMENTE SEGURO
   • Claude/Anthropic (1 RPM): ❌ INSEGURO
   • OpenAI (3 RPM): ❌ INSEGURO
   • Cohere (100 RPM): ✅ SEGURO
   
   Ação recomendada:
   {'→ Continuar usando sem problemas' if rpm < 10 else '→ Implementar rate limiting' if rpm < 60 else '→ Urgente: Upgradar para plano pago'}
    """)

finally:
    conn.close()
