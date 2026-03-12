@echo off
REM Script para iniciar o pipeline automaticamente

cd /d "e:\Área de Trabalho 2\Portal The News\Nerd\TheNews_MaquinaNerd"

echo "Ativando o ambiente virtual..."
call venv\Scripts\activate.bat

echo "Iniciando o programa..."
python main.py

pause
