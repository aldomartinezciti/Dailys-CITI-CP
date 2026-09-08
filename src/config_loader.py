"""
config_loader.py
----------------
Carga y valida el config.json. Centraliza el acceso a las variables que
cambian cada PI (PAT, organización, proyecto, mapeo de campos, etc.) para
que nunca haya que tocar el código fuente.
"""
import json
import os
from pathlib import Path


class Config:
    def __init__(self, ruta="config.json"):
        ruta = Path(ruta)
        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo de configuración: {ruta.resolve()}"
            )
        with open(ruta, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        self._validar()

    # --- accesos rápidos ---------------------------------------------------
    @property
    def azure(self):        return self._data["azure"]

    @property
    def wit(self):          return self._data["work_item_types"]

    @property
    def states(self):       return self._data["states"]

    @property
    def fields(self):       return self._data["fields"]

    @property
    def logic(self):        return self._data["logic"]

    @property
    def output(self):       return self._data["output"]

    def field(self, clave_logica):
        """Devuelve el reference name real de Azure a partir del nombre lógico."""
        return self._data["fields"][clave_logica]

    # --- validación --------------------------------------------------------
    def _validar(self):
        az = self._data.get("azure", {})
        if "TU_ORGANIZACION" in az.get("organization_url", ""):
            print("[AVISO] Configura 'organization_url' en config.json.")
        if az.get("personal_access_token", "").startswith("PEGA_AQUI"):
            raise ValueError("Falta el PAT en config.json (azure.personal_access_token).")

        # Aseguramos que las carpetas de salida existan
        for ruta in self._data.get("output", {}).values():
            carpeta = os.path.dirname(ruta)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
