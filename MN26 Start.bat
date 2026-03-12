@echo off
title TheNerd MN26 - Pipeline

cd /d "%~dp0"

echo.
echo  ================================================
echo   TheNerd MN26 - Iniciando Pipeline
echo  ================================================
echo.

set PYTHON_EXE=

if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    goto run
)

if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE=venv\Scripts\python.exe
    goto run
)

set PYTHON_EXE=py
echo [AVISO] Venv nao encontrado. Usando Python do sistema...
echo.

:run
echo [INFO] Usando: %PYTHON_EXE%
echo [INFO] Iniciando main.py...
echo.

%PYTHON_EXE% main.py

echo.
echo  ================================================
echo   Pipeline finalizado.
echo  ================================================
echo.
pause
