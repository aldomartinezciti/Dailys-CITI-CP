@echo off
cd /d "%~dp0"

echo Descargando la ultima version del proyecto...
git pull
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo actualizar. Revisa tu conexion a internet.
    pause
    exit /b 1
)

echo Actualizando dependencias de Python ^(por si cambiaron^)...
python -m pip install --quiet -r requirements.txt

echo.
echo Listo, ya tienes la ultima version. Tu config.json no se toco.
pause
