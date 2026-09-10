@echo off
REM Script para copiar dependencias manuales de Nexo Solar

REM Verificar que el script NO se ejecute desde System32
setlocal
set CURDIR=%cd%
if /I "%CURDIR%"=="C:\Windows\System32" (
    echo ERROR: No ejecutes este script desde System32. Abre una terminal en la carpeta del proyecto y vuelve a intentarlo.
    pause
    exit /b 1
)
endlocal

REM Copiar dependencias manuales si existen
REM Copiar PyQt6.sip
if exist venv\Lib\site-packages\PyQt6\sip.cp*.pyd copy /Y venv\Lib\site-packages\PyQt6\sip.cp*.pyd dist\Nexo Solar\
if not exist dist\Nexo Solar\PyQt6 mkdir dist\Nexo Solar\PyQt6
if exist venv\Lib\site-packages\PyQt6\sip.cp*.pyd copy /Y venv\Lib\site-packages\PyQt6\sip.cp*.pyd dist\Nexo Solar\PyQt6\
REM Copiar PyQt6.QtCharts si existe
if exist venv\Lib\site-packages\PyQt6\Qt6\plugins\PyQt6\QtCharts.pyd copy /Y venv\Lib\site-packages\PyQt6\Qt6\plugins\PyQt6\QtCharts.pyd dist\Nexo Solar\PyQt6\

REM Mostrar resultado
if %errorlevel% neq 0 (
    echo ERROR: Fallo la copia de dependencias.
    pause
    exit /b %errorlevel%
) else (
    echo Copia de dependencias completada.
    echo Puedes continuar con el instalador Inno Setup.
    pause
)
