import sqlite3

try:
    conn = sqlite3.connect("app/store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tabelas no banco:")
    for table in tables:
        print(f"  - {table[0]}")
    conn.close()
except Exception as e:
    print(f"Erro: {e}")
