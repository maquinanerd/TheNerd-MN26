#!/usr/bin/env python3
"""Analisa o ciclo de postagem executado"""
import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path('data/app.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print('\n' + '=' * 80)
print('RELATORIO DO CICLO DE POSTAGEM EXECUTADO')
print('=' * 80)

# Obter estrutura das tabelas
print('\nESTRUTURA DO BANCO DE DADOS:')
print('-' * 80)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    print(f'\n{table_name}:')
    for col in columns:
        print(f'  - {col[1]} ({col[2]})')

# Estatísticas gerais
print('\n' + '=' * 80)
print('ESTATÍSTICAS GERAIS:')
print('-' * 80)

try:
    cursor.execute('SELECT COUNT(*) FROM seen_articles')
    seen = cursor.fetchone()[0]
    print(f'Total de artigos vistos: {seen}')
except Exception as e:
    print(f'Erro ao contar artigos vistos: {e}')

try:
    cursor.execute('SELECT COUNT(*) FROM posts')
    published = cursor.fetchone()[0]
    print(f'Total de posts publicados: {published}')
except Exception as e:
    print(f'Erro ao contar posts: {e}')

try:
    cursor.execute('SELECT COUNT(*) FROM failures')
    failures = cursor.fetchone()[0]
    print(f'Total de falhas: {failures}')
except Exception as e:
    print(f'Erro ao contar falhas: {e}')

# Últimos artigos processados
print('\n' + '=' * 80)
print('ÚLTIMOS ARTIGOS PROCESSADOS:')
print('-' * 80)

try:
    cursor.execute('''
        SELECT id, source_id, external_id, inserted_at 
        FROM seen_articles 
        ORDER BY inserted_at DESC 
        LIMIT 10
    ''')
    articles = cursor.fetchall()
    for i, art in enumerate(articles, 1):
        print(f'{i}. ID: {art[0]}, Fonte: {art[1]}, Data: {art[3]}')
except Exception as e:
    print(f'Erro ao recuperar artigos: {e}')

# Posts publicados
print('\n' + '=' * 80)
print('POSTS PUBLICADOS RECENTEMENTE:')
print('-' * 80)

try:
    cursor.execute('''
        SELECT p.id, p.seen_article_id, p.wp_post_id, p.created_at, sa.source_id
        FROM posts p
        LEFT JOIN seen_articles sa ON p.seen_article_id = sa.id
        ORDER BY p.created_at DESC 
        LIMIT 10
    ''')
    posts = cursor.fetchall()
    if posts:
        for i, post in enumerate(posts, 1):
            print(f'{i}. ID BD: {post[0]}, Fonte: {post[4]}, WP ID: {post[2]}, Data: {post[3]}')
    else:
        print('Nenhum post publicado encontrado.')
except Exception as e:
    print(f'Erro ao recuperar posts: {e}')

# Falhas
print('\n' + '=' * 80)
print('FALHAS RECENTES:')
print('-' * 80)

try:
    cursor.execute('''
        SELECT id, source_id, article_url, error_message, failed_at 
        FROM failures 
        ORDER BY failed_at DESC 
        LIMIT 5
    ''')
    errors = cursor.fetchall()
    if errors:
        for i, err in enumerate(errors, 1):
            print(f'{i}. Data: {err[4]}, Erro: {err[3][:80]}...')
    else:
        print('Nenhuma falha registrada.')
except Exception as e:
    print(f'Erro ao recuperar falhas: {e}')

conn.close()
print('\n' + '=' * 80)
