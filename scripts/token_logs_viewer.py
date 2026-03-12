#!/usr/bin/env python3
"""
Visualizador de logs de tokens - Dashboard em terminal
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

class TokenLogsViewer:
    """Visualiza e analisa logs de tokens"""
    
    def __init__(self, log_dir: str = "logs/tokens"):
        self.log_dir = Path(log_dir)
        if not self.log_dir.exists():
            print(f"❌ Diretório de logs não encontrado: {self.log_dir}")
            sys.exit(1)
        
        self.stats_file = self.log_dir / 'token_stats.json'
    
    def load_stats(self) -> Dict:
        """Carrega as estatísticas salvas"""
        if not self.stats_file.exists():
            return {}
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erro ao ler estatísticas: {e}")
            return {}
    
    def load_logs(self, days: int = 1) -> List[Dict]:
        """
        Carrega logs dos últimos N dias
        
        Args:
            days: Número de dias para carregar (padrão: 1)
        """
        logs = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            log_file = self.log_dir / f"tokens_{date}.jsonl"
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                logs.append(json.loads(line))
                except Exception as e:
                    print(f"⚠️  Erro ao ler {log_file}: {e}")
        
        return logs
    
    def print_header(self, title: str) -> None:
        """Imprime um cabeçalho formatado"""
        print("\n" + "="*100)
        print(f"  {title}")
        print("="*100)
    
    def print_table_header(self, columns: List[str], widths: List[int]) -> None:
        """Imprime cabeçalho de tabela"""
        header = ""
        for col, width in zip(columns, widths):
            header += f" {col:<{width-2}} |"
        print(header)
        print("-" * sum(widths) + "-" * len(widths))
    
    def print_table_row(self, values: List[str], widths: List[int]) -> None:
        """Imprime uma linha de tabela"""
        row = ""
        for val, width in zip(values, widths):
            row += f" {str(val):<{width-2}} |"
        print(row)
    
    def view_summary(self) -> None:
        """Exibe resumo geral"""
        stats = self.load_stats()
        
        if not stats:
            print("\n⚠️  Nenhuma estatística disponível ainda.")
            return
        
        self.print_header("📊 RESUMO GERAL DE TOKENS")
        
        # Calcular totais
        total_prompt = 0
        total_completion = 0
        total_requests = 0
        total_success = 0
        total_fail = 0
        
        for api_data in stats.values():
            for model_data in api_data.values():
                total_prompt += model_data.get('total_prompt_tokens', 0)
                total_completion += model_data.get('total_completion_tokens', 0)
                total_requests += model_data.get('total_requests', 0)
                total_success += model_data.get('successful_requests', 0)
                total_fail += model_data.get('failed_requests', 0)
        
        total_tokens = total_prompt + total_completion
        
        print(f"\n📥 TOKENS DE ENTRADA (PROMPTS):")
        print(f"   {total_prompt:>15,} tokens")
        
        print(f"\n📤 TOKENS DE SAÍDA (RESPOSTAS):")
        print(f"   {total_completion:>15,} tokens")
        
        print(f"\n✅ TOTAL DE TOKENS:")
        print(f"   {total_tokens:>15,} tokens")
        
        print(f"\n📋 REQUISIÇÕES:")
        print(f"   Total:        {total_requests:>12,}")
        print(f"   Sucesso:      {total_success:>12,} ✔️")
        print(f"   Falhas:       {total_fail:>12,} ❌")
        
        if total_requests > 0:
            success_rate = (total_success / total_requests) * 100
            print(f"   Taxa Sucesso: {success_rate:>12.1f}%")
        
        print()
    
    def view_by_api(self) -> None:
        """Exibe detalhamento por tipo de API"""
        stats = self.load_stats()
        
        if not stats:
            print("\n⚠️  Nenhuma estatística disponível.")
            return
        
        self.print_header("🔌 DETALHAMENTO POR API")
        
        for api_type, api_data in stats.items():
            print(f"\n\n🔌 {api_type.upper()}")
            print("-" * 100)
            
            columns = ["Modelo", "Entrada", "Saída", "Total", "Requisições", "Sucesso", "Falhas", "Taxa"]
            widths = [25, 15, 15, 15, 15, 12, 12, 12]
            
            self.print_table_header(columns, widths)
            
            for model, model_data in api_data.items():
                prompt = model_data['total_prompt_tokens']
                completion = model_data['total_completion_tokens']
                total = model_data['total_tokens']
                requests = model_data['total_requests']
                success = model_data['successful_requests']
                fail = model_data['failed_requests']
                
                success_rate = (success / requests * 100) if requests > 0 else 0
                
                self.print_table_row(
                    [
                        model[:23],
                        f"{prompt:,}",
                        f"{completion:,}",
                        f"{total:,}",
                        f"{requests:,}",
                        f"{success:,}",
                        f"{fail:,}",
                        f"{success_rate:.1f}%"
                    ],
                    widths
                )
        
        print()
    
    def view_recent_logs(self, limit: int = 20, days: int = 1) -> None:
        """Exibe logs recentes"""
        logs = self.load_logs(days)
        
        if not logs:
            print(f"\n⚠️  Nenhum log encontrado nos últimos {days} dia(s).")
            return
        
        self.print_header(f"🕐 ÚLTIMOS {limit} REGISTROS (últimos {days} dias)")
        
        columns = ["Timestamp", "API", "Modelo", "Entrada", "Saída", "Total", "Status"]
        widths = [25, 10, 20, 12, 12, 12, 10]
        
        self.print_table_header(columns, widths)
        
        # Mostrar últimos registros (invertido para mais recentes)
        for log in logs[-limit:]:
            timestamp = log['timestamp'].split('T')[1][:8]  # HH:MM:SS
            api_type = log['api_type'][:8]
            model = log['model'][:18]
            prompt = log['prompt_tokens']
            completion = log['completion_tokens']
            total = log['total_tokens']
            status = "✅" if log['success'] else "❌"
            
            self.print_table_row(
                [timestamp, api_type, model, f"{prompt:,}", f"{completion:,}", f"{total:,}", status],
                widths
            )
        
        print()
    
    def view_daily_comparison(self, days: int = 7) -> None:
        """Exibe comparação diária"""
        self.print_header(f"📈 COMPARAÇÃO DIÁRIA (últimos {days} dias)")
        
        daily_stats = defaultdict(lambda: {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'requests': 0,
            'success': 0
        })
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            logs = self.load_logs(1)  # Carrega logs do dia específico
            
            for log in logs:
                if log['timestamp'].startswith(date):
                    daily_stats[date]['prompt_tokens'] += log['prompt_tokens']
                    daily_stats[date]['completion_tokens'] += log['completion_tokens']
                    daily_stats[date]['requests'] += 1
                    if log['success']:
                        daily_stats[date]['success'] += 1
        
        if not daily_stats:
            print("\n⚠️  Nenhum dado diário disponível.")
            return
        
        columns = ["Data", "Entrada", "Saída", "Total", "Requisições", "Sucesso"]
        widths = [15, 15, 15, 15, 15, 15]
        
        self.print_table_header(columns, widths)
        
        for date in sorted(daily_stats.keys(), reverse=True):
            stats = daily_stats[date]
            prompt = stats['prompt_tokens']
            completion = stats['completion_tokens']
            total = prompt + completion
            requests = stats['requests']
            success = stats['success']
            
            self.print_table_row(
                [date, f"{prompt:,}", f"{completion:,}", f"{total:,}", f"{requests:,}", f"{success:,}"],
                widths
            )
        
        print()
    
    def view_export_csv(self, output_file: str = "token_stats.csv") -> None:
        """Exporta estatísticas em CSV"""
        stats = self.load_stats()
        
        if not stats:
            print("\n⚠️  Nenhuma estatística para exportar.")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("API,Modelo,Entrada,Saída,Total,Requisições,Sucesso,Falhas,TaxaSucesso\n")
                
                for api_type, api_data in stats.items():
                    for model, model_data in api_data.items():
                        prompt = model_data['total_prompt_tokens']
                        completion = model_data['total_completion_tokens']
                        total = model_data['total_tokens']
                        requests = model_data['total_requests']
                        success = model_data['successful_requests']
                        fail = model_data['failed_requests']
                        success_rate = (success / requests * 100) if requests > 0 else 0
                        
                        f.write(
                            f"{api_type},{model},{prompt},{completion},{total},"
                            f"{requests},{success},{fail},{success_rate:.1f}\n"
                        )
            
            print(f"\n✅ Estatísticas exportadas para: {output_file}")
        
        except Exception as e:
            print(f"\n❌ Erro ao exportar: {e}")

def main():
    """Menu principal"""
    import os
    
    # Determinar diretório de logs
    script_dir = Path(__file__).parent
    log_dir = script_dir.parent / 'logs' / 'tokens'
    
    viewer = TokenLogsViewer(str(log_dir))
    
    while True:
        print("\n" + "="*100)
        print("  📊 VISUALIZADOR DE LOGS DE TOKENS")
        print("="*100)
        print("\nOpções:")
        print("  1. 📊 Resumo Geral")
        print("  2. 🔌 Detalhamento por API")
        print("  3. 🕐 Últimos Logs")
        print("  4. 📈 Comparação Diária")
        print("  5. 📥 Exportar para CSV")
        print("  6. 🔄 Atualizar Visão")
        print("  0. ❌ Sair")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == '1':
            viewer.view_summary()
        elif choice == '2':
            viewer.view_by_api()
        elif choice == '3':
            limit = input("Quantos logs recentes? (padrão: 20): ").strip()
            limit = int(limit) if limit.isdigit() else 20
            days = input("Últimos quantos dias? (padrão: 1): ").strip()
            days = int(days) if days.isdigit() else 1
            viewer.view_recent_logs(limit, days)
        elif choice == '4':
            days = input("Quantos dias? (padrão: 7): ").strip()
            days = int(days) if days.isdigit() else 7
            viewer.view_daily_comparison(days)
        elif choice == '5':
            filename = input("Nome do arquivo CSV (padrão: token_stats.csv): ").strip()
            filename = filename if filename else "token_stats.csv"
            viewer.view_export_csv(filename)
        elif choice == '6':
            os.system('cls' if os.name == 'nt' else 'clear')
            continue
        elif choice == '0':
            print("\n👋 Até logo!")
            break
        else:
            print("\n❌ Opção inválida!")
        
        input("\nPressione ENTER para continuar...")

if __name__ == '__main__':
    main()
