#!/usr/bin/env python3
"""
Script para mostrar quantos tokens foram gastos no último post processado.
"""

import json
from pathlib import Path
from datetime import datetime

def main():
    # Ler último registro
    log_file = Path("logs/tokens/tokens_2026-02-05.jsonl")
    
    if not log_file.exists():
        print("❌ Nenhum arquivo de log encontrado. Processe um post primeiro!")
        return
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        print("❌ Arquivo de log vazio. Processe um post primeiro!")
        return
    
    last_entry = json.loads(lines[-1])
    
    # Calcular custos (preços gemini-2.5-flash-lite)
    custo_entrada = last_entry['prompt_tokens'] * (0.0375 / 1_000_000)
    custo_saida = last_entry['completion_tokens'] * (0.15 / 1_000_000)
    custo_total = custo_entrada + custo_saida
    
    # Exibir
    print("\n" + "="*80)
    print("📊 CONSUMO DE TOKENS - ÚLTIMO POST")
    print("="*80)
    print()
    print(f"⏰ Timestamp:              {last_entry['timestamp']}")
    print()
    print(f"📥 ENTRADA (Prompt):       {last_entry['prompt_tokens']:,} tokens")
    print(f"📤 SAÍDA (Resposta):       {last_entry['completion_tokens']:,} tokens")
    print("-" * 80)
    print(f"✅ TOTAL:                  {last_entry['prompt_tokens'] + last_entry['completion_tokens']:,} tokens")
    print()
    print(f"🤖 Modelo:                 {last_entry.get('model', 'N/A')}")
    print(f"📦 Tipo de operação:       {last_entry.get('metadata', {}).get('operation', 'N/A')}")
    print(f"🔋 Status:                 {last_entry.get('status', 'N/A')}")
    print()
    print("-" * 80)
    print("💰 CUSTO ESTIMADO (gemini-2.5-flash-lite):")
    print(f"   Entrada:  {last_entry['prompt_tokens']:,} × $0.0375/1M = ${custo_entrada:.8f}")
    print(f"   Saída:    {last_entry['completion_tokens']:,} × $0.15/1M  = ${custo_saida:.8f}")
    print("   " + "-" * 70)
    print(f"   Total:                                    ${custo_total:.8f}")
    print()
    if custo_total > 0:
        print(f"   (Aproximadamente 1/{int(1/custo_total):.0f} de um centavo)")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
