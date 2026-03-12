#!/usr/bin/env python3
"""
Script simplificado para mostrar detalhes do último post processado.
Mostra APENAS os dados que temos com certeza e podem ser correlacionados.
"""

import json
from pathlib import Path

def get_last_token_record():
    """Retorna o último registro de tokens."""
    log_file = Path("logs/tokens/tokens_2026-02-05.jsonl")
    
    if not log_file.exists():
        return None
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return None
    
    return json.loads(lines[-1])

def find_corresponding_json(timestamp):
    """Encontra o arquivo JSON mais próximo do timestamp."""
    debug_dir = Path("debug")
    json_files = sorted(debug_dir.glob("ai_response_batch_*.json"), reverse=True)
    
    if not json_files:
        return None
    
    # Retorna o mais recente
    return json_files[0]

def read_json_response(json_file):
    """Lê o arquivo JSON de resposta."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def format_html(html, max_length=300):
    """Formata HTML para visualização."""
    import re
    # Remover tags
    text = re.sub('<[^<]+?>', '', html)
    # Limpar
    text = text.replace('\n', ' ').replace('  ', ' ').strip()
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text

def main():
    print("\n" + "="*100)
    print("📊 DETALHES DO ÚLTIMO POST PROCESSADO")
    print("="*100 + "\n")
    
    # 1. Pegar registro de tokens
    token_record = get_last_token_record()
    if not token_record:
        print("❌ Nenhum registro de tokens encontrado!")
        return
    
    print(f"⏰ Timestamp do processamento:")
    print(f"   {token_record['timestamp']}\n")
    
    # 2. Encontrar JSON correspondente
    json_file = find_corresponding_json(token_record['timestamp'])
    json_data = None
    
    if json_file:
        print(f"📦 Arquivo JSON gerado:")
        print(f"   {json_file.name}\n")
        json_data = read_json_response(json_file)
    else:
        print("⚠️  Arquivo JSON não encontrado\n")
    
    # 3. Extrair dados do post
    print("="*100)
    print("📝 DADOS DO POST GERADO")
    print("="*100 + "\n")
    
    if json_data:
        # Se é um array de resultados
        if isinstance(json_data, dict) and 'resultados' in json_data:
            post = json_data['resultados'][0] if json_data['resultados'] else {}
        else:
            post = json_data
        
        print(f"📌 Título final:")
        print(f"   {post.get('titulo_final', 'N/A')}\n")
        
        print(f"🔗 Slug (URL amigável):")
        print(f"   {post.get('slug', 'N/A')}\n")
        
        print(f"📂 Categorias:")
        cats = [c.get('nome', 'N/A') for c in post.get('categorias', [])]
        print(f"   {', '.join(cats)}\n")
        
        print(f"🏷️  Tags:")
        tags = post.get('tags_sugeridas', [])
        print(f"   {', '.join(tags[:8])}\n")
        
        print(f"📄 Descrição para Meta:")
        print(f"   {post.get('meta_description', 'N/A')}\n")
        
        print(f"📖 Conteúdo (primeiros 300 caracteres):")
        print("   " + "-"*96)
        content_preview = format_html(post.get('conteudo_final', 'N/A'))
        # Quebrar em linhas de 90 caracteres
        for i in range(0, len(content_preview), 90):
            print(f"   {content_preview[i:i+90]}")
        print("   " + "-"*96 + "\n")
    else:
        print("⚠️  Não consegui ler o JSON\n")
    
    print("="*100)
    print("⚡ CONSUMO DE TOKENS (DADOS REAIS)")
    print("="*100 + "\n")
    
    entrada = token_record.get('prompt_tokens', 0)
    saida = token_record.get('completion_tokens', 0)
    total = entrada + saida
    
    print(f"📥 Entrada (Prompt da IA):")
    print(f"   {entrada:,} tokens\n")
    
    print(f"📤 Saída (Resposta da IA):")
    print(f"   {saida:,} tokens\n")
    
    print("─" * 100)
    print(f"✅ TOTAL DE TOKENS GASTOS:")
    print(f"   {total:,} tokens\n")
    
    # Calcular custos
    custo_entrada = entrada * (0.0375 / 1_000_000)
    custo_saida = saida * (0.15 / 1_000_000)
    custo_total = custo_entrada + custo_saida
    
    print("💰 CUSTO ESTIMADO (Gemini 2.5 Flash Lite):")
    print(f"   Entrada: {entrada:,} tokens × $0.0375 por 1M = ${custo_entrada:.8f}")
    print(f"   Saída:   {saida:,} tokens × $0.15 por 1M   = ${custo_saida:.8f}")
    print("   " + "─" * 94)
    print(f"   TOTAL CUSTO: ${custo_total:.8f}")
    
    if custo_total > 0:
        divisor = int(1 / custo_total)
        if divisor > 1:
            print(f"\n   (Equivalente a 1/{divisor}º de um centavo)")
    
    print()
    print("="*100)
    print("🔬 INFORMAÇÕES DA REQUISIÇÃO")
    print("="*100 + "\n")
    
    print(f"🤖 Modelo usado:")
    print(f"   {token_record.get('model', 'N/A')}\n")
    
    metadata = token_record.get('metadata', {})
    print(f"📦 Tipo de operação:")
    print(f"   {metadata.get('operation', 'N/A')}\n")
    
    print(f"📊 Tamanho do batch:")
    print(f"   {metadata.get('batch_size', 'N/A')} post(s)\n")
    
    print(f"📋 API:")
    print(f"   {token_record.get('api', 'N/A')}\n")
    
    print("ℹ️  Observação:")
    print("   O prompt completo NÃO é armazenado (seria muito grande)")
    print("   Mas foi enviado para Gemini baseado no template em 'app/prompt.txt'")
    print()
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
