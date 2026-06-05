"""
Módulo 6: Cliente de recursos sociales del portal de datos abiertos de Valencia.

Obtiene los datasets de la categoría 'Sociedad y Bienestar' a través de la API
datastore de CKAN (opendata.vlci.valencia.es) y los unifica en un único DataFrame
con coordenadas WGS84, nombre y titular de cada recurso.

Las coordenadas originales vienen en ETRS89/UTM Zona 30N (EPSG:25830) y se
convierten a WGS84 (EPSG:4326) con pyproj para el renderizado en el mapa.

Fuente: Portal de Datos Abiertos del Ayuntament de València (CC BY 4.0)
URL:    https://opendata.vlci.valencia.es
"""
import logging
from typing import Any

import pandas as pd
import requests
from pyproj import Transformer

logger = logging.getLogger(__name__)

CKAN_DATASTORE = "https://opendata.vlci.valencia.es/api/3/action/datastore_search"

# Transformer UTM Zona 30N (EPSG:25830) → WGS84 (EPSG:4326), reutilizado por todos los datasets.
_UTM_TO_WGS84 = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)

# Mapeo categoría → resource_id del datastore CKAN.
# Los IDs son estables mientras no se elimine/recree el recurso en el portal.
DATASETS: dict[str, str] = {
    "Mayores":                   "928f8343-61fa-4c1f-93db-5c7747c1e7cc",
    "Personas sin Techo":        "e3217586-fade-45ab-b14e-fd7a5bab2b99",
    "Mujeres":                   "b726e19f-44f5-4485-b607-b7fa98ade1d8",
    "Inmigrantes":               "43754ab5-5b27-4591-be3b-098196ddb4e3",
    "Minorías Étnicas":          "caeecfe8-f39d-4045-9a87-8c38fc27b215",
    "Enfermedad Mental":         "a8aa4c8f-af7b-4d34-8072-fc1f1ac5a195",
    "Discapacidad Sensorial":    "3150e05d-a247-4bf1-9e63-8655a983050c",
    "Discapacidad Intelectual":  "4d3fcec0-2ab6-4553-8209-cf278e09215e",
    "Discapacidad Física":       "b16e5881-fdde-4f7f-b2e5-1df3ef946aaf",
    "Discapacidad (General)":    "ccc49142-a090-47f3-bff5-92982da94d59",
    "Personas Dependientes":     "4543a0c4-acb8-45ce-af91-907c50bb3968",
    "Presos y Exreclusos":       "d1ae6303-4119-4f1c-8d3e-c666e5f54aba",
    "Familias y Menores":        "e6e94aa5-1b56-495b-b32f-bad3545dda86",
    "Trastornos Adictivos":      "5fb5572d-2b00-4d25-b2c1-677f086971d9",
    "Jóvenes":                   "b7e32fe0-f3c9-4a1d-9c7b-026955df810a",
    "Cooperación Internacional": "e9e982fa-8e86-41d2-8d0e-be143e829d5f",
    "Toda la Población":         "5ed32dd3-98d2-4eb0-8ac4-dd95709eaca4",
}

# Colores HEX por categoría para el mapa
CATEGORY_COLORS: dict[str, str] = {
    "Mayores":                   "#E67E22",
    "Personas sin Techo":        "#E74C3C",
    "Mujeres":                   "#E91E8C",
    "Inmigrantes":               "#3498DB",
    "Minorías Étnicas":          "#9B59B6",
    "Enfermedad Mental":         "#1ABC9C",
    "Discapacidad Sensorial":    "#F39C12",
    "Discapacidad Intelectual":  "#F1C40F",
    "Discapacidad Física":       "#F0A500",
    "Discapacidad (General)":    "#D4AC0D",
    "Personas Dependientes":     "#A04000",
    "Presos y Exreclusos":       "#95A5A6",
    "Familias y Menores":        "#2ECC71",
    "Trastornos Adictivos":      "#8E44AD",
    "Jóvenes":                   "#17A589",
    "Cooperación Internacional": "#2980B9",
    "Toda la Población":         "#27AE60",
}
DEFAULT_COLOR = "#7F8C8D"


def _fetch_dataset(categoria: str, resource_id: str) -> list[dict[str, Any]]:
    records: list[dict] = []
    offset = 0
    limit = 1000

    while True:
        resp = requests.get(
            CKAN_DATASTORE,
            params={"resource_id": resource_id, "limit": limit, "offset": offset},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()["result"]
        batch = result["records"]
        if not batch:
            break

        for row in batch:
            x, y = row.get("X"), row.get("Y")
            lat, lon = None, None
            if x is not None and y is not None:
                try:
                    lon, lat = _UTM_TO_WGS84.transform(float(x), float(y))
                except Exception:
                    pass
            records.append({
                "categoria":   categoria,
                "descripcion": (row.get("descripcion") or "").strip().title(),
                "titularidad": (row.get("titularidad") or "").strip(),
                "lat": lat,
                "lon": lon,
                "color": CATEGORY_COLORS.get(categoria, DEFAULT_COLOR),
            })

        offset += limit
        if offset >= result["total"]:
            break

    return records


def load_all_resources() -> pd.DataFrame:
    """
    Descarga todos los datasets SS_* y devuelve un DataFrame unificado.
    Los datasets que fallen (timeout, error de red, etc.) se omiten sin
    interrumpir la carga de los demás.
    """
    all_records: list[dict] = []
    loaded = []
    failed = []

    for categoria, resource_id in DATASETS.items():
        try:
            records = _fetch_dataset(categoria, resource_id)
            all_records.extend(records)
            loaded.append(f"{categoria} ({len(records)})")
        except Exception as e:
            failed.append(categoria)
            logger.debug(f"Dataset '{categoria}' no disponible ({resource_id}): {e}")

    if loaded:
        logger.info(f"Recursos cargados: {', '.join(loaded)}")
    if failed:
        logger.debug(f"Datasets omitidos (no disponibles): {', '.join(failed)}")

    if not all_records:
        return pd.DataFrame(columns=["categoria", "descripcion", "titularidad", "lat", "lon", "color"])

    df = pd.DataFrame(all_records)
    df = df[df["descripcion"].str.strip() != ""].reset_index(drop=True)
    return df
