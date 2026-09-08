"""
azure_client.py
---------------
Wrapper delgado sobre la API REST de Azure DevOps.

Estrategia de jerarquía:
- En vez de recorrer las relaciones (System.LinkTypes.Hierarchy-Forward) HDU por
  HDU, consultamos las Tareas directamente por el campo System.Parent con un
  IN (...). Es una sola llamada, es exacto y evita N peticiones individuales.
"""
import requests
from urllib.parse import quote


class AzureDevOpsClient:
    def __init__(self, cfg):
        self.cfg = cfg
        az = cfg.azure
        self.org = az["organization_url"].rstrip("/")
        self.project = az["project"]
        self.api = az.get("api_version", "7.1")
        self.session = requests.Session()
        # Autenticación PAT: usuario vacío + PAT como password (Basic Auth)
        self.session.auth = ("", az["personal_access_token"])
        self.session.headers.update({"Content-Type": "application/json"})

    # --- helpers de URL ----------------------------------------------------
    def _url_proyecto(self, path):
        proj = quote(self.project, safe="")
        return f"{self.org}/{proj}/_apis/{path}?api-version={self.api}"

    def _url_org(self, path):
        return f"{self.org}/_apis/{path}?api-version={self.api}"

    # --- WIQL --------------------------------------------------------------
    def run_wiql(self, query):
        """Ejecuta una consulta WIQL plana y devuelve la lista de IDs."""
        url = self._url_proyecto("wit/wiql")
        r = self.session.post(url, json={"query": query})
        self._check(r, "WIQL")
        data = r.json()
        return [w["id"] for w in data.get("workItems", [])]

    # --- Batch de work items ----------------------------------------------
    def get_work_items(self, ids, fields):
        """Trae los campos indicados para una lista de IDs (en lotes de 200)."""
        if not ids:
            return []
        resultados = []
        for i in range(0, len(ids), 200):
            lote = ids[i:i + 200]
            url = self._url_org("wit/workitemsbatch")
            body = {"ids": lote, "fields": fields}
            r = self.session.post(url, json=body)
            self._check(r, "workitemsbatch")
            resultados.extend(r.json().get("value", []))
        return resultados

    # --- Miembros del equipo ----------------------------------------------
    def get_team_members(self, team):
        """Devuelve los nombres (displayName) de los integrantes del equipo."""
        proj = quote(self.project, safe="")
        tm = quote(team, safe="")
        url = (f"{self.org}/_apis/projects/{proj}/teams/{tm}/members"
               f"?api-version={self.api}")
        r = self.session.get(url)
        self._check(r, "team_members")
        nombres = []
        for m in r.json().get("value", []):
            ident = m.get("identity", m)
            nombre = ident.get("displayName") or ident.get("uniqueName")
            if nombre:
                nombres.append(nombre)
        return nombres

    # --- Equipos del proyecto ---------------------------------------------
    def get_teams(self):
        """Lista los equipos del proyecto (nombre exacto para el macro
        @CurrentIteration y para teamsettings/iterations)."""
        proj = quote(self.project, safe="")
        url = f"{self.org}/_apis/projects/{proj}/teams?api-version={self.api}"
        r = self.session.get(url)
        self._check(r, "teams")
        return [t.get("name") for t in r.json().get("value", [])]

    # --- Iteraciones del equipo (sprints) ---------------------------------
    def get_team_iterations(self, team):
        """Devuelve las iteraciones asignadas al equipo, con su timeframe
        (past/current/future) y fechas. Requiere azure.team en el config."""
        proj = quote(self.project, safe="")
        tm = quote(team, safe="")
        url = (f"{self.org}/{proj}/{tm}/_apis/work/teamsettings/iterations"
               f"?api-version={self.api}")
        r = self.session.get(url)
        self._check(r, "team_iterations")
        out = []
        for it in r.json().get("value", []):
            attr = it.get("attributes", {}) or {}
            out.append({
                "name": it.get("name"),
                "path": it.get("path"),
                "timeframe": attr.get("timeFrame"),
                "start": attr.get("startDate"),
                "finish": attr.get("finishDate"),
            })
        return out

    # --- Áreas (classification nodes) -------------------------------------
    def get_areas(self, depth=6):
        """Devuelve el árbol de áreas del proyecto."""
        proj = quote(self.project, safe="")
        url = (f"{self.org}/{proj}/_apis/wit/classificationnodes/areas"
               f"?$depth={depth}&api-version={self.api}")
        r = self.session.get(url)
        self._check(r, "areas")
        return r.json()

    # --- Utilidad para descubrir reference names --------------------------
    def dump_fields(self, work_item_id):
        """Imprime todos los reference names y valores de un work item.
        Úsalo una vez para llenar el mapeo 'fields' del config.json."""
        url = self._url_org(f"wit/workitems/{work_item_id}")
        r = self.session.get(url)
        self._check(r, "get_work_item")
        campos = r.json().get("fields", {})
        for k in sorted(campos.keys()):
            print(f"{k:45s} = {campos[k]}")
        return campos

    def get_all_fields(self, work_item_id):
        """Devuelve el dict de campos crudos de un work item (sin imprimir)."""
        url = self._url_org(f"wit/workitems/{work_item_id}")
        r = self.session.get(url)
        self._check(r, "get_work_item")
        return r.json().get("fields", {})

    def asignado_desde(self, work_item_id, email):
        """Devuelve el ISO de la última vez que el item cambió su 'Assigned To'
        a 'email' (según el historial), o None. Sirve para detectar si se le
        asignó recientemente a alguien."""
        url = self._url_org(f"wit/workItems/{work_item_id}/updates")
        r = self.session.get(url)
        self._check(r, "workitem_updates")
        ult = None
        for up in r.json().get("value", []):
            f = up.get("fields", {}) or {}
            a = f.get("System.AssignedTo")
            if isinstance(a, dict):
                nv = a.get("newValue")
                un = nv.get("uniqueName") if isinstance(nv, dict) else None
                if un and un.lower() == email.lower():
                    cd = f.get("System.ChangedDate")
                    ts = cd.get("newValue") if isinstance(cd, dict) else None
                    ult = ts or up.get("revisedDate") or ult
        return ult

    # --- manejo de errores -------------------------------------------------
    @staticmethod
    def _check(resp, contexto):
        if resp.status_code >= 400:
            raise RuntimeError(
                f"[Azure/{contexto}] HTTP {resp.status_code}: {resp.text[:500]}"
            )
