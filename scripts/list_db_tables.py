#!/usr/bin/env python3
import sqlite3

db = sqlite3.connect('data/app.db')
cursor = db.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print('Tabelas no banco:')
for table in tables:
    print(f'  - {table[0]}')

db.close()
