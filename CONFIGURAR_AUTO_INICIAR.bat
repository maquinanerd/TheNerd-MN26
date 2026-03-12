@echo off
REM Script para agendar o pipeline para iniciar automaticamente no boot
REM Executar como ADMINISTRADOR

setlocal enabledelayedexpansion

REM Caminho do script
set SCRIPT_PATH="e:\Área de Trabalho 2\Portal The News\Nerd\TheNews_MaquinaNerd\INICIAR_PIPELINE.bat"
set TASK_NAME="TheNerdMN Pipeline"

echo.
echo ============================================
echo  Configurando Pipeline para Auto-Iniciar
echo ============================================
echo.

REM Verificar se tem permissão de admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERRO: Este script precisa ser executado como ADMINISTRADOR!
    echo.
    echo Instruções:
    echo 1. Pressione Windows + R
    echo 2. Digite: cmd
    echo 3. Pressione Ctrl+Shift+Enter (para abrir como admin)
    echo 4. Cole este comando:
    echo.
    echo    schtasks /create /tn "%TASK_NAME%" /tr "%SCRIPT_PATH%" /sc onboot /rl highest /f
    echo.
    pause
    exit /b 1
)

REM Criar tarefa agendada
echo Criando tarefa agendada...
schtasks /create /tn %TASK_NAME% /tr %SCRIPT_PATH% /sc onboot /rl highest /f

if %errorLevel% equ 0 (
    echo.
    echo ✅ SUCESSO! Pipeline será iniciado automaticamente no boot.
    echo.
    echo Verificar status:
    echo   schtasks /query /tn "%TASK_NAME%"
    echo.
    echo Remover tarefa:
    echo   schtasks /delete /tn "%TASK_NAME%" /f
    echo.
) else (
    echo.
    echo ERRO ao criar tarefa!
    echo.
)

pause
