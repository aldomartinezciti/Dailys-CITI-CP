# Azure DevOps Daily

Automatiza el reporte diario del equipo a partir de Azure DevOps:

1. **Tarea 1** — Registra HDU cerradas (últimas 24h) + sus tareas hijas en Excel.
2. **Tarea 2** — Genera un dashboard HTML de pendientes + CSV para Power BI.
3. **Tarea 3** — Arma la vista de la Daily (consola + Markdown + sección en el HTML).

## Requisitos

- Python 3.10+
- Un Personal Access Token (PAT) propio de Azure DevOps con permiso de lectura sobre **Work Items**

## Instalación

```bash
git clone <url-del-repo>
cd azure_devops_daily
pip install -r requirements.txt
```

## Configuración

El archivo `config.json` **no se sube al repositorio** porque contiene el PAT (credencial personal). Cada quien usa el suyo:

1. Copia la plantilla:
   ```bash
   cp config.example.json config.json
   ```
2. Genera tu propio PAT en Azure DevOps:
   - Entra a `https://dev.azure.com/ClaroPay` → ícono de usuario (arriba a la derecha) → **Personal access tokens** → **New Token**.
   - Dale un nombre, vigencia (ej. 90 días) y permiso **Work Items: Read**.
   - Copia el token (solo se muestra una vez).
3. Abre `config.json` y reemplaza `"PEGA_AQUI_TU_PAT_DE_AZURE_DEVOPS"` con tu token real.
4. Revisa que `organization_url`, `project`, `team` y `team_roster` correspondan a tu equipo.

`config.json` queda ignorado por git (ver `.gitignore`), así que tu PAT nunca se sube.

## Ejecución

```bash
python run_daily.py
```

Salidas generadas en `salidas/`:

- `contenedores_cerrados.xlsx`
- `faltantes_powerbi.csv`
- `dashboard.html` — ábrelo directamente en tu navegador (doble clic) para ver el dashboard.
- `daily_scrum.md`

También puedes inspeccionar los campos de un work item puntual:

```bash
python run_daily.py --dump-fields 12345
```

## Recibir actualizaciones del proyecto

Como el repositorio es privado, una vez que te agreguen como colaboradora solo necesitas:

```bash
git pull
```

para traer los cambios más recientes del código. Tu `config.json` local no se ve afectado.
