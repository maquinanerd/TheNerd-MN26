#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

conn = sqlite3.connect('data/app.db')
c = conn.cursor()

# Check seen_articles table
print("Tabela: seen_articles")
c.execute("PRAGMA table_info(seen_articles)")
for row in c.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\nTabela: posts")
c.execute("PRAGMA table_info(posts)")
for row in c.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\nTabela: failures")
c.execute("PRAGMA table_info(failures)")
for row in c.fetchall():
    print(f"  {row[1]}: {row[2]}")

# Count records
print("\nRegistros:")
c.execute("SELECT COUNT(*) FROM seen_articles")
print(f"  seen_articles: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM posts")
print(f"  posts: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM failures")
print(f"  failures: {c.fetchone()[0]}")

# Sample seen_articles
print("\nSample seen_articles (primeiros 2):")
c.execute("SELECT id, title, content_len FROM seen_articles LIMIT 2")
for row in c.fetchall():
    print(f"  {row}")

conn.close()
