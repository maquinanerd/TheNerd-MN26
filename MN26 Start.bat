@echo off
chcp 65001 >nul
title TheNerd MN26 — Pipeline

cd /d "%~dp0"

echo.
echo  ================================================
echo   TheNerd MN26 — Iniciando Pipeline
echo  ================================================
echo.

:: Seleciona o Python do .venv ou venv (sem depender do PATH do sistema)
set PYTHON_EXE=

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_EXE=.venv\Scripts\python.exe
    )
)

if "%PYTHON_EXE%"=="" (
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set PYTHON_EXE=venv\Scripts\python.exe
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [AVISO] Ambiente virtual nao encontrado ou invalido.
    echo         Tentando Python do sistema (py launcher)...
    set PYTHON_EXE=py
    echo.
)

echo [INFO] Usando: %PYTHON_EXE%
echo [INFO] Iniciando pipeline...
echo.

%PYTHON_EXE% main.py

echo.
echo  ================================================
echo   Pipeline finalizado.
echo  ================================================
echo.
pause
