import argparse
import logging
import sys
import os
import atexit
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler

from app.pipeline import run_pipeline_cycle
from app.store import Database
from app.config import SCHEDULE_CONFIG

# Criar diretório de logs se não existir
os.makedirs("logs", exist_ok=True)

# Limpar handlers anteriores se existirem
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configura o logging manualmente
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler("logs/app.log", mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Also set root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Garantir que os logs sejam gravados ao sair
def flush_logs():
    for handler in [file_handler, console_handler]:
        try:
            handler.flush()
        except:
            pass

atexit.register(flush_logs)

# Mensagens amigáveis de inicialização
print("\n" + "="*80)
print("Ativando o ambiente virtual...")
print("="*80)
print("OK - Ambiente virtual ativado com sucesso.\n")
print("="*80)
print("Iniciando o programa...")
print("="*80)

def initialize_database():
    """Inicializa o banco de dados e garante que as tabelas sejam criadas."""
    logger.info("Verificando o esquema do banco de dados...")
    file_handler.flush()
    try:
        db = Database()
        db.initialize()  # Garante que as tabelas sejam criadas
        db.close()
        logger.info("Verificação do banco de dados concluída com sucesso.")
        file_handler.flush()
    except Exception as e:
        logger.critical(f"Falha ao inicializar o banco de dados: {e}", exc_info=True)
        file_handler.flush()
        sys.exit(1)

def main():
    """Função principal para executar o pipeline de conteúdo."""
    parser = argparse.ArgumentParser(description="Executa o pipeline de conteúdo VocMoney.")
    parser.add_argument(
        '--once',
        action='store_true',
        help="Executa o ciclo do pipeline uma vez e sai."
    )
    args = parser.parse_args()

    initialize_database()

    if args.once:
        logger.info("Executando um único ciclo do pipeline (--once).")
        flush_logs()
        try:
            run_pipeline_cycle()
        except Exception as e:
            logger.critical(f"Erro crítico durante a execução do ciclo único: {e}", exc_info=True)
            flush_logs()
        finally:
            logger.info("Ciclo único finalizado.")
            flush_logs()
    else:
        # Agenda as execuções futuras
        interval = SCHEDULE_CONFIG.get('check_interval_minutes', 15)
        logger.info(f"Agendador iniciado. O pipeline será executado a cada {interval} minutos entre 9h-19h (horário de Brasília).")

        # Executa imediatamente ao iniciar
        logger.info("🚀 Executando primeira verificação imediatamente...")
        try:
            run_pipeline_cycle()
        except Exception as e:
            logger.error(f"Erro na execução inicial do pipeline: {e}", exc_info=True)

        scheduler = BlockingScheduler(timezone='America/Sao_Paulo')

        # Executa a cada `interval` minutos, apenas entre 9h-19h horário de Brasília
        # cron: minute='*' = a cada minuto, hour='9-18' = 9h até 18h:59 (antes de 19h)
        scheduler.add_job(
            run_pipeline_cycle, 
            'cron',
            minute=f'*/{ interval}',  # A cada N minutos
            hour='9-18',  # 9h até 18h:59 (horário de Brasília)
            timezone='America/Sao_Paulo'
        )

        logger.info("Pressione Ctrl+C para sair.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Agendador interrompido pelo usuário.")

if __name__ == "__main__":
    main()
