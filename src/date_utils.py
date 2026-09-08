"""
date_utils.py
-------------
Manejo de fechas robusto para evitar el corrimiento de calendario por el
offset de México (UTC-6). Los campos de fecha "de calendario" (FechaInicio /
FechaFin) se leen tomando la parte de fecha en UTC: como tus bots los guardan
a mediodía UTC (T12:00:00Z), la fecha de calendario nunca se corre al día
anterior aunque se convierta a zona local.

"Hoy" y "mañana" se calculan en la zona horaria del equipo para que coincidan
con la percepción real de la Daily.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def parse_azure_datetime(valor):
    """Convierte un string ISO de Azure ('2026-07-10T12:00:00Z') en datetime
    aware en UTC. Devuelve None si no hay valor."""
    if not valor:
        return None
    s = str(valor).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # Formato con milisegundos u otros: recortamos a segundos
        try:
            dt = datetime.fromisoformat(s.split(".")[0] + "+00:00")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fecha_calendario(valor):
    """Devuelve solo la fecha (date) de un campo tipo FechaInicio/FechaFin,
    tomando el día en UTC para respetar la corrección de mediodía."""
    dt = parse_azure_datetime(valor)
    return dt.date() if dt else None


def hoy(tz_nombre="America/Mexico_City"):
    return datetime.now(ZoneInfo(tz_nombre)).date()


def manana(tz_nombre="America/Mexico_City"):
    return hoy(tz_nombre) + timedelta(days=1)


def cutoff_utc(horas_atras):
    """Instante UTC hace N horas, formateado para WIQL ('...Z')."""
    dt = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def dias_habiles(inicio, fin):
    """Cuenta días hábiles (lunes a viernes) entre dos fechas, inclusive.
    'inicio'/'fin' son objetos date. Devuelve 0 si faltan o están invertidas."""
    if not inicio or not fin or fin < inicio:
        return 0
    dias = 0
    actual = inicio
    while actual <= fin:
        if actual.weekday() < 5:
            dias += 1
        actual += timedelta(days=1)
    return dias
