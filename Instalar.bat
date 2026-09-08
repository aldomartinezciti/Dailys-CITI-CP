@echo off
setlocal

rem ============================================================
rem  Instalar.bat - configuracion inicial (correr UNA sola vez)
rem  No necesita Git. Descarga el proyecto como ZIP, instala
rem  dependencias y prepara tu config.json con tu propio PAT.
rem ============================================================

set REPO_ZIP_URL=https://github.com/aldomartinezciti/Dailys-CITI-CP/archive/refs/heads/main.zip
set CARPETA=azure_devops_daily

echo === Instalador de Azure DevOps Daily ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo Python no se encontro. Intentando instalarlo...
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo instalar Python automaticamente.
        echo Pide ayuda a tu equipo de IT para instalar Python 3, o contacta a Aldo.
        pause
        exit /b 1
    )
    echo.
    echo IMPORTANTE: Python se acaba de instalar. Cierra esta ventana por completo
    echo y vuelve a hacer doble clic en Instalar.bat para continuar
    echo ^(esto es necesario para que Windows reconozca el nuevo PATH^).
    pause
    exit /b 0
)

if exist "%CARPETA%" (
    echo La carpeta %CARPETA% ya existe, se omite la descarga inicial.
    echo Si quieres bajar cambios nuevos usa Actualizar.bat en vez de este archivo.
) else (
    echo Descargando el proyecto...
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%REPO_ZIP_URL%' -OutFile 'proyecto.zip' } catch { exit 1 }"
    if errorlevel 1 (
        echo [ERROR] No se pudo descargar el proyecto. Revisa tu conexion a internet.
        pause
        exit /b 1
    )

    powershell -NoProfile -Command "Expand-Archive -Path 'proyecto.zip' -DestinationPath 'temp_descarga' -Force"

    for /d %%D in (temp_descarga\*) do (
        move "%%D" "%CARPETA%" >nul
    )

    rmdir /s /q temp_descarga
    del proyecto.zip
)

cd /d "%CARPETA%"

echo Instalando dependencias de Python...
python -m pip install --user --quiet --upgrade pip
python -m pip install --user --quiet -r requirements.txt

if not exist config.json (
    copy config.example.json config.json >nul
    echo.
    echo Se va a abrir config.json en el Bloc de notas.
    echo Busca la linea "personal_access_token" y reemplaza
    echo PEGA_AQUI_TU_PAT_DE_AZURE_DEVOPS por tu propio PAT de Azure DevOps.
    echo Guarda el archivo ^(Ctrl+S^) y cierra el Bloc de notas para continuar.
    pause
    notepad config.json
)

echo.
echo ================================================
echo  Listo. A partir de ahora usa Ejecutar.bat
echo  ^(dentro de la carpeta %CARPETA%^) cada vez que
echo  quieras generar el reporte del dia.
echo ================================================
pause
