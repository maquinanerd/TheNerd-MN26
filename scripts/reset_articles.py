#!/usr/bin/env python3
"""
Script para resetar artigos do banco de dados.
Permite reprocessar os últimos artigos ingeridos.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path('data/app.db')

if not DB_PATH.exists():
    print(f"❌ Banco de dados não encontrado em {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Mostrar status atual
    cursor.execute('SELECT COUNT(*) FROM seen_articles')
    total = cursor.fetchone()[0]
    print(f"\n📊 Status atual:")
    print(f"   Total de artigos vistos: {total}")
    
    # Contar por status
    cursor.execute('SELECT status, COUNT(*) FROM seen_articles GROUP BY status')
    for status, count in cursor.fetchall():
        print(f"   • {status}: {count}")
    
    # Menu
    print("\n🎯 Opções:")
    print("   1 - Deletar TODOS os artigos (resetar completamente)")
    print("   2 - Resetar últimas 24 horas para NEW (reprocessar)")
    print("   3 - Resetar apenas FAILED para NEW (reprocessar falhas)")
    print("   4 - Cancelar")
    
    choice = input("\nEscolha uma opção (1-4): ").strip()
    
    if choice == '1':
        confirm = input("⚠️  Deseja DELETAR todos os artigos? (S/N): ").strip().upper()
        if confirm == 'S':
            cursor.execute('DELETE FROM seen_articles')
            cursor.execute('DELETE FROM posts')
            conn.commit()
            print("✅ Todos os artigos deletados com sucesso!")
    
    elif choice == '2':
        confirm = input("⚠️  Resetar artigos das últimas 24h para NEW? (S/N): ").strip().upper()
        if confirm == 'S':
            cutoff = datetime.now() - timedelta(hours=24)
            cursor.execute(
                'UPDATE seen_articles SET status = "NEW" WHERE inserted_at > ? AND status IN ("PUBLISHED", "FAILED")',
                (cutoff,)
            )
            count = cursor.rowcount
            conn.commit()
            print(f"✅ {count} artigos resetados para NEW!")
    
    elif choice == '3':
        confirm = input("⚠️  Resetar artigos FAILED para NEW? (S/N): ").strip().upper()
        if confirm == 'S':
            cursor.execute('UPDATE seen_articles SET status = "NEW" WHERE status = "FAILED"')
            count = cursor.rowcount
            conn.commit()
            print(f"✅ {count} artigos FAILED resetados para NEW!")
    
    elif choice == '4':
        print("❌ Cancelado.")
    
    else:
        print("❌ Opção inválida!")

finally:
    conn.close()
    print("\n✨ Banco de dados atualizado. Execute o pipeline novamente:\n")
    print("   python -m app.main\n")
