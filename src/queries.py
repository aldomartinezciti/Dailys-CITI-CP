"""
queries.py
----------
Construye las consultas WIQL a partir del config (tipos, estados y campos) y
normaliza los work items crudos de Azure a diccionarios cómodos de usar.
"""
from src.date_utils import parse_azure_datetime, fecha_calendario


def _lista_sql(valores):
    """['A', 'B'] -> \"'A', 'B'\" para cláusulas IN de WIQL."""
    return ", ".join("'" + v.replace("'", "''") + "'" for v in valores)


def _filtro_equipo(cfg):
    """Filtra por el campo de equipo (p.ej. 'Agile Team' = 'Core Team').
    WIQL acepta el nombre amigable del campo entre corchetes."""
    campo = cfg.azure.get("team_field", "").strip()
    valor = cfg.azure.get("team_value", "").strip()
    if campo and valor:
        return f" AND [{campo}] = '{valor.replace(chr(39), chr(39)*2)}'"
    return ""


def _filtro_area(cfg):
    area = cfg.azure.get("area_path", "").strip()
    return f" AND [System.AreaPath] UNDER '{area}'" if area else ""


def _filtro_iteration(cfg):
    it = cfg.azure.get("iteration_path", "").strip()
    if not it:
        return ""
    if it.upper() == "CURRENT":
        team = cfg.azure.get("team", "").strip()
        if not team:
            return ""  # sin equipo no se puede resolver el sprint actual
        proj = cfg.azure["project"]
        return f" AND [System.IterationPath] = @CurrentIteration('[{proj}]\\{team}')"
    return f" AND [System.IterationPath] UNDER '{it}'"


# --- Consultas WIQL --------------------------------------------------------
def wiql_hdu_cerradas(cfg, cutoff_iso):
    """HDU que entraron a un estado cerrado en las últimas N horas."""
    f = cfg.fields
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] = '{cfg.wit['user_story']}' "
        f"AND [System.State] IN ({_lista_sql(cfg.states['closed'])}) "
        f"AND [{f['closed_date']}] >= '{cutoff_iso}'"
        f"{_filtro_area(cfg)}"
    )


def wiql_hdu_activas(cfg):
    """HDU que NO están cerradas (activas)."""
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] = '{cfg.wit['user_story']}' "
        f"AND [System.State] NOT IN ({_lista_sql(cfg.states['closed'])})"
        f"{_filtro_area(cfg)}"
    )


def _tipos_tarea(cfg):
    """El tipo de tarea puede ser un string o una lista (p.ej. ['Task','Tarea'])."""
    t = cfg.wit["task"]
    return t if isinstance(t, list) else [t]


def normalizar_iter_path(cfg, path):
    """Asegura que el path de iteración empiece con el nombre del proyecto,
    como lo espera WIQL (formato 'Proyecto\\...\\IT_x.y')."""
    if not path:
        return path
    p = path.strip("\\")
    proj = cfg.azure["project"]
    if not p.startswith(proj):
        p = f"{proj}\\{p}"
    return p


def wiql_tasks_bajo_iteracion(cfg, iter_path):
    """Task del área cuyo IterationPath cuelga de iter_path (una IT o un PI)."""
    ip = iter_path.replace("'", "''")
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] IN ({_lista_sql(_tipos_tarea(cfg))}) "
        f"AND [System.IterationPath] UNDER '{ip}'"
        f"{_filtro_equipo(cfg)}"
        f"{_filtro_area(cfg)}"
    )


def wiql_all_tasks(cfg):
    """Todas las Task del área configurada (planeadas). De aquí subimos a sus
    padres, sean del tipo que sean (HDU, Enabler, Objetivo IT, etc.)."""
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] IN ({_lista_sql(_tipos_tarea(cfg))})"
        f"{_filtro_area(cfg)}"
        f"{_filtro_iteration(cfg)}"
    )


def wiql_tareas_de(cfg, ids_padres):
    """Tareas cuyo System.Parent está en la lista de HDU dadas."""
    if not ids_padres:
        return None
    ids = ", ".join(str(i) for i in ids_padres)
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.WorkItemType] IN ({_lista_sql(_tipos_tarea(cfg))}) "
        f"AND [System.Parent] IN ({ids})"
    )


def wiql_spotlight(cfg, email, since_iso):
    """Todo lo asignado a 'email' con actividad desde 'since_iso', excluyendo
    los tipos Task (solo cosas fuera de Task: issues, bugs, features, etc.).
    Sin filtro de iteración: trae también lo que no tiene sprint asignado."""
    em = email.replace("'", "''")
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.AssignedTo] = '{em}' "
        f"AND [System.ChangedDate] >= '{since_iso}' "
        f"AND [System.WorkItemType] NOT IN ({_lista_sql(_tipos_tarea(cfg))})"
    )


def wiql_asignado_en_pi(cfg, email, pi_path):
    """Todo lo asignado a 'email' cuya iteración cuelga del PI (cualquier tipo,
    sin filtrar por equipo)."""
    ip = pi_path.replace("'", "''")
    em = email.replace("'", "''")
    return (
        "SELECT [System.Id] FROM WorkItems WHERE "
        f"[System.AssignedTo] = '{em}' "
        f"AND [System.IterationPath] UNDER '{ip}'"
    )


def wiql_hijos_de(cfg, ids_padres):
    """Hijos (de cualquier tipo) cuyo System.Parent está en la lista dada."""
    if not ids_padres:
        return None
    ids = ", ".join(str(i) for i in ids_padres)
    return f"SELECT [System.Id] FROM WorkItems WHERE [System.Parent] IN ({ids})"


# --- Campos que pedimos al batch ------------------------------------------
def campos_solicitados(cfg):
    f = cfg.fields
    return [
        f["title"], f["state"], f["assigned_to"], f["work_item_type"],
        f["parent"], f["changed_date"], f["closed_date"],
        f["start_date"], f["target_date"],
        f["estimated_hours"], f["real_hours"],
        "System.IterationPath", "System.CreatedDate",
    ]


# --- Normalización ---------------------------------------------------------
def normalizar(wi, cfg):
    """Convierte un work item crudo de Azure en un dict plano y legible."""
    f = cfg.fields
    campos = wi.get("fields", {})

    asignado = campos.get(f["assigned_to"])
    if isinstance(asignado, dict):
        asignado = asignado.get("displayName") or asignado.get("uniqueName")
    asignado = asignado or "Sin asignar"

    return {
        "id":            wi.get("id"),
        "titulo":        campos.get(f["title"], ""),
        "estado":        campos.get(f["state"], ""),
        "asignado":      asignado,
        "tipo":          campos.get(f["work_item_type"], ""),
        "parent":        campos.get(f["parent"]),
        "iteration":     campos.get("System.IterationPath", ""),
        "creado":        parse_azure_datetime(campos.get("System.CreatedDate")),
        "changed_date":  parse_azure_datetime(campos.get(f["changed_date"])),
        "closed_date":   parse_azure_datetime(campos.get(f["closed_date"])),
        "fecha_inicio":  fecha_calendario(campos.get(f["start_date"])),
        "fecha_fin":     fecha_calendario(campos.get(f["target_date"])),
        "horas":         campos.get(f["estimated_hours"]),
        "horas_reales":  campos.get(f["real_hours"]),
    }
