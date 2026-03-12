#!/usr/bin/env python3
"""
Reorganiza JSONs existentes para o novo padrão com slug.
Run: python reorganize_jsons.py
"""

import json
from pathlib import Path
import time
import re

def slugify(text):
    """Convert text to slug format."""
    text = text.lower().strip()
    text = re.sub(r'[ãõá]*', '', text)  # Remove common Portuguese chars
    text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars
    text = re.sub(r'[-\s]+', '-', text)  # Replace spaces and hyphens with single hyphen
    return text.strip('-')

def rename_existing_jsons():
    """Rename existing JSON files to include slug."""
    debug_dir = Path("debug")
    if not debug_dir.exists():
        print("❌ debug/ directory not found!")
        return
    
    json_files = list(debug_dir.glob("ai_response_batch_*.json"))
    
    if not json_files:
        print("✅ No JSON files to reorganize")
        return
    
    print(f"📁 Found {len(json_files)} JSON files to process\n")
    
    renamed_count = 0
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract slug from JSON
            if isinstance(data, dict):
                if 'resultados' in data and data['resultados']:
                    primeiro = data['resultados'][0]
                else:
                    primeiro = data
            else:
                primeiro = data if isinstance(data, dict) else {}
            
            slug = primeiro.get('slug', 'sem-slug')
            titulo = primeiro.get('titulo_final', 'untitled')
            
            # Check if already has slug in filename
            if slug in json_file.name:
                print(f"⏭️  Skip (já tem slug): {json_file.name}")
                continue
            
            # Generate new filename
            # Extract timestamp from old filename if possible
            match = re.search(r'(\d{8}-\d{6})', json_file.name)
            timestamp = match.group(1) if match else time.strftime("%Y%m%d-%H%M%S")
            
            new_filename = f"ai_response_batch_{slug}_{timestamp}.json"
            new_path = debug_dir / new_filename
            
            # Avoid duplicates
            counter = 1
            while new_path.exists():
                new_filename = f"ai_response_batch_{slug}_{timestamp}_v{counter}.json"
                new_path = debug_dir / new_filename
                counter += 1
            
            json_file.rename(new_path)
            print(f"✅ {json_file.name}")
            print(f"   → {new_filename}")
            print(f"   Title: {titulo[:60]}")
            print()
            renamed_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")
            continue
    
    print(f"\n{'='*70}")
    print(f"✅ CONCLUSÃO: {renamed_count}/{len(json_files)} arquivos reorganizados")
    print(f"{'='*70}")

if __name__ == "__main__":
    rename_existing_jsons()
