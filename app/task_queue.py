# app/queue.py
from collections import deque

class ArticleQueue:
    def __init__(self):
        self.q = deque()
    def push(self, item):
        self.q.append(item)
    def push_many(self, items):
        self.q.extend(items)
    def pop(self):
        return self.q.popleft() if self.q else None
    def __len__(self):
        return len(self.q)
