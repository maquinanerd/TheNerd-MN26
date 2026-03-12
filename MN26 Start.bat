@echo off
chcp 65001 >nul
title TheNerd MN26 — Pipeline

cd /d "%~dp0"

echo.
echo  ================================================
echo   TheNerd MN26 — Iniciando Pipeline
echo  ================================================
echo.

:: Ativa o ambiente virtual (preferencia para .venv, fallback para venv)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [AVISO] Nenhum ambiente virtual encontrado.
    echo         Usando Python do sistema...
    echo.
)

echo [INFO] Iniciando pipeline...
echo.

python main.py

echo.
echo  ================================================
echo   Pipeline finalizado.
echo  ================================================
echo.
pause
