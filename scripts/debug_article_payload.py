#!/usr/bin/env python3
"""Debug para ver o conteúdo exato de um post"""

import os
import json
from dotenv import load_dotenv
from app.store import Database
from app.html_utils import html_to_gutenberg_blocks

load_dotenv()

# Conectar ao banco e pegar um artigo recente
db = Database()

# Pegar o artigo mais recente 
query = """
    SELECT id, title, content_html FROM articles 
    ORDER BY id DESC 
    LIMIT 1
"""

cursor = db.conn.cursor()
cursor.execute(query)
article = cursor.fetchone()

if article:
    article_id, title, content_html = article
    
    print("=" * 80)
    print(f"ARTIGO ID: {article_id}")
    print(f"TÍTULO: {title}")
    print("=" * 80)
    
    print("\n📝 CONTEÚDO HTML (primeiros 500 chars):")
    print(content_html[:500])
    
    print("\n\n🔄 CONVERTENDO PARA GUTENBERG...")
    gutenberg_content = html_to_gutenberg_blocks(content_html)
    
    print("\n✅ CONTEÚDO GUTENBERG (primeiros 800 chars):")
    print(gutenberg_content[:800])
    
    # Simular payload
    payload = {
        'title': title,
        'content': gutenberg_content,
        'categories': [20],
        'tags': [100],
        'featured_media': 12345,
    }
    
    payload_json = json.dumps(payload)
    payload_size = len(payload_json)
    
    print(f"\n\n📊 ANÁLISE DO PAYLOAD:")
    print(f"   Tamanho total: {payload_size} bytes ({payload_size/1024:.2f} KB)")
    print(f"   Tamanho do conteúdo: {len(gutenberg_content)} chars")
    print(f"   Limite: 30KB ({30000} bytes)")
    
    if payload_size > 30000:
        print(f"   ❌ EXCEDE o limite!")
    else:
        print(f"   ✅ Dentro do limite ({(payload_size/30000)*100:.1f}%)")
    
    # Salvar payload em arquivo para inspeção
    with open('debug_payload.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n💾 Payload salvo em: debug_payload.json")
    
else:
    print("❌ Nenhum artigo encontrado")

db.close()
