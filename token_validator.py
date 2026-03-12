#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR OBRIGATÓRIO DE TOKENS
Garante que 100% dos tokens foram contabilizados corretamente
Valida logs, stats e persistência
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import sys
from tabulate import tabulate  # pip install tabulate

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TokenValidator:
    """Valida integridade do sistema de rastreamento de tokens"""
    
    def __init__(self, workspace_path: str = None):
        if workspace_path is None:
            workspace_path = Path(__file__).parent
        else:
            workspace_path = Path(workspace_path)
        
        self.workspace = workspace_path
        self.logs_dir = workspace_path / "logs"
        self.tokens_dir = self.logs_dir / "tokens"
        self.app_log = self.logs_dir / "app.log"
        self.token_debug_log = self.tokens_dir / "token_debug.log"
        self.token_stats = self.tokens_dir / "token_stats.json"
        
        self.issues = []
        self.warnings = []
        self.validations = []
    
    def validate_directories(self) -> bool:
        """Valida existência de diretórios requeridos"""
        logger.info("🔍 Validando estrutura de diretórios...")
        
        required_dirs = [self.logs_dir, self.tokens_dir]
        all_exist = True
        
        for dir_path in required_dirs:
            if dir_path.exists():
                logger.info(f"✅ Diretório encontrado: {dir_path.name}")
            else:
                logger.error(f"❌ Diretório FALTANDO: {dir_path}")
                self.issues.append(f"Diretório {dir_path.name} não existe")
                all_exist = False
        
        return all_exist
    
    def validate_token_files(self) -> dict:
        """Valida arquivos de tokens"""
        logger.info("🔍 Validando arquivos de logs de tokens...")
        
        results = {
            "jsonl_files": [],
            "total_entries": 0,
            "date_range": None,
            "missing_fields": []
        }
        
        if not self.tokens_dir.exists():
            self.issues.append("Diretório tokens não existe")
            return results
        
        jsonl_files = list(self.tokens_dir.glob("tokens_*.jsonl"))
        
        if not jsonl_files:
            self.warnings.append("Nenhum arquivo JSONL encontrado")
            return results
        
        total_tokens = 0
        dates = set()
        
        for jsonl_file in sorted(jsonl_files):
            file_info = {
                "file": jsonl_file.name,
                "size": jsonl_file.stat().st_size,
                "entries": 0,
                "total_tokens": 0,
                "valid": True
            }
            
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line_no, line in enumerate(f, 1):
                        if not line.strip():
                            continue
                        
                        try:
                            entry = json.loads(line)
                            file_info["entries"] += 1
                            
                            # Validar campos obrigatórios
                            required = ["timestamp", "prompt_tokens", "completion_tokens"]
                            for field in required:
                                if field not in entry:
                                    self.issues.append(
                                        f"{jsonl_file.name}:{line_no} - Campo {field} faltando"
                                    )
                                    file_info["valid"] = False
                            
                            # Somar tokens
                            prompt = entry.get("prompt_tokens", 0)
                            completion = entry.get("completion_tokens", 0)
                            total = prompt + completion
                            
                            # Validar valores
                            if prompt < 0 or completion < 0:
                                self.issues.append(
                                    f"{jsonl_file.name}:{line_no} - Tokens negativos"
                                )
                                file_info["valid"] = False
                            
                            file_info["total_tokens"] += total
                            total_tokens += total
                            
                            # Extrair data
                            if "timestamp" in entry:
                                dates.add(entry["timestamp"][:10])
                        
                        except json.JSONDecodeError as e:
                            self.issues.append(f"{jsonl_file.name}:{line_no} - JSON inválido: {e}")
                            file_info["valid"] = False
                
                if file_info["entries"] > 0:
                    logger.info(f"✅ {jsonl_file.name}: {file_info['entries']} entradas, {file_info['total_tokens']} tokens")
                else:
                    self.warnings.append(f"{jsonl_file.name} está vazio")
                
                results["jsonl_files"].append(file_info)
            
            except Exception as e:
                self.issues.append(f"Erro ao ler {jsonl_file.name}: {e}")
        
        results["total_entries"] = sum(f["entries"] for f in results["jsonl_files"])
        results["total_tokens"] = total_tokens
        results["date_range"] = f"{min(dates)} a {max(dates)}" if dates else "N/A"
        
        return results
    
    def validate_stats_file(self) -> dict:
        """Valida arquivo de estatísticas agregadas"""
        logger.info("🔍 Validando arquivo de estatísticas...")
        
        results = {
            "file_exists": self.token_stats.exists(),
            "total_apis": 0,
            "total_models": 0,
            "stats": None,
            "valid": True
        }
        
        if not self.token_stats.exists():
            self.warnings.append("Arquivo token_stats.json não encontrado")
            return results
        
        try:
            with open(self.token_stats, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            
            results["stats"] = stats
            results["total_apis"] = len(stats)
            
            for api_type, models in stats.items():
                results["total_models"] += len(models)
                
                for model, data in models.items():
                    # Validar campos
                    required = ["total_prompt_tokens", "total_completion_tokens", "total_requests"]
                    for field in required:
                        if field not in data:
                            self.issues.append(
                                f"Stats: {api_type}/{model} - Campo {field} faltando"
                            )
                            results["valid"] = False
            
            logger.info(f"✅ Stats válidas: {results['total_apis']} APIs, {results['total_models']} modelos")
            return results
        
        except json.JSONDecodeError as e:
            self.issues.append(f"token_stats.json inválido: {e}")
            results["valid"] = False
            return results
    
    def reconcile_tokens(self, jsonl_results: dict, stats_results: dict) -> dict:
        """Reconcilia totais entre JSONL e stats agregadas"""
        logger.info("🔍 Reconciliando tokens entre JSONL e Stats...")
        
        reconciliation = {
            "jsonl_total": jsonl_results.get("total_tokens", 0),
            "stats_total": 0,
            "match": False,
            "discrepancy": 0,
            "details": []
        }
        
        if stats_results["stats"]:
            for api_type, models in stats_results["stats"].items():
                for model, data in models.items():
                    total = data.get("total_prompt_tokens", 0) + data.get("total_completion_tokens", 0)
                    reconciliation["stats_total"] += total
        
        reconciliation["discrepancy"] = abs(
            reconciliation["jsonl_total"] - reconciliation["stats_total"]
        )
        reconciliation["match"] = reconciliation["discrepancy"] == 0
        
        if reconciliation["match"]:
            logger.info(f"✅ PERFEITO: JSONL e Stats sincronizados ({reconciliation['jsonl_total']} tokens)")
        else:
            self.issues.append(
                f"Discrepância de tokens: JSONL={reconciliation['jsonl_total']}, "
                f"Stats={reconciliation['stats_total']} (diferença: {reconciliation['discrepancy']})"
            )
            logger.error(f"❌ Discrepância detectada: {reconciliation['discrepancy']} tokens")
        
        return reconciliation
    
    def generate_report(self) -> str:
        """Gera relatório completo de validação"""
        logger.info("\n" + "="*80)
        logger.info("INÍCIO DA VALIDAÇÃO OBRIGATÓRIA DE TOKENS")
        logger.info("="*80)
        
        # Executar validações
        dir_valid = self.validate_directories()
        jsonl_results = self.validate_token_files()
        stats_results = self.validate_stats_file()
        reconciliation = self.reconcile_tokens(jsonl_results, stats_results)
        
        # Construir relatório
        report = []
        report.append("\n" + "="*80)
        report.append("RELATÓRIO DE VALIDAÇÃO DE TOKENS")
        report.append("="*80)
        report.append(f"Data: {datetime.now().isoformat()}\n")
        
        # Seção: Status Geral
        report.append("📊 STATUS GERAL:")
        report.append("-" * 80)
        report.append(f"Diretórios: {'✅ OK' if dir_valid else '❌ FALTANDO'}")
        report.append(f"JSONL Válidos: {'✅ OK' if jsonl_results['jsonl_files'] else '❌ NENHUM'}")
        report.append(f"Stats Válidas: {'✅ OK' if stats_results['valid'] else '❌ INVÁLIDO'}")
        report.append(f"Reconciliação: {'✅ OK' if reconciliation['match'] else '❌ DISCREPÂNCIA'}")
        report.append("")
        
        # Seção: Detalhes de Tokens
        report.append("💰 DETALHES DE TOKENS:")
        report.append("-" * 80)
        report.append(f"Total em JSONL: {jsonl_results['total_tokens']:,} tokens")
        report.append(f"Total em Stats: {reconciliation['stats_total']:,} tokens")
        report.append(f"Discrepância: {reconciliation['discrepancy']:,} tokens")
        report.append(f"Período: {jsonl_results['date_range']}")
        report.append("")
        
        # Seção: Arquivos JSONL
        if jsonl_results['jsonl_files']:
            report.append("📋 ARQUIVOS JSONL:")
            report.append("-" * 80)
            table_data = []
            for f in jsonl_results['jsonl_files']:
                table_data.append([
                    f['file'],
                    f['entries'],
                    f"{f['total_tokens']:,}",
                    '✅ OK' if f['valid'] else '❌ ERRO'
                ])
            report.append(tabulate(
                table_data,
                headers=['Arquivo', 'Entradas', 'Tokens', 'Status'],
                tablefmt='grid'
            ))
            report.append("")
        
        # Seção: APIs e Modelos
        if stats_results["stats"]:
            report.append("🔧 APIS E MODELOS:")
            report.append("-" * 80)
            table_data = []
            for api_type, models in stats_results["stats"].items():
                for model, data in models.items():
                    prompt = data.get("total_prompt_tokens", 0)
                    completion = data.get("total_completion_tokens", 0)
                    total = prompt + completion
                    requests = data.get("total_requests", 0)
                    
                    table_data.append([
                        api_type.upper(),
                        model,
                        f"{prompt:,}",
                        f"{completion:,}",
                        f"{total:,}",
                        requests
                    ])
            report.append(tabulate(
                table_data,
                headers=['API', 'Modelo', 'Entrada', 'Saída', 'Total', 'Requisições'],
                tablefmt='grid'
            ))
            report.append("")
        
        # Seção: Problemas
        if self.issues:
            report.append("❌ PROBLEMAS DETECTADOS:")
            report.append("-" * 80)
            for issue in self.issues:
                report.append(f"  • {issue}")
            report.append("")
        
        # Seção: Avisos
        if self.warnings:
            report.append("⚠️  AVISOS:")
            report.append("-" * 80)
            for warning in self.warnings:
                report.append(f"  • {warning}")
            report.append("")
        
        # Conclusão
        report.append("="*80)
        if not self.issues and reconciliation['match']:
            report.append("✅ CONCLUSÃO: SISTEMA DE TOKENS 100% OPERACIONAL E ÍNTEGRO")
        elif not self.issues:
            report.append("⚠️ CONCLUSÃO: Sistema operacional mas com discrepâncias menores")
        else:
            report.append("❌ CONCLUSÃO: Sistema requer correção!")
        report.append("="*80)
        
        return "\n".join(report)
    
    def run(self):
        """Executa validação completa"""
        report = self.generate_report()
        print(report)
        
        # Salvar relatório
        report_file = self.tokens_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"\n📄 Relatório salvo em: {report_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar relatório: {e}")
        
        # Retornar status
        return len(self.issues) == 0


if __name__ == "__main__":
    validator = TokenValidator()
    success = validator.run()
    sys.exit(0 if success else 1)
