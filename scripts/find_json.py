#!/usr/bin/env python3
"""
🔍 PROCURA JSON PELO SLUG OU TÍTULO

Use:
    python find_json.py "jogos-olimpicos-inverno"
    python find_json.py "Jogos Olímpicos"
"""

import sys
import json
from pathlib import Path

def find_json(search_term):
    """Find JSON file by slug, title, or keyword."""
    debug_dir = Path("debug")
    
    if not debug_dir.exists():
        print("❌ debug/ directory not found!")
        return
    
    json_files = sorted(debug_dir.glob("ai_response_batch_*.json"), reverse=True)
    
    if not json_files:
        print("❌ No JSON files found!")
        return
    
    results = []
    search_lower = search_term.lower()
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both single objects and arrays
            if isinstance(data, dict):
                if 'resultados' in data and data['resultados']:
                    items = data['resultados']
                else:
                    items = [data]
            else:
                items = [data] if isinstance(data, dict) else []
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                slug = item.get('slug', '').lower()
                title = item.get('titulo_final', '').lower()
                
                if search_lower in slug or search_lower in title:
                    results.append({
                        'file': json_file.name,
                        'slug': item.get('slug', 'N/A'),
                        'title': item.get('titulo_final', 'N/A')[:60],
                        'path': json_file
                    })
        
        except Exception as e:
            continue
    
    if not results:
        print(f"❌ Nenhum resultado para: '{search_term}'")
        return
    
    print(f"\n{'='*100}")
    print(f"✅ Encontrados {len(results)} arquivo(s) para '{search_term}'")
    print(f"{'='*100}\n")
    
    for idx, result in enumerate(results, 1):
        print(f"{idx}. {result['file']}")
        print(f"   Slug:   {result['slug']}")
        print(f"   Título: {result['title']}")
        print(f"   Path:   {result['path']}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python find_json.py '<termo_de_busca>'")
        print("\nExemplos:")
        print("  python find_json.py 'olimpicos'")
        print("  python find_json.py 'Filmes'")
        print("  python find_json.py 'jogos-olimpicos-inverno'")
        sys.exit(1)
    
    search_term = " ".join(sys.argv[1:])
    find_json(search_term)
