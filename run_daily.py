"""
run_daily.py
------------
Punto de entrada. Orquesta las tres tareas del MVP:
  Tarea 1  Registrar HDU cerradas (24h) + tareas hijas en Excel.
  Tarea 2  Dashboard HTML de faltantes + CSV para Power BI.
  Tarea 3  Vista de la Daily (consola + Markdown + sección en el HTML).

Uso:
    python run_daily.py                 # ejecuta todo
    python run_daily.py --dump-fields 12345   # inspecciona campos de un WI
"""
import sys
from datetime import datetime
from collections import defaultdict

from src.config_loader import Config
from src.azure_client import AzureDevOpsClient
from src import queries as Q
from src import excel_writer, dashboard, daily_scrum
from src.date_utils import cutoff_utc, hoy, parse_azure_datetime, fecha_calendario, dias_habiles

# La consola de Windows suele usar un codepage (cp1252/cp850) que no cubre todo
# unicode; un título con un carácter raro (p.ej. guion no separable ‑)
# puede tumbar el batch diario completo. Forzamos utf-8 con reemplazo.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def agrupar_por_padre(tareas):
    d = defaultdict(list)
    for t in tareas:
        if t["parent"]:
            d[t["parent"]].append(t)
    return d


def listar_areas(cfg, cliente):
    """Imprime todas las rutas de área del proyecto, listas para pegar en
    config.json (azure.area_path). Recuerda usar \\\\ en el JSON."""
    print(">> Áreas del proyecto (copia la que sea tu equipo):\n")
    raiz = cliente.get_areas()

    def recorrer(nodo, prefijo):
        ruta = f"{prefijo}\\{nodo['name']}" if prefijo else nodo["name"]
        print(f"   {ruta}")
        for hijo in nodo.get("children", []):
            recorrer(hijo, ruta)

    recorrer(raiz, "")
    print("\n   En config.json ponlo con doble barra, por ejemplo:")
    print('     "area_path": "Proyecto\\\\Core Team"')


def escanear_scopes(cfg, cliente):
    """Muestra las Áreas e Iteraciones (sprints) reales de las Task, con
    conteos, para elegir bien area_path / iteration_path en el config."""
    print(">> Escaneando cómo están etiquetadas las Task (área e iteración)...\n")
    tipos = Q._tipos_tarea(cfg)
    tipos_sql = ", ".join("'" + t + "'" for t in tipos)
    ids = None
    for dias in (30, 14, 7):
        q = ("SELECT [System.Id] FROM WorkItems WHERE "
             f"[System.WorkItemType] IN ({tipos_sql}) "
             f"AND [System.ChangedDate] >= @Today - {dias}")
        try:
            ids = cliente.run_wiql(q)
            print(f"   (Task modificadas en los últimos {dias} días: {len(ids)})\n")
            break
        except RuntimeError as e:
            if "20000" in str(e) or "size limit" in str(e).lower():
                continue
            raise
    if not ids:
        print("   No se pudo muestrear. Revisa el tipo 'task' en config.json.")
        return

    wis = cliente.get_work_items(ids[:500],
                                 ["System.AreaPath", "System.IterationPath"])
    areas, iters = {}, {}
    for wi in wis:
        f = wi.get("fields", {})
        a = f.get("System.AreaPath", "?")
        it = f.get("System.IterationPath", "?")
        areas[a] = areas.get(a, 0) + 1
        iters[it] = iters.get(it, 0) + 1

    print("   === ÁREAS (para azure.area_path — recuerda doble barra \\\\) ===")
    for a, n in sorted(areas.items(), key=lambda x: -x[1])[:20]:
        print(f"     ({n:4d})  {a}")
    print("\n   === ITERACIONES / SPRINTS (para azure.iteration_path) ===")
    for it, n in sorted(iters.items(), key=lambda x: -x[1])[:20]:
        print(f"     ({n:4d})  {it}")
    print("\n   Tip: para la Daily, lo normal es fijar el sprint actual.")
    print("   Puedes poner iteration_path = \"CURRENT\" y azure.team = \"Core Team\"")
    print("   para que siga automáticamente el sprint vigente del equipo.")


def diagnosticar_item(cfg, cliente, wid):
    """Evalúa un work item contra cada filtro del dashboard y explica por qué
    aparece o no."""
    print(f">> Diagnóstico del work item {wid}\n")
    campos = cliente.get_all_fields(wid)

    tipo = campos.get("System.WorkItemType", "?")
    iterp = campos.get("System.IterationPath", "")
    estado = campos.get("System.State", "?")
    parent = campos.get("System.Parent")
    asig = campos.get("System.AssignedTo")
    if isinstance(asig, dict):
        asig = asig.get("displayName") or asig.get("uniqueName")
    # El campo de equipo puede tener nombre custom; probamos varios
    agile = (campos.get("Custom.AgileTeam")
             or campos.get(cfg.azure.get("team_field", ""))
             or "(vacío)")

    print(f"   Tipo:        {tipo}")
    print(f"   Estado:      {estado}")
    print(f"   Iteración:   {iterp}")
    print(f"   Agile Team:  {agile}")
    print(f"   Asignado a:  {asig or '(sin asignar)'}")
    print(f"   Parent:      {parent if parent else '(sin padre)'}\n")

    # Resolver el PI vigente para comparar
    actual_path, pi_path, _ = resolver_iteracion(cfg, cliente)
    tipos = Q._tipos_tarea(cfg)
    team_val = cfg.azure.get("team_value", "").strip()

    ok_tipo = tipo in tipos
    ok_iter = bool(pi_path) and iterp.startswith(pi_path)
    ok_team = (agile == team_val)

    def marca(b): return "PASA " if b else "FALLA"

    print("   Contra los filtros del dashboard:")
    print(f"     [{marca(ok_tipo)}] Tipo en {tipos}")
    print(f"     [{marca(ok_iter)}] Iteración bajo el PI vigente ({pi_path})")
    print(f"     [{marca(ok_team)}] Agile Team = '{team_val}'\n")

    if ok_tipo and ok_iter and ok_team:
        print("   => Debería aparecer. Si no lo ves, revisa a qué persona/filtro cae")
        print(f"      (asignado a '{asig}', estado '{estado}').")
    else:
        motivos = []
        if not ok_tipo:
            motivos.append(f"su tipo es '{tipo}', no {tipos}")
        if not ok_iter:
            motivos.append(f"su iteración no cuelga del PI vigente ({pi_path})")
        if not ok_team:
            motivos.append(f"su Agile Team es '{agile}', no '{team_val}'")
        print("   => NO aparece porque: " + "; ".join(motivos) + ".")
        if not ok_tipo:
            print(f"      Para incluir este tipo, agrégalo en work_item_types.task del config.")
        if not ok_iter:
            print("      Está fuera del PI actual (probablemente de un PI anterior).")


def diagnosticar(cfg, cliente):
    """Muestra los nombres reales de tipos de work item y estados que existen
    en el proyecto, con conteos. Sirve para llenar bien el config.json."""
    print(">> Diagnóstico del proyecto (leyendo work items recientes)...\n")

    # Acotamos por fecha para no chocar con el tope de 20,000 de Azure.
    # Probamos ventanas cada vez más chicas hasta que la consulta pase.
    ids = None
    for dias in (7, 3, 1):
        query = ("SELECT [System.Id] FROM WorkItems "
                 f"WHERE [System.ChangedDate] >= @Today - {dias} "
                 "ORDER BY [System.ChangedDate] DESC")
        try:
            ids = cliente.run_wiql(query)
            print(f"   (muestra de work items modificados en los últimos {dias} día(s))")
            break
        except RuntimeError as e:
            if "20000" in str(e) or "size limit" in str(e).lower():
                continue  # demasiados; probamos ventana más chica
            raise
    if ids is None:
        print("   Incluso 1 día devuelve más de 20,000 items. Define un 'area_path'")
        print("   en config.json para acotar a tu equipo/ART y vuelve a intentar.")
        return
    if not ids:
        print("   No hubo work items modificados en la ventana. Prueba abrir Azure")
        print("   y confirmar que hay actividad reciente en este proyecto.")
        return

    muestra = ids[:200]
    wis = cliente.get_work_items(
        muestra, ["System.WorkItemType", "System.State", "System.AssignedTo"])

    tipos, estados = {}, {}
    for wi in wis:
        f = wi.get("fields", {})
        t = f.get("System.WorkItemType", "?")
        e = f.get("System.State", "?")
        tipos[t] = tipos.get(t, 0) + 1
        estados.setdefault(t, {})
        estados[t][e] = estados[t].get(e, 0) + 1

    print(f"   Work items revisados: {len(wis)} (de {len(ids)} totales)\n")
    print("   === TIPOS de work item que existen (copia estos nombres tal cual) ===")
    for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"     '{t}'   ({n})")
    print("\n   === ESTADOS por tipo ===")
    for t, mapa in estados.items():
        est = ", ".join(f"'{e}' ({n})" for e, n in sorted(mapa.items(), key=lambda x: -x[1]))
        print(f"     {t}: {est}")
    print("\n   Ajusta en config.json:")
    print("     - work_item_types.user_story  = el nombre de tu Historia de Usuario")
    print("     - work_item_types.task        = el nombre de tu Tarea")
    print("     - states.closed / in_progress / new_todo = los estados de arriba")


def _iter_por_fecha_hoy(iters, cfg):
    h = hoy(cfg.logic["timezone"])
    for it in iters:
        s = parse_azure_datetime(it.get("start"))
        f = parse_azure_datetime(it.get("finish"))
        if s and f and s.date() <= h <= f.date():
            return it
    return None


def resolver_iteracion(cfg, cliente):
    """Devuelve (iteracion_actual, pi_path, iteraciones_equipo).
    - Si azure.iteration_path es una ruta concreta, esa manda.
    - Si es 'CURRENT' o vacío, usa las iteraciones del equipo para hallar la
      que está en curso (por timeframe o por fechas)."""
    proj = cfg.azure["project"]
    it_cfg = cfg.azure.get("iteration_path", "").strip()
    team = cfg.azure.get("team", "").strip()

    iters = []
    if team:
        try:
            iters = cliente.get_team_iterations(team)
        except Exception as e:
            print(f"   [aviso] No pude leer las iteraciones del equipo '{team}': {e}")

    actual = None
    if it_cfg and it_cfg.upper() != "CURRENT":
        actual = Q.normalizar_iter_path(cfg, it_cfg)
    elif iters:
        cur = [it for it in iters if it.get("timeframe") == "current"]
        elegido = cur[0] if cur else _iter_por_fecha_hoy(iters, cfg)
        elegido = elegido or (iters[-1] if iters else None)
        if elegido:
            actual = Q.normalizar_iter_path(cfg, elegido["path"])

    if not actual:
        return None, None, iters

    padre = actual.rsplit("\\", 1)[0]
    pi = padre if (padre and padre != proj and "\\" in padre) else actual
    return actual, pi, iters


def main():
    cfg = Config("config.json")
    cliente = AzureDevOpsClient(cfg)

    # Utilidad: descubrir reference names para llenar el config
    if len(sys.argv) >= 3 and sys.argv[1] == "--dump-fields":
        cliente.dump_fields(int(sys.argv[2]))
        return

    # Lista las rutas de área tal como Azure las tiene escritas.
    # Uso: python run_daily.py --areas
    if len(sys.argv) >= 2 and sys.argv[1] == "--areas":
        listar_areas(cfg, cliente)
        return

    # Diagnóstico: muestra los NOMBRES REALES de tipos y estados del proyecto,
    # para saber exactamente qué poner en config.json. Uso: python run_daily.py --diagnose
    if len(sys.argv) >= 2 and sys.argv[1] == "--diagnose":
        diagnosticar(cfg, cliente)
        return

    # Diagnostica por qué un item NO aparece. Uso: python run_daily.py --why 63127
    if len(sys.argv) >= 3 and sys.argv[1] == "--why":
        diagnosticar_item(cfg, cliente, int(sys.argv[2]))
        return

    # Lista los equipos del proyecto. Uso: python run_daily.py --teams
    if len(sys.argv) >= 2 and sys.argv[1] == "--teams":
        print(">> Equipos del proyecto (usa el nombre EXACTO en azure.team):\n")
        for nombre in cliente.get_teams():
            print(f"   {nombre}")
        return

    # Escanea cómo están etiquetadas las Task por Área e Iteración (sprint).
    # Uso: python run_daily.py --scopes
    if len(sys.argv) >= 2 and sys.argv[1] == "--scopes":
        escanear_scopes(cfg, cliente)
        return

    print(">> Conectando a Azure DevOps...")
    campos = Q.campos_solicitados(cfg)

    # --- 1) Resolver la iteración actual y el PI que la contiene ---------
    actual_path, pi_path, iters_equipo = resolver_iteracion(cfg, cliente)
    if not pi_path:
        print("[ERROR] No pude determinar la iteración. Revisa azure.team o pon")
        print("        azure.iteration_path con una ruta como")
        print("        'Proceso de Trabajo con SAFe\\\\2026\\\\PI_Q2\\\\IT_2.3'.")
        return
    print(f"   Iteración en curso: {actual_path}")
    print(f"   PI (para el selector): {pi_path}")

    # --- 2) Traer las Task del PI completo (todas sus iteraciones) -------
    wiql_tasks = Q.wiql_tasks_bajo_iteracion(cfg, pi_path)
    print(f"   WIQL: {wiql_tasks}")
    ids_tareas = cliente.run_wiql(wiql_tasks)
    tareas_raw = cliente.get_work_items(ids_tareas, campos) if ids_tareas else []
    tareas = [Q.normalizar(wi, cfg) for wi in tareas_raw]
    print(f"   Task en el PI: {len(tareas)}")

    # --- 3) Subir a los contenedores padre (cualquier tipo) -------------
    ids_padres = sorted({t["parent"] for t in tareas if t["parent"]})
    contenedores_raw = cliente.get_work_items(ids_padres, campos) if ids_padres else []
    contenedores = {wi["id"]: Q.normalizar(wi, cfg) for wi in contenedores_raw}
    cerrados_estado = set(cfg.states["closed"])

    # --- 3b) Subir un nivel más: Features padre de las HDU ---------------
    hdu_tipo = cfg.wit["user_story"]
    hdus_todas = [c for c in contenedores.values() if c["tipo"] == hdu_tipo]
    ids_features = sorted({h["parent"] for h in hdus_todas if h["parent"]})
    features_raw = cliente.get_work_items(ids_features, campos) if ids_features else []
    features = {wi["id"]: Q.normalizar(wi, cfg) for wi in features_raw}
    print(f"   HDU con Feature padre: {len(ids_features)} -> {len(features)} Features")

    # --- 4) Iteraciones a mostrar en el selector (ordenadas) ------------
    orden = []
    if iters_equipo:
        for it in iters_equipo:
            p = Q.normalizar_iter_path(cfg, it["path"])
            if p.startswith(pi_path):
                orden.append(p)
    if not orden:  # respaldo: las iteraciones presentes en las Task
        orden = sorted({t["iteration"] for t in tareas if t["iteration"]})
    if actual_path not in orden:
        orden.insert(0, actual_path)

    # Roster de nombres (del config) + personas con Task fuera del roster.
    roster_cfg = cfg.azure.get("team_roster", [])
    asignados = {t["asignado"] for t in tareas
                 if t["asignado"] and t["asignado"] != "Sin asignar"}
    print(f"   Roster configurado: {len(roster_cfg)} · "
          f"asignados distintos en el PI: {len(asignados)}")
    print("   Task por iteración:")
    for path in orden:
        print(f"     {path.split(chr(92))[-1]}: "
              f"{len([t for t in tareas if t['iteration'] == path])}")

    # --- 5) Construir datos por iteración (faltantes + tarjetas por dev) --
    # Rango real (inicio/fin) de cada iteración, para capacidad y timeline.
    horas_por_dia = cfg.logic.get("hours_per_day", 8)
    horas_default = cfg.logic.get("default_iteration_hours", 120)
    rango_iters = {}
    for it in (iters_equipo or []):
        p = Q.normalizar_iter_path(cfg, it["path"])
        rango_iters[p] = (fecha_calendario(it.get("start")), fecha_calendario(it.get("finish")))

    datos = {}
    for path in orden:
        tareas_it = [t for t in tareas if t["iteration"] == path]
        por_padre_it = agrupar_por_padre(tareas_it)
        activos_it = [c for c in contenedores.values()
                      if c["id"] in por_padre_it and c["estado"] not in cerrados_estado]
        activos_hdu_it = [c for c in activos_it if c["tipo"] == hdu_tipo]
        activos_otros_it = [c for c in activos_it if c["tipo"] != hdu_tipo]
        df_it = dashboard.construir_faltantes(activos_hdu_it, por_padre_it, cfg)
        df_otros_it = dashboard.construir_faltantes(activos_otros_it, por_padre_it, cfg)

        hdus_it = [h for h in hdus_todas if h["iteration"] == path]
        por_feature_it = agrupar_por_padre(hdus_it)
        features_activos_it = [f for f in features.values()
                                if f["id"] in por_feature_it and f["estado"] not in cerrados_estado]
        df_features_it = dashboard.construir_faltantes(features_activos_it, por_feature_it, cfg)

        ini_it, fin_it = rango_iters.get(path, (None, None))
        if ini_it and fin_it:
            horas_disp = dias_habiles(ini_it, fin_it) * horas_por_dia
        else:
            horas_disp = horas_default

        datos[path] = {
            "faltantes": dashboard.faltantes_registros(df_it),
            "faltantes_otros": dashboard.faltantes_registros(df_otros_it),
            "faltantes_features": dashboard.faltantes_registros(df_features_it),
            "devs": daily_scrum.por_dev_filtros(tareas_it, cfg, roster_cfg, horas_disp),
            "rango": {"inicio": ini_it.isoformat() if ini_it else None,
                      "fin": fin_it.isoformat() if fin_it else None,
                      "horas_disponibles": horas_disp},
        }

    # === TAREA 1: Excel de contenedores cerrados en 24h (todo el PI) =====
    cutoff = parse_azure_datetime(cutoff_utc(cfg.logic["lookback_hours"]))
    por_padre_all = agrupar_por_padre(tareas)
    cont_cerrados = []
    for c in contenedores.values():
        if c["estado"] in cerrados_estado:
            ref = c["closed_date"] or c["changed_date"]
            if ref and ref >= cutoff:
                cont_cerrados.append(c)
    registros = excel_writer.construir_registros(cont_cerrados, por_padre_all)
    if registros:
        nuevos, total = excel_writer.upsert_excel(cfg.output["closed_report_xlsx"], registros)
        print(f">> [T1] Excel actualizado: +{nuevos} filas, {total} en total "
              f"-> {cfg.output['closed_report_xlsx']}")
    else:
        print(">> [T1] No hubo contenedores cerrados en la ventana; Excel sin cambios.")

    # === TAREA 2: CSV Power BI con TODAS las iteraciones ================
    filas_csv = []
    for path in orden:
        df = dashboard.construir_faltantes(
            [c for c in contenedores.values()
             if c["id"] in agrupar_por_padre([t for t in tareas if t["iteration"] == path])
             and c["estado"] not in cerrados_estado],
            agrupar_por_padre([t for t in tareas if t["iteration"] == path]), cfg)
        if not df.empty:
            df = df.copy(); df.insert(0, "iteracion", path.split("\\")[-1])
            filas_csv.append(df)
    import pandas as pd
    df_csv = pd.concat(filas_csv, ignore_index=True) if filas_csv else pd.DataFrame()
    dashboard.exportar_powerbi_csv(df_csv, cfg.output["powerbi_export_csv"])
    print(f">> [T2] CSV para Power BI ({len(df_csv)} filas) -> {cfg.output['powerbi_export_csv']}")

    # === TAREA 3: Daily de la iteración EN CURSO (consola + Markdown) ===
    tareas_actual = [t for t in tareas if t["iteration"] == actual_path]
    clasificado = daily_scrum.clasificar(tareas_actual, cfg)
    with open(cfg.output["daily_markdown"], "w", encoding="utf-8") as f:
        f.write(daily_scrum.render_markdown(clasificado, cfg))
    print(daily_scrum.render_consola(clasificado, cfg))
    print(f">> [T3] Markdown de la Daily -> {cfg.output['daily_markdown']}")

    # === Spotlight: todo lo asignado a una persona en el PI (p.ej. Laura) ==
    laura = []
    sp_email = cfg.azure.get("spotlight_email", "").strip()
    sp_nombre = cfg.azure.get("spotlight_nombre", sp_email) or "—"
    if sp_email:
        try:
            desde = (cfg.azure.get("spotlight_since", "2026-01-01").strip() or "2026-01-01")
            since_iso = f"{desde}T00:00:00Z"
            ids_sp = cliente.run_wiql(Q.wiql_spotlight(cfg, sp_email, since_iso))
            sp_raw = cliente.get_work_items(ids_sp, campos) if ids_sp else []
            sp_items = [Q.normalizar(wi, cfg) for wi in sp_raw]
            # Hijas de esos items (cualquier tipo)
            q_hijos = Q.wiql_hijos_de(cfg, ids_sp)
            ids_h = cliente.run_wiql(q_hijos) if q_hijos else []
            hijos = [Q.normalizar(wi, cfg) for wi in cliente.get_work_items(ids_h, campos)] if ids_h else []
            hijos_por_padre = agrupar_por_padre(hijos)
            corte24 = parse_azure_datetime(cutoff_utc(24))
            recientes = 0
            for it in sorted(sp_items, key=lambda x: x["creado"] or parse_azure_datetime("1970-01-01T00:00:00Z"), reverse=True):
                hijos_it = hijos_por_padre.get(it["id"], [])
                mods = [h["changed_date"] for h in hijos_it if h["changed_date"]]
                mod_hija = max(mods).isoformat() if mods else None
                # ¿Recién creado o recién asignado a ella (últimas 24 h)?
                reciente = bool(it["creado"] and it["creado"] >= corte24)
                if not reciente:
                    try:
                        ad = parse_azure_datetime(cliente.asignado_desde(it["id"], sp_email))
                        reciente = bool(ad and ad >= corte24)
                    except Exception:
                        pass
                if reciente:
                    recientes += 1
                laura.append({
                    "id": it["id"], "tipo": it["tipo"], "titulo": it["titulo"],
                    "creado": it["creado"].strftime("%Y-%m-%d") if it["creado"] else None,
                    "mod_hija": mod_hija,
                    "sin_hijas": len(hijos_it) == 0,
                    "reciente": reciente,
                    "hijos": [{
                        "id": h["id"], "titulo": h["titulo"], "asignado": h["asignado"],
                        "estado": h["estado"], "horas": h["horas"], "horas_reales": h["horas_reales"],
                    } for h in hijos_it],
                })
            print(f"   Spotlight ({sp_nombre}): {len(laura)} items ({recientes} nuevo/s en 24 h)")
        except Exception as e:
            print(f"   [aviso] No pude construir la sección de {sp_nombre}: {e}")

    # === Dashboard interactivo (selector de iteración) =================
    from urllib.parse import quote as _q
    wi_base = (cfg.azure["organization_url"].rstrip("/") + "/"
               + _q(cfg.azure["project"], safe="") + "/_workitems/edit/")
    dashboard.generar_html_interactivo(
        datos, orden, actual_path,
        cfg.output["dashboard_html"], hoy(cfg.logic["timezone"]).isoformat(), wi_base,
        laura=laura, laura_nombre=sp_nombre,
        pat_expira=cfg.azure.get("pat_expira"))
    print(f">> [T2/T3] Dashboard interactivo -> {cfg.output['dashboard_html']}")

    # --- Resumen de exclusiones (iteración en curso) --------------------
    sin_padre = sum(1 for t in tareas_actual if not t["parent"])
    sin_asignar = sum(1 for t in tareas_actual if t["asignado"] == "Sin asignar")
    sin_fecha_fin = sum(1 for t in tareas_actual
                        if t["estado"] not in cerrados_estado and not t["fecha_fin"])
    print("\n--- Resumen (iteración en curso) ---")
    print(f"   Task en curso sin padre: {sin_padre}")
    print(f"   Task sin responsable asignado: {sin_asignar}")
    print(f"   Task abiertas sin FechaFin (no evaluables como retraso): {sin_fecha_fin}")
    print("   Listo.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
