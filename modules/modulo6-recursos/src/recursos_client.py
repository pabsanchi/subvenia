"""
Módulo 6: Cliente de recursos sociales del portal de datos abiertos de Valencia.

Descarga los datasets GeoJSON de la categoría 'Sociedad y Bienestar' del portal
opendata.vlci.valencia.es (servidos desde geoportal.valencia.es) y los unifica
en un único DataFrame con coordenadas, nombre y titular de cada recurso.

Fuente: Portal de Datos Abiertos del Ayuntament de València (CC BY 4.0)
URL:    https://opendata.vlci.valencia.es
"""
import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

GEOPORTAL_BASE = "https://geoportal.valencia.es/apps/OpenData/SociedadBienestar"

# Datasets confirmados del portal. La clave es el nombre de categoría que se
# muestra al usuario; el valor es el nombre del fichero GeoJSON en el geoportal.
# Los ficheros con nombre tentativo (marcados con #?) se intentan cargar y se
# omiten silenciosamente si no existen, sin interrumpir el resto.
DATASETS: dict[str, str] = {
    "Mayores": "SS_MAYORES.json",
    "Personas sin Techo": "SS_SINTECHO.json",
    "Mujeres": "SS_MUJERES.json",
    "Inmigrantes": "SS_MIGRANTES.json",
    "Minorías Étnicas": "SS_ETNICAS.json",
    "Enfermedad Mental": "SS_ENFERMEDAD_MENTAL.json",
    "Discapacidad Sensorial": "SS_DISCAPACIDAD_S.json",
    "Discapacidad Intelectual": "SS_DISCAPACIDAD_I.json",
    "Discapacidad Física": "SS_DISCAPACIDAD_F.json",
    "Discapacidad (General)": "SS_DISCAPACIDAD.json",
    "Personas Dependientes": "SS_DEPENDENCIA.json",
    "Presos y Exreclusos": "SS_PRESOS.json",
    "Familias y Menores": "SS_FAMILIA_MENOR.json",
    "Trastornos Adictivos": "SS_ADICCIONES.json",
    "Jóvenes": "SS_JUVENTUD.json",
    "Cooperación Internacional": "SS_COOP_INTER.json",
    "Toda la Población": "SS_TODA_POBLACION.json",
}

# Colores HEX por categoría para el mapa
CATEGORY_COLORS: dict[str, str] = {
    "Mayores": "#E67E22",
    "Personas sin Techo": "#E74C3C",
    "Mujeres": "#E91E8C",
    "Inmigrantes": "#3498DB",
    "Minorías Étnicas": "#9B59B6",
    "Enfermedad Mental": "#1ABC9C",
    "Discapacidad Sensorial": "#F39C12",
    "Discapacidad Intelectual": "#F1C40F",
    "Discapacidad Física": "#F0A500",
    "Discapacidad (General)": "#D4AC0D",
    "Personas Dependientes": "#A04000",
    "Presos y Exreclusos": "#95A5A6",
    "Familias y Menores": "#2ECC71",
    "Trastornos Adictivos": "#8E44AD",
    "Jóvenes": "#17A589",
    "Cooperación Internacional": "#2980B9",
    "Toda la Población": "#27AE60",
}
DEFAULT_COLOR = "#7F8C8D"


def _fetch_dataset(categoria: str, filename: str) -> list[dict[str, Any]]:
    url = f"{GEOPORTAL_BASE}/{filename}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    records = []
    for feat in resp.json().get("features", []):
        props = feat.get("properties") or {}
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        records.append({
            "categoria": categoria,
            "descripcion": (props.get("descripcion") or "").strip().title(),
            "titularidad": (props.get("titularidad") or "").strip(),
            "lat": coords[1] if len(coords) > 1 else None,
            "lon": coords[0] if len(coords) > 0 else None,
            "color": CATEGORY_COLORS.get(categoria, DEFAULT_COLOR),
        })
    return records


def load_all_resources() -> pd.DataFrame:
    """
    Descarga todos los datasets SS_* y devuelve un DataFrame unificado.
    Los datasets que fallen (404, timeout, etc.) se omiten sin interrumpir
    la carga de los demás.
    """
    all_records: list[dict] = []
    loaded = []
    failed = []

    for categoria, filename in DATASETS.items():
        try:
            records = _fetch_dataset(categoria, filename)
            all_records.extend(records)
            loaded.append(f"{categoria} ({len(records)})")
        except Exception as e:
            failed.append(categoria)
            logger.debug(f"Dataset '{categoria}' no disponible ({filename}): {e}")

    if loaded:
        logger.info(f"Recursos cargados: {', '.join(loaded)}")
    if failed:
        logger.debug(f"Datasets omitidos (no disponibles): {', '.join(failed)}")

    if not all_records:
        return pd.DataFrame(columns=["categoria", "descripcion", "titularidad", "lat", "lon", "color"])

    df = pd.DataFrame(all_records)
    df = df[df["descripcion"].str.strip() != ""].reset_index(drop=True)
    return df
