@echo off
cd /d "%~dp0"

rem ============================================================
rem  Actualizar.bat - baja los cambios mas recientes del proyecto
rem  (sin Git). No toca tu config.json ni tus reportes generados.
rem ============================================================

set REPO_ZIP_URL=https://github.com/aldomartinezciti/Dailys-CITI-CP/archive/refs/heads/main.zip

echo Descargando la ultima version del proyecto...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%REPO_ZIP_URL%' -OutFile '..\actualizacion_temp.zip' } catch { exit 1 }"
if errorlevel 1 (
    echo [ERROR] No se pudo descargar la actualizacion. Revisa tu conexion a internet.
    pause
    exit /b 1
)

powershell -NoProfile -Command "Expand-Archive -Path '..\actualizacion_temp.zip' -DestinationPath '..\actualizacion_extraida' -Force"

for /d %%D in (..\actualizacion_extraida\*) do (
    xcopy "%%D" "." /e /y /i >nul
)

rmdir /s /q ..\actualizacion_extraida
del ..\actualizacion_temp.zip

echo Actualizando dependencias de Python ^(por si cambiaron^)...
python -m pip install --user --quiet -r requirements.txt

echo.
echo Listo, ya tienes la ultima version. Tu config.json y tus reportes no se tocaron.
pause
