#!/usr/bin/env python3
"""
Teste rápido da chave de API fornecida
"""
import google.generativeai as genai

# Chave fornecida pelo usuário
API_KEY = "AIzaSyCvbX6nkhzc4Yp_GqAsS6ejtNuat89yTUk"

print("="*80)
print("TESTE DE VALIDAÇÃO DE CHAVE API GEMINI")
print("="*80)

print(f"\n✓ Chave: {API_KEY[:15]}...{API_KEY[-4:]}")
print(f"✓ Começa com AIza: {API_KEY.startswith('AIza')}")

print("\n Configurando chave...")
try:
    genai.configure(api_key=API_KEY)
    print("✓ Chave configurada com sucesso")
except Exception as e:
    print(f"✗ Erro ao configurar chave: {e}")
    exit(1)

print("\n Tentando gerar conteúdo com modelo gemini-2.5-flash-lite...")
try:
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    response = model.generate_content("Olá, você consegue responder?")
    print(f"✓ Sucesso! Resposta: {response.text[:100]}...")
except Exception as e:
    print(f"✗ Erro ao gerar conteúdo: {e}")
    print(f"  Tipo: {type(e).__name__}")
    exit(1)

print("\n" + "="*80)
print("✅ CHAVE É VÁLIDA E FUNCIONA!")
print("="*80)
