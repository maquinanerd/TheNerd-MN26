#!/usr/bin/env python3
"""
Test script para verificar se as chaves de API estão sendo carregadas corretamente
e se estão trocando quando uma excede quota.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Carrega .env
load_dotenv(override=True)

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("🔍 TEST: Verificar Carregamento de Chaves de API Gemini")
print("="*80)

# 1. Verificar variáveis de ambiente
print("\n1️⃣  VARIÁVEIS DE AMBIENTE CARREGADAS:")
print("-" * 80)
found_keys = {}
for key, value in os.environ.items():
    if 'GEMINI' in key.upper() and value and str(value).startswith('AIza'):
        found_keys[key] = value
        print(f"   ✅ {key}: {value[:20]}...{value[-4:]}")

if not found_keys:
    print("   ❌ NENHUMA CHAVE ENCONTRADA!")
    sys.exit(1)

# 2. Testar carregamento da config
print("\n2️⃣  CARREGANDO CONFIG.PY:")
print("-" * 80)
try:
    from app.config import AI_API_KEYS
    print(f"   ✅ AI_API_KEYS carregado com sucesso!")
    print(f"   Total de chaves: {len(AI_API_KEYS)}")
    for idx, key in enumerate(AI_API_KEYS, 1):
        print(f"      Chave {idx}: {key[:20]}...{key[-4:]}")
except Exception as e:
    print(f"   ❌ Erro ao carregar config: {e}")
    sys.exit(1)

# 3. Testar AIClient
print("\n3️⃣  INICIALIZANDO AICLIENT:")
print("-" * 80)
try:
    from app.ai_client_gemini import AIClient
    client = AIClient(
        keys=AI_API_KEYS,
        min_interval_s=6,
        backoff_base=20,
        backoff_max=300
    )
    print(f"   ✅ AIClient inicializado com {len(AI_API_KEYS)} chaves")
except Exception as e:
    print(f"   ❌ Erro ao inicializar AIClient: {e}")
    sys.exit(1)

# 4. Testar geração de texto com primeira chave
print("\n4️⃣  TESTANDO GERAÇÃO COM PRIMEIRA CHAVE:")
print("-" * 80)
try:
    prompt = "Responda brevemente: qual é 2+2?"
    print(f"   📝 Prompt: {prompt}")
    result = client.generate_text(prompt)
    print(f"   ✅ Resultado: {result}")
except Exception as e:
    print(f"   ⚠️  Erro na geração (pode ser quota excedida): {e}")

# 5. Testar KeyPool
print("\n5️⃣  TESTANDO KEYPOOL (Rotação de Chaves):")
print("-" * 80)
print(f"   Total de slots no pool: {len(client.pool.slots)}")
print(f"   Testando next_ready() 3 vezes:")
for i in range(min(3, len(client.pool.slots))):
    slot = client.pool.next_ready()
    print(f"      Slot {i+1}: {slot.key[:20]}...{slot.key[-4:]} (cooldown_until={slot.cooldown_until})")

print("\n" + "="*80)
print("✅ TESTE CONCLUÍDO")
print("="*80 + "\n")
