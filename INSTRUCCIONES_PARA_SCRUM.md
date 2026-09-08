# Guía rápida — Azure DevOps Daily

No necesitas saber programar ni usar la terminal. Solo sigue estos pasos.

## 1. Instalación (una sola vez)

1. Guarda el archivo **`Instalar.bat`** que te compartieron en una carpeta, por ejemplo `Documentos`.
2. Haz **doble clic** en `Instalar.bat`.
   - Se abrirá una ventana negra (consola) que va instalando todo solo. No la cierres hasta que termine.
   - Si te pide instalar Python, espera a que termine, **cierra la ventana por completo** y vuelve a hacer doble clic en `Instalar.bat` para continuar.
3. En algún momento se abrirá el **Bloc de notas** con un archivo llamado `config.json`. Ahí necesitas pegar tu propio PAT (ver el paso 2 abajo).

## 2. Generar tu propio PAT de Azure DevOps

El PAT es como una contraseña que te da acceso a los datos, personal e intransferible.

1. Entra a `https://dev.azure.com/ClaroPay` en tu navegador (con tu cuenta).
2. Arriba a la derecha, haz clic en el ícono de usuario → **Personal access tokens**.
3. Clic en **+ New Token**.
4. Ponle un nombre (ej. "Dashboard Daily"), vigencia 90 días, y en permisos elige **Work Items: Read**.
5. Clic en **Create** y **copia el token** (solo se muestra una vez, guárdalo en un lugar seguro mientras lo pegas).

## 3. Completar `config.json`

De vuelta en el Bloc de notas que se abrió:

1. Busca la línea que dice:
   ```
   "personal_access_token": "PEGA_AQUI_TU_PAT_DE_AZURE_DEVOPS",
   ```
2. Reemplaza `PEGA_AQUI_TU_PAT_DE_AZURE_DEVOPS` por el token que copiaste (entre las comillas).
3. Guarda con **Ctrl+S** y cierra el Bloc de notas.

Este archivo se queda solo en tu computadora — nunca se comparte ni se sube a ningún lado.

## 4. Ver el reporte del día

Dentro de la carpeta `azure_devops_daily` que se creó, hay un archivo **`Ejecutar.bat`**.

- Doble clic en `Ejecutar.bat` cada vez que quieras ver el reporte actualizado.
- Va a jalar la información más reciente de Azure DevOps con tu PAT y **abrir automáticamente el dashboard** en tu navegador.

## 5. Cuando haya una actualización grande del proyecto

Si Aldo te avisa que hizo cambios importantes al proyecto (no a los datos, sino al programa en sí):

- Doble clic en **`Actualizar.bat`** (está en la misma carpeta).
- Descarga los cambios más recientes. Tu `config.json` (con tu PAT) no se toca ni se pierde.

## ¿Algo no funcionó?

Toma una captura de pantalla de la ventana negra con el mensaje de error y mándasela a Aldo.
