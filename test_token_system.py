#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE COMPLETO DO SISTEMA DE TOKENS
Valida que NENHUM token é perdido e todos os mecanismos funcionam
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from app.token_guarantee import TokenGuarantee

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_token_guarantee():
    """Testa o sistema de garantia de tokens"""
    print("\n" + "=" * 80)
    print("🧪 TESTE 1: GARANTIA DE TOKENS")
    print("=" * 80)
    
    workspace = Path(__file__).parent
    guarantee = TokenGuarantee(workspace / "logs" / "tokens")
    
    # Teste 1.1: Registro normal
    logger.info("Teste 1.1: Registro normal")
    success = guarantee.log_guarantee(
        prompt_tokens=5000,
        completion_tokens=1000,
        operation="test_operation",
        source="test_module"
    )
    assert success, "❌ Falha ao registrar tokens"
    print("✅ Teste 1.1 passou")
    
    # Teste 1.2: Rejeição de tokens negativos
    logger.info("Teste 1.2: Rejeição de tokens negativos")
    success = guarantee.log_guarantee(
        prompt_tokens=-100,  # Negativo!
        completion_tokens=1000,
        operation="test_negative",
        source="test_module"
    )
    assert not success, "❌ Deveria rejeitar tokens negativos"
    print("✅ Teste 1.2 passou")
    
    # Teste 1.3: Verificar integridade
    logger.info("Teste 1.3: Verificar integridade dos logs")
    integrity = guarantee.verify_integrity()
    
    print(f"  Guarantee log existe: {integrity['guarantee_log_exists']}")
    print(f"  Tamanho do guarantee log: {integrity['guarantee_log_size']} bytes")
    print(f"  Linhas no audit log: {integrity['audit_log_lines']}")
    
    assert integrity['guarantee_log_exists'], "❌ Guarantee log não existe"
    assert integrity['status'] == 'OK', "❌ Status não OK"
    print("✅ Teste 1.3 passou")
    
    return True


def test_token_files():
    """Testa se os arquivos de tokens existem e têm conteúdo"""
    print("\n" + "=" * 80)
    print("🧪 TESTE 2: ARQUIVOS DE TOKENS")
    print("=" * 80)
    
    tokens_dir = Path(__file__).parent / "logs" / "tokens"
    
    # Teste 2.1: Diretório existe
    logger.info("Teste 2.1: Verificar diretório")
    assert tokens_dir.exists(), f"❌ Diretório {tokens_dir} não existe"
    print(f"✅ Teste 2.1 passou: {tokens_dir}")
    
    # Teste 2.2: Arquivos JSONL existem
    logger.info("Teste 2.2: Verificar arquivos JSONL")
    jsonl_files = list(tokens_dir.glob("tokens_*.jsonl"))
    assert len(jsonl_files) > 0, "❌ Nenhum arquivo JSONL encontrado"
    print(f"✅ Teste 2.2 passou: {len(jsonl_files)} arquivos JSONL encontrados")
    
    # Teste 2.3: Stats JSON existe
    logger.info("Teste 2.3: Verificar stats JSON")
    stats_file = tokens_dir / "token_stats.json"
    assert stats_file.exists(), "❌ Stats JSON não existe"
    
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    print(f"✅ Teste 2.3 passou: Stats JSON válido")
    print(f"   APIs encontradas: {list(stats.keys())}")
    
    # Teste 2.4: Garantia log existe
    logger.info("Teste 2.4: Verificar guarantee log")
    guarantee_file = tokens_dir / "token_guarantee.log"
    assert guarantee_file.exists(), "❌ Guarantee log não existe"
    print(f"✅ Teste 2.4 passou: Guarantee log existe")
    
    return True


def test_token_data():
    """Testa integridade dos dados de tokens"""
    print("\n" + "=" * 80)
    print("🧪 TESTE 3: INTEGRIDADE DOS DADOS")
    print("=" * 80)
    
    tokens_dir = Path(__file__).parent / "logs" / "tokens"
    stats_file = tokens_dir / "token_stats.json"
    
    # Teste 3.1: Carregar stats
    logger.info("Teste 3.1: Carregar stats")
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    print(f"✅ Teste 3.1 passou: Stats carregadas")
    
    # Teste 3.2: Validar estrutura de stats
    logger.info("Teste 3.2: Validar estrutura de stats")
    for api_type, models in stats.items():
        for model, data in models.items():
            required = [
                "total_prompt_tokens",
                "total_completion_tokens", 
                "total_requests"
            ]
            for field in required:
                assert field in data, f"❌ Campo {field} faltando em {api_type}/{model}"
    
    print(f"✅ Teste 3.2 passou: Estrutura de stats válida")
    
    # Teste 3.3: Calcular totais
    logger.info("Teste 3.3: Calcular totais")
    totals = {
        "prompt": 0,
        "completion": 0,
        "requests": 0
    }
    
    for api_type, models in stats.items():
        for model, data in models.items():
            totals["prompt"] += data.get("total_prompt_tokens", 0)
            totals["completion"] += data.get("total_completion_tokens", 0)
            totals["requests"] += data.get("total_requests", 0)
    
    print(f"✅ Teste 3.3 passou:")
    print(f"   Total de entrada: {totals['prompt']:,} tokens")
    print(f"   Total de saída: {totals['completion']:,} tokens")
    print(f"   Total de requisições: {totals['requests']:,}")
    print(f"   TOTAL GERAL: {totals['prompt'] + totals['completion']:,} tokens")
    
    return True


def test_reconciliation():
    """Testa reconciliação entre JSONL e Stats"""
    print("\n" + "=" * 80)
    print("🧪 TESTE 4: RECONCILIAÇÃO JSONL ↔ STATS")
    print("=" * 80)
    
    tokens_dir = Path(__file__).parent / "logs" / "tokens"
    
    # Teste 4.1: Somar tokens de JSONL
    logger.info("Teste 4.1: Somar tokens de JSONL")
    jsonl_total = 0
    jsonl_files = list(tokens_dir.glob("tokens_*.jsonl"))
    
    for jsonl_file in jsonl_files:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    jsonl_total += entry.get("total_tokens", 0)
    
    print(f"✅ Teste 4.1 passou: JSONL total = {jsonl_total:,} tokens")
    
    # Teste 4.2: Somar tokens de Stats
    logger.info("Teste 4.2: Somar tokens de Stats")
    stats_file = tokens_dir / "token_stats.json"
    stats_total = 0
    
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    for api_type, models in stats.items():
        for model, data in models.items():
            stats_total += data.get("total_tokens", 0)
    
    print(f"✅ Teste 4.2 passou: Stats total = {stats_total:,} tokens")
    
    # Teste 4.3: Reconciliação
    logger.info("Teste 4.3: Reconciliação")
    discrepancy = abs(jsonl_total - stats_total)
    
    if discrepancy == 0:
        print(f"✅ Teste 4.3 passou: PERFEITO! Sem discrepâncias ({discrepancy})")
    else:
        print(f"⚠️ Teste 4.3 AVISO: Discrepância de {discrepancy} tokens")
        print(f"   JSONL: {jsonl_total}, Stats: {stats_total}")
    
    return discrepancy == 0


def main():
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  🧪 TESTE COMPLETO DO SISTEMA DE TOKENS".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    try:
        # Executar testes
        results["tests"]["token_guarantee"] = test_token_guarantee()
        results["tests"]["token_files"] = test_token_files()
        results["tests"]["token_data"] = test_token_data()
        results["tests"]["reconciliation"] = test_reconciliation()
        
        # Resumo
        print("\n" + "=" * 80)
        print("📊 RESUMO DOS TESTES")
        print("=" * 80)
        
        all_passed = all(results["tests"].values())
        
        for test_name, passed in results["tests"].items():
            status = "✅ PASSOU" if passed else "❌ FALHOU"
            print(f"{status}: {test_name}")
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ CONCLUSÃO: TODOS OS TESTES PASSARAM!")
            print("✅ SISTEMA DE TOKENS 100% OPERACIONAL, ÍNTEGRO E GARANTIDO!")
            print("=" * 80)
            return 0
        else:
            print("❌ CONCLUSÃO: ALGUNS TESTES FALHARAM")
            print("=" * 80)
            return 1
    
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTES: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
