#!/usr/bin/env python3
import urllib.parse

INPUT = 'posts_2025-10-30.txt'

lines = []
with open(INPUT, 'r', encoding='utf-8') as f:
    for line in f:
        line=line.strip()
        if not line:
            continue
        url = line.split('\t')[0]
        lines.append(url)

len_lines = len(lines)
print(f'Total URLs: {len_lines}')

non_article_patterns = ['/category/', '/tag/', '/author/', '/page/', '/?s=', '/feed']

articles = []
others = []
for u in lines:
    path = urllib.parse.urlparse(u).path.lower()
    if any(p in path for p in non_article_patterns):
        others.append(u)
    else:
        articles.append(u)

print(f'Articles (heuristic): {len(articles)}')
print(f'Others: {len(others)}')

# Save samples and first 100 titles by fetching
import requests
from bs4 import BeautifulSoup
HEADERS={'User-Agent':'Mozilla/5.0'}

sampled = articles[:100]
results = []
for u in sampled:
    try:
        r = requests.get(u, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        title = soup.find('title')
        t = title.get_text(strip=True) if title else ''
        results.append((u, t))
    except Exception as e:
        results.append((u, f'ERROR: {e}'))

with open('posts_2025_10_30_samples.txt','w',encoding='utf-8') as f:
    for u,t in results:
        f.write(u + '\t' + t + '\n')

print('Saved first 100 titles to posts_2025_10_30_samples.txt')
