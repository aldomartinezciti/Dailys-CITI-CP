@echo off
cd /d "%~dp0"

echo Generando el reporte del dia...
python run_daily.py
if errorlevel 1 (
    echo.
    echo [ERROR] Algo fallo al generar el reporte. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
echo Listo. Abriendo el dashboard...
start "" "salidas\dashboard.html"
pause
