#!/usr/bin/env python3
import sqlite3
import time
from datetime import datetime

conn = sqlite3.connect('data/app.db')
c = conn.cursor()

print("="*80)
print("MONITORAMENTO DE POSTS EM TEMPO REAL")
print("="*80)

while True:
    c.execute('SELECT COUNT(*) FROM posts WHERE created_at > datetime("now", "-1 hour")')
    count_1h = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM posts WHERE created_at > datetime("now", "-1 day")')
    count_1d = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM posts')
    total = c.fetchone()[0]
    
    c.execute('SELECT MAX(created_at) FROM posts')
    last = c.fetchone()[0]
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
    print(f"  Última hora: {count_1h} posts")
    print(f"  Último dia: {count_1d} posts")
    print(f"  Total: {total} posts")
    print(f"  Último: {last}")
    
    time.sleep(5)
