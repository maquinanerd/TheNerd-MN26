@echo off
REM 🚀 SCRIPT RÁPIDO: Validar Instalação do CTA Removal System
REM Execute este arquivo para validar que TUDO está funcionando

echo.
echo ================================================================================
echo 🚀 VALIDACAO DO NUCLEAR CTA REMOVAL SYSTEM
echo ================================================================================
echo.

cd /d "e:\Área de Trabalho 2\Portal The News\Nerd\TheNews_MaquinaNerd"

echo.
echo [1/3] Testando NUCLEAR CTA REMOVAL (5 cenários)...
echo.
python test_nuclear_cta_removal.py
if %ERRORLEVEL% EQU 0 (
    echo. & echo ✅ TESTE NUCLEAR PASSOU!
) else (
    echo. & echo ❌ TESTE NUCLEAR FALHOU!
    pause
    exit /b 1
)

echo.
echo [2/3] Testando PIPELINE CTA INTEGRATION (6 cenários)...
echo.
python test_pipeline_cta_integration.py
if %ERRORLEVEL% EQU 0 (
    echo. & echo ✅ TESTE INTEGRADO PASSOU!
) else (
    echo. & echo ❌ TESTE INTEGRADO FALHOU!
    pause
    exit /b 1
)

echo.
echo [3/3] Validando sintaxe do pipeline.py...
echo.
python -m py_compile app/pipeline.py
if %ERRORLEVEL% EQU 0 (
    echo ✅ Sintaxe OK!
) else (
    echo ❌ ERRO DE SINTAXE!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo ✅✅✅ TODOS OS TESTES PASSARAM! SISTEMA PRONTO PARA PRODUÇÃO! 🎉🎉🎉
echo ================================================================================
echo.
echo 📊 Resumo:
echo   - Nuclear tests: 5/5 PASSARAM
echo   - Integrated tests: 6/6 PASSARAM
echo   - Sintaxe: OK
echo   - Total: 11/11 TESTES VALIDADOS
echo.
echo 🚀 Próximo passo: Executar o pipeline
echo   python -m app.main
echo.
pause
