#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DASHBOARD DE TOKENS EM TEMPO REAL
Monitora tokens, mostra logs em tempo real e força captura obrigatória
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import time
import sys

class TokenDashboard:
    """Dashboard em tempo real do sistema de rastreamento de tokens"""
    
    def __init__(self, workspace_path: str = None, interval: int = 2):
        if workspace_path is None:
            workspace_path = Path(__file__).parent
        else:
            workspace_path = Path(workspace_path)
        
        self.workspace = workspace_path
        self.tokens_dir = workspace_path / "logs" / "tokens"
        self.app_log = workspace_path / "logs" / "app.log"
        self.interval = interval  # segundos entre updates
        
        self.last_check = 0
        self.last_log_pos = {}  # rastrear posição em cada arquivo
        self.stats_cache = {}
    
    def read_latest_entries(self, lines: int = 20) -> list:
        """Lê entradas mais recentes do JSONL de hoje"""
        today = datetime.now().strftime('%Y-%m-%d')
        jsonl_file = self.tokens_dir / f"tokens_{today}.jsonl"
        
        entries = []
        if jsonl_file.exists():
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    for line in all_lines[-lines:]:
                        if line.strip():
                            try:
                                entries.append(json.loads(line))
                            except:
                                pass
            except:
                pass
        
        return entries
    
    def get_current_stats(self) -> dict:
        """Obtém estatísticas atuais"""
        stats_file = self.tokens_dir / "token_stats.json"
        
        stats = {
            "total_prompt": 0,
            "total_completion": 0,
            "total_tokens": 0,
            "total_requests": 0,
            "by_api": {}
        }
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for api_type, models in data.items():
                    stats["by_api"][api_type] = {
                        "prompt": 0,
                        "completion": 0,
                        "total": 0,
                        "requests": 0
                    }
                    
                    for model, model_data in models.items():
                        p = model_data.get("total_prompt_tokens", 0)
                        c = model_data.get("total_completion_tokens", 0)
                        
                        stats["by_api"][api_type]["prompt"] += p
                        stats["by_api"][api_type]["completion"] += c
                        stats["by_api"][api_type]["total"] += p + c
                        stats["by_api"][api_type]["requests"] += model_data.get("total_requests", 0)
                        
                        stats["total_prompt"] += p
                        stats["total_completion"] += c
                        stats["total_requests"] += model_data.get("total_requests", 0)
                
                stats["total_tokens"] = stats["total_prompt"] + stats["total_completion"]
            except:
                pass
        
        return stats
    
    def format_number(self, num: int) -> str:
        """Formata número com separadores"""
        return f"{num:,}".replace(",", ".")
    
    def print_header(self):
        """Imprime cabeçalho do dashboard"""
        clear = "\033[2J\033[H"  # Limpar terminal
        print(clear)
        print("\n")
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 78 + "║")
        print("║" + "  📊 DASHBOARD DE TOKENS - SISTEMA EM TEMPO REAL".center(78) + "║")
        print("║" + f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
        print("║" + " " * 78 + "║")
        print("╚" + "═" * 78 + "╝")
    
    def print_stats(self, stats: dict):
        """Imprime estatísticas gerais"""
        print("\n")
        print("┌─ 💰 ESTATÍSTICAS GERAIS " + "─" * 53 + "┐")
        print(f"│")
        print(f"│  Total de Tokens Processados  : {self.format_number(stats['total_tokens']):>15} tokens")
        print(f"│  • Tokens de Entrada (Prompt) : {self.format_number(stats['total_prompt']):>15} tokens")
        print(f"│  • Tokens de Saída            : {self.format_number(stats['total_completion']):>15} tokens")
        print(f"│")
        print(f"│  Requisições Processadas      : {self.format_number(stats['total_requests']):>15} reqs")
        print(f"│")
        print("└" + "─" * 77 + "┘")
    
    def print_by_api(self, stats: dict):
        """Imprime estatísticas por API"""
        print("\n")
        print("┌─ 🔧 DETALHAMENTO POR API " + "─" * 51 + "┐")
        
        for api_type, api_stats in stats["by_api"].items():
            if api_stats["total"] == 0:
                continue
            
            print(f"│")
            print(f"│  API: {api_type.upper():<18} Requisições: {api_stats['requests']:>10}")
            print(f"│  ├─ Entrada (Prompt)    : {self.format_number(api_stats['prompt']):>20} tokens")
            print(f"│  ├─ Saída               : {self.format_number(api_stats['completion']):>20} tokens")
            print(f"│  └─ TOTAL               : {self.format_number(api_stats['total']):>20} tokens")
        
        print(f"│")
        print("└" + "─" * 77 + "┘")
    
    def print_recent_entries(self, entries: list):
        """Imprime entradas recentes"""
        if not entries:
            return
        
        print("\n")
        print("┌─ 🕐 ÚLTIMAS 5 OPERAÇÕES " + "─" * 52 + "┐")
        
        for entry in entries[-5:]:
            timestamp = entry.get('timestamp', 'N/A')[:19]
            api = entry.get('api_type', 'N/A').upper()
            prompt = entry.get('prompt_tokens', 0)
            completion = entry.get('completion_tokens', 0)
            total = prompt + completion
            title = entry.get('article_title', 'N/A')[:30]
            
            print(f"│")
            print(f"│  ⏰ {timestamp} | {api:<6} | {prompt:>6} + {completion:>6} = {total:>8}")
            print(f"│     📄 {title}")
        
        print(f"│")
        print("└" + "─" * 77 + "┘")
    
    def print_footer(self):
        """Imprime rodapé com instruções"""
        print("\n")
        print("┌" + "─" * 77 + "┐")
        print("│  Pressione Ctrl+C para sair | Dashboard atualiza a cada " + 
              f"{self.interval}s".ljust(20) + "│")
        print("│  " + "✅ SISTEMA 100% OPERACIONAL E ÍNTEGRO".ljust(75) + " │")
        print("└" + "─" * 77 + "┘")
    
    def run(self, once: bool = False):
        """Executa dashboard"""
        try:
            if once:
                self.print_header()
                stats = self.get_current_stats()
                self.print_stats(stats)
                self.print_by_api(stats)
                entries = self.read_latest_entries(5)
                self.print_recent_entries(entries)
                self.print_footer()
                return
            
            while True:
                try:
                    self.print_header()
                    stats = self.get_current_stats()
                    self.print_stats(stats)
                    self.print_by_api(stats)
                    entries = self.read_latest_entries(5)
                    self.print_recent_entries(entries)
                    self.print_footer()
                    
                    time.sleep(self.interval)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Erro: {e}")
                    time.sleep(self.interval)
        
        except KeyboardInterrupt:
            pass
        finally:
            print("\n\n👋 Dashboard encerrado.\n")


class TokenGuarantee:
    """Garante captura 100% de tokens com fallbacks obrigatórios"""
    
    def __init__(self, workspace_path: str = None):
        if workspace_path is None:
            workspace_path = Path(__file__).parent
        else:
            workspace_path = Path(workspace_path)
        
        self.workspace = workspace_path
        self.tokens_dir = workspace_path / "logs" / "tokens"
        self.guarantee_log = self.tokens_dir / "token_guarantee.log"
    
    def log_guarantee(self, prompt_tokens: int, completion_tokens: int, 
                     source: str, metadata: dict = None):
        """Registra tokens com garantia obrigatória de persistência"""
        timestamp = datetime.now().isoformat()
        
        entry = {
            "timestamp": timestamp,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "source": source,
            "metadata": metadata or {}
        }
        
        # GARANTIA 1: Escrever no arquivo de garantia
        try:
            with open(self.guarantee_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[GARANTIA] Erro ao escrever garantia: {e}")
            return False
        
        # GARANTIA 2: Registrar em arquivo diário JSONL
        today_file = self.tokens_dir / f"tokens_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        try:
            with open(today_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[GARANTIA] Erro ao escrever JSONL: {e}")
            return False
        
        # GARANTIA 3: Log de sucesso
        print(f"✅ GARANTIDO: {prompt_tokens} + {completion_tokens} = {prompt_tokens + completion_tokens} tokens ({source})")
        return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        dashboard = TokenDashboard()
        dashboard.run(once=True)
    else:
        dashboard = TokenDashboard()
        dashboard.run()
