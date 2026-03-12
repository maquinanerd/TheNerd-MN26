#!/usr/bin/env python3
"""
Exemplo de integração do TokenTracker com a API Gemini
"""

import sys
from pathlib import Path

# Adicionar diretório do app ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.token_tracker import get_tracker, log_tokens

def exemplo_uso_simples():
    """Exemplo simples de uso"""
    print("📌 Exemplo 1: Uso Simples do TokenTracker\n")
    
    # Registrar uma chamada bem-sucedida
    log_tokens(
        prompt_tokens=150,
        completion_tokens=320,
        api_type="gemini",
        model="gemini-2.5-flash",
        api_key_suffix="abc123",
        success=True
    )
    print("✅ Log registrado: 150 tokens entrada + 320 tokens saída\n")
    
    # Registrar outra chamada
    log_tokens(
        prompt_tokens=200,
        completion_tokens=450,
        api_type="gemini",
        model="gemini-2.5-flash",
        api_key_suffix="def456",
        success=True
    )
    print("✅ Log registrado: 200 tokens entrada + 450 tokens saída\n")

def exemplo_uso_com_erro():
    """Exemplo com registro de erro"""
    print("📌 Exemplo 2: Registrando Falhas\n")
    
    log_tokens(
        prompt_tokens=100,
        completion_tokens=0,
        api_type="gemini",
        model="gemini-2.5-flash",
        api_key_suffix="xyz789",
        success=False,
        error_message="Quota excedida (429)"
    )
    print("✅ Log de falha registrado\n")

def exemplo_com_metadata():
    """Exemplo com metadata adicional"""
    print("📌 Exemplo 3: Com Metadados\n")
    
    log_tokens(
        prompt_tokens=250,
        completion_tokens=500,
        api_type="gemini",
        model="gemini-2.5-flash-lite",
        api_key_suffix="meta001",
        success=True,
        metadata={
            "request_type": "article_generation",
            "article_title": "Exemplo de Artigo",
            "processing_time_ms": 2450
        }
    )
    print("✅ Log com metadata registrado\n")

def exemplo_visualizar_stats():
    """Exemplo de visualização de estatísticas"""
    print("📌 Exemplo 4: Visualizar Estatísticas\n")
    
    tracker = get_tracker()
    tracker.print_summary()

def main():
    """Menu de exemplos"""
    print("\n" + "="*80)
    print("🎓 EXEMPLOS DE USO DO TOKEN TRACKER")
    print("="*80)
    
    print("\n1. Registrando tokens simples")
    exemplo_uso_simples()
    
    print("2. Registrando erros")
    exemplo_uso_com_erro()
    
    print("3. Registrando com metadados")
    exemplo_com_metadata()
    
    print("4. Visualizando estatísticas")
    exemplo_visualizar_stats()
    
    print("\n" + "="*80)
    print("✅ Exemplos concluídos!")
    print("\nLogs foram salvos em: logs/tokens/")
    print("\nPara visualizar em tempo real, execute:")
    print("  python token_logs_viewer.py")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
