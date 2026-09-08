@echo off
setlocal

rem ============================================================
rem  Instalar.bat - configuracion inicial (correr UNA sola vez)
rem  Descarga el proyecto, instala dependencias y prepara tu
rem  config.json con tu propio PAT de Azure DevOps.
rem ============================================================

set REPO_URL=https://github.com/REEMPLAZAR/azure_devops_daily.git
set CARPETA=azure_devops_daily

echo === Instalador de Azure DevOps Daily ===
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro Git instalado.
    echo Instalalo desde https://git-scm.com/download/win y vuelve a correr este archivo.
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo Python no se encontro. Intentando instalarlo con winget...
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    echo.
    echo IMPORTANTE: Python se acaba de instalar. Cierra esta ventana por completo
    echo y vuelve a hacer doble clic en Instalar.bat para continuar
    echo ^(esto es necesario para que Windows reconozca el nuevo PATH^).
    pause
    exit /b 0
)

if exist "%CARPETA%" (
    echo La carpeta %CARPETA% ya existe, se omite la descarga.
) else (
    echo Descargando el proyecto...
    git clone "%REPO_URL%" "%CARPETA%"
    if errorlevel 1 (
        echo [ERROR] No se pudo descargar el repositorio. Revisa tu conexion o la URL.
        pause
        exit /b 1
    )
)

cd /d "%CARPETA%"

echo Instalando dependencias de Python...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

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
