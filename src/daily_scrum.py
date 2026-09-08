"""
daily_scrum.py  (Tarea 3)
-------------------------
Genera la vista de la Daily agrupada por desarrollador. Cada tarea cae en UN
solo bucket, con prioridad: RETRASADO > HOY > MAÑANA.

- Retrasado: fecha_fin < hoy y la tarea sigue abierta (no cerrada).
- Hoy:       estado en 'in_progress'.
- Mañana:    estado 'new_todo' con fecha_inicio dentro de la ventana próxima.
             Como solo listamos tareas NO iniciadas, una tarea que ya está en
             curso jamás aparece aquí -> se cumple "solo si es diferente a lo de
             hoy" por construcción, sin ruido visual.
"""
from datetime import timedelta
from src.date_utils import hoy as _hoy, manana as _manana


def clasificar(tareas_activas, cfg):
    tz = cfg.logic["timezone"]
    hoy = _hoy(tz)
    manana = _manana(tz)
    ventana = hoy + timedelta(days=cfg.logic.get("upcoming_window_days", 2))

    cerrados = set(cfg.states["closed"])
    en_curso = set(cfg.states["in_progress"])
    nuevos = set(cfg.states["new_todo"])

    por_dev = {}  # dev -> {"retrasado": [], "hoy": [], "manana": []}

    for t in tareas_activas:
        dev = t["asignado"]
        por_dev.setdefault(dev, {"retrasado": [], "hoy": [], "manana": []})

        if t["estado"] in cerrados:
            continue

        # 1) Retrasado
        if t["fecha_fin"] and t["fecha_fin"] < hoy:
            por_dev[dev]["retrasado"].append(t)
            continue
        # 2) Hoy
        if t["estado"] in en_curso:
            por_dev[dev]["hoy"].append(t)
            continue
        # 3) Mañana / próximo (solo no iniciadas dentro de la ventana)
        if t["estado"] in nuevos and t["fecha_inicio"] and hoy <= t["fecha_inicio"] <= ventana:
            por_dev[dev]["manana"].append(t)

    # Quitamos desarrolladores sin nada relevante
    return {d: b for d, b in por_dev.items()
            if b["retrasado"] or b["hoy"] or b["manana"]}


# --- Renders ---------------------------------------------------------------
def _linea(t, con_fin=False, con_inicio=False):
    extra = ""
    if con_fin and t["fecha_fin"]:
        extra = f" (venció {t['fecha_fin'].isoformat()}, estado: {t['estado']})"
    elif con_inicio and t["fecha_inicio"]:
        extra = f" (inicia {t['fecha_inicio'].isoformat()})"
    return f"[{t['id']}] {t['titulo']}{extra}"


def render_markdown(clasificado, cfg):
    tz = cfg.logic["timezone"]
    out = [f"# Daily Scrum — {_hoy(tz).isoformat()}", ""]
    if not clasificado:
        out.append("_No hay tareas relevantes para la Daily de hoy._")
        return "\n".join(out)

    for dev in sorted(clasificado):
        b = clasificado[dev]
        out.append(f"## {dev}")
        if b["retrasado"]:
            out.append("**Retrasado — cerrar / revisar bloqueo**")
            out += [f"- {_linea(t, con_fin=True)}" for t in b["retrasado"]]
        if b["hoy"]:
            out.append("**Trabajando hoy**")
            out += [f"- {_linea(t)}" for t in b["hoy"]]
        if b["manana"]:
            out.append("**Mañana / en puerta (nuevo)**")
            out += [f"- {_linea(t, con_inicio=True)}" for t in b["manana"]]
        out.append("")
    return "\n".join(out)


def render_consola(clasificado, cfg):
    tz = cfg.logic["timezone"]
    ancho = 70
    linea = "=" * ancho
    out = [linea, f" DAILY SCRUM  —  {_hoy(tz).isoformat()}".center(ancho), linea]
    if not clasificado:
        out.append(" (Sin tareas relevantes para hoy)")
        return "\n".join(out)

    for dev in sorted(clasificado):
        b = clasificado[dev]
        out.append(f"\n>> {dev}")
        if b["retrasado"]:
            out.append("   RETRASADO:")
            out += [f"     - {_linea(t, con_fin=True)}" for t in b["retrasado"]]
        if b["hoy"]:
            out.append("   HOY:")
            out += [f"     - {_linea(t)}" for t in b["hoy"]]
        if b["manana"]:
            out.append("   MAÑANA:")
            out += [f"     - {_linea(t, con_inicio=True)}" for t in b["manana"]]
    out.append("\n" + linea)
    return "\n".join(out)


def clasificar_serializable(tareas, cfg):
    """Devuelve la Daily como listas de strings ya formateados, para embeber
    en el HTML interactivo (una entrada por desarrollador)."""
    clas = clasificar(tareas, cfg)
    out = {}
    for dev in sorted(clas):
        b = clas[dev]
        out[dev] = {
            "retrasado": [_linea(t, con_fin=True) for t in b["retrasado"]],
            "hoy":       [_linea(t) for t in b["hoy"]],
            "manana":    [_linea(t, con_inicio=True) for t in b["manana"]],
        }
    return out


import unicodedata
import re

_DOMINIO = {"citi", "com", "mx", "net", "org", "www", "claropay"}


def _tokens(texto):
    """Normaliza un nombre/correo a un set de tokens sin acentos ni dominio."""
    if not texto:
        return set()
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = {t for t in re.split(r"[^a-z0-9]+", s) if len(t) > 1}
    return toks - _DOMINIO


def construir_indice_roster(nombres_completos):
    """Prepara el roster: por cada persona, su primer nombre (con acento) y
    sus tokens para emparejar contra lo que entrega Azure (nombre o correo)."""
    idx = []
    for fn in nombres_completos:
        partes = fn.strip().split()
        idx.append({"first": partes[0] if partes else fn, "tokens": _tokens(fn)})
    return idx


def resolver_primer_nombre(asignado, idx):
    """Devuelve el primer nombre del roster que mejor empata con 'asignado'.
    Si no hay match (persona fuera del roster), usa el primer token capitalizado."""
    if not asignado or asignado == "Sin asignar":
        return "Sin asignar"
    at = _tokens(asignado)
    mejor, score = None, 0
    for p in idx:
        ov = len(at & p["tokens"])
        if ov > score:
            score, mejor = ov, p
    if mejor and score >= 2:
        return mejor["first"]
    crudo = (asignado or "").strip().split()
    crudo = crudo[0].split(".")[0] if crudo else (asignado or "Sin asignar")
    return crudo.capitalize() if crudo else "Sin asignar"


def por_dev_filtros(tareas_it, cfg, roster_nombres, horas_disponibles=None):
    """Agrupa las tareas de la iteración por desarrollador (primer nombre) en
    cinco filtros: en_curso, nuevas, atrasadas, closed, todas.
    Incluye a TODO el roster, aunque no tengan tareas.
    Si se pasa 'horas_disponibles' (capacidad de la iteración en horas),
    además calcula el % de asignación de cada dev sobre esa capacidad."""
    H = _hoy(cfg.logic["timezone"])
    M = _manana(cfg.logic["timezone"])
    closed = set(cfg.states["closed"])
    idx = construir_indice_roster(roster_nombres)

    devs = {}

    def ensure(d):
        devs.setdefault(d, {"en_curso": [], "proximas": [], "atrasadas": [],
                            "closed": [], "todas": []})

    for p in idx:
        ensure(p["first"])

    for t in tareas_it:
        dev = resolver_primer_nombre(t["asignado"], idx)
        ensure(dev)
        item = {
            "id": t["id"], "parent": t["parent"], "titulo": t["titulo"],
            "horas": t["horas"], "horas_reales": t["horas_reales"],
            "fecha_inicio": t["fecha_inicio"].isoformat() if t["fecha_inicio"] else None,
            "fecha_fin": t["fecha_fin"].isoformat() if t["fecha_fin"] else None,
        }
        ini, fin = t["fecha_inicio"], t["fecha_fin"]
        es_closed = t["estado"] in closed

        devs[dev]["todas"].append(item)
        if es_closed:
            devs[dev]["closed"].append(item)
        # En curso: el periodo Start-Due cubre hoy (Start <= hoy <= Due)
        if ini and fin and ini <= H <= fin:
            devs[dev]["en_curso"].append(item)
        # Próximas: inician mañana o después (independiente del estado)
        if ini and ini >= M:
            devs[dev]["proximas"].append(item)
        # Atrasadas: Due Date pasó (1+ día) y no están cerradas
        if fin and fin < H and not es_closed:
            devs[dev]["atrasadas"].append(item)

    for dev, b in devs.items():
        asignadas = 0.0
        for it in b["todas"]:
            try:
                asignadas += float(it["horas"])
            except (TypeError, ValueError):
                pass
        porcentaje = (round(100 * asignadas / horas_disponibles, 1)
                      if horas_disponibles else None)
        b["capacidad"] = {
            "asignadas": round(asignadas, 1),
            "disponibles": horas_disponibles,
            "porcentaje": porcentaje,
        }
    return devs


def render_html_seccion(clasificado, cfg):
    """Fragmento HTML para incrustar en el dashboard (Tarea 2)."""
    if not clasificado:
        return "<p>No hay tareas relevantes para la Daily de hoy.</p>"

    bloques = []
    for dev in sorted(clasificado):
        b = clasificado[dev]
        partes = [f"<h3>{dev}</h3>"]

        def ul(titulo, items, css, fin=False, ini=False):
            if not items:
                return ""
            lis = "".join(f"<li>{_linea(t, con_fin=fin, con_inicio=ini)}</li>" for t in items)
            return f'<div class="bucket {css}"><span class="etq">{titulo}</span><ul>{lis}</ul></div>'

        partes.append(ul("Retrasado", b["retrasado"], "rojo", fin=True))
        partes.append(ul("Hoy", b["hoy"], "verde"))
        partes.append(ul("Mañana", b["manana"], "azul", ini=True))
        bloques.append(f'<div class="dev-card">{"".join(partes)}</div>')
    return "\n".join(bloques)