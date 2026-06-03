"""
Módulo 5: Cliente de búsqueda filtrada de convocatorias en MongoDB.

Consulta la colección 'convocatorias' con filtros estructurados basados en
los campos booleanos que Gemini extrajo de cada convocatoria. La lógica de
filtrado es OR dentro del perfil del usuario (cualquier criterio coincidente
devuelve la convocatoria) y AND para los filtros adicionales (tipo de ayuda,
ámbito geográfico).
"""
import os
import re
import logging
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR.parent.parent / ".env"
DB_NAME = "subvenia"
COLLECTION_NAME = "convocatorias"
BDNS_PORTAL_URL = "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatorias"

# ---------------------------------------------------------------------------
# Etiquetas legibles para los filtros de la UI
# ---------------------------------------------------------------------------
SITUACION_LABORAL: dict[str, str] = {
    "desempleado": "Desempleado/a",
    "autonomo_o_emprendedor": "Autónomo/Emprendedor",
    "jubilado_o_pensionista": "Jubilado/Pensionista",
    "empleado": "Empleado/a",
    "empleado_hogar": "Empleado/a del hogar",
}
SITUACION_FAMILIAR: dict[str, str] = {
    "familia_numerosa": "Familia numerosa",
    "familia_monoparental_o_soltero": "Familia monoparental / Soltero-a",
    "familia_con_dependientes": "Con personas dependientes a cargo",
    "familia_acogedora": "Familia acogedora",
}
VULNERABILIDAD: dict[str, str] = {
    "riesgo_exclusion_pobreza": "Riesgo de exclusión o pobreza",
    "discapacidad_o_dependencia": "Discapacidad o dependencia",
    "victima_violencia_genero": "Víctima de violencia de género",
    "victima_terrorismo": "Víctima de terrorismo",
}
COLECTIVOS: dict[str, str] = {
    "jovenes": "Jóvenes",
    "personas_mayores": "Personas mayores",
    "menores": "Menores de edad",
    "estudiantes_o_investigadores": "Estudiantes / Investigadores",
    "pymes_o_cooperativas": "PYMES / Cooperativas",
    "sector_primario_agri_ganadero": "Sector primario / Agrícola",
}
AID_TYPES: dict[str, str] = {
    "subvencion": "Subvención",
    "prestacion": "Prestación",
    "bonificacion": "Bonificación",
    "deduccion_fiscal": "Deducción fiscal",
    "beca": "Beca",
    "microcredito": "Microcrédito",
    "ayuda_alquiler": "Ayuda al alquiler",
    "ayuda_energia": "Ayuda a la energía",
    "ayuda_transporte": "Ayuda al transporte",
    "ayuda_alimentacion": "Ayuda a la alimentación",
}
GEO_LEVELS: dict[str, str] = {
    "autonomico": "Autonómico",
    "provincial": "Provincial",
    "municipal": "Municipal",
    "nacional": "Nacional",
    "europeo": "Europeo",
}


def _get_client() -> MongoClient:
    load_dotenv(ENV_PATH)
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise ValueError("MONGO_URI no encontrada en .env")
    return MongoClient(uri, serverSelectionTimeoutMS=8000)


def buscar_convocatorias(
    situacion_laboral: list[str] | None = None,
    situacion_familiar: list[str] | None = None,
    vulnerabilidad: list[str] | None = None,
    colectivos: list[str] | None = None,
    aid_types: list[str] | None = None,
    geo_level: str | None = None,
    texto: str | None = None,
    max_results: int = 60,
    exclude_closed: bool = True,
) -> list[dict[str, Any]]:
    """
    Devuelve convocatorias que coincidan con el perfil del usuario.

    Lógica OR: si el usuario selecciona varios criterios de perfil, se
    devuelven convocatorias que apliquen a CUALQUIERA de ellos. Un jubilado
    desempleado verá tanto ayudas para jubilados como para desempleados.

    Parámetros
    ----------
    situacion_laboral : lista de claves de SITUACION_LABORAL
    situacion_familiar : lista de claves de SITUACION_FAMILIAR
    vulnerabilidad : lista de claves de VULNERABILIDAD
    colectivos : lista de claves de COLECTIVOS
    aid_types : lista de claves de AID_TYPES (requiere campo `aid_type` en doc)
    geo_level : clave de GEO_LEVELS (requiere campo `geographic_scope.level`)
    texto : texto libre para búsqueda por regex en `descripcion`
    max_results : límite de resultados devueltos
    exclude_closed : si True (defecto), excluye documentos con status='cerrada'
    """
    query: dict[str, Any] = {}
    or_conditions = []

    for field in (situacion_laboral or []):
        or_conditions.append({f"beneficiaries.situacion_laboral.{field}": True})
    for field in (situacion_familiar or []):
        or_conditions.append({f"beneficiaries.situacion_familiar.{field}": True})
    for field in (vulnerabilidad or []):
        or_conditions.append({f"beneficiaries.vulnerabilidad.{field}": True})
    for field in (colectivos or []):
        or_conditions.append({f"beneficiaries.colectivos_generales.{field}": True})

    if or_conditions:
        query["$or"] = or_conditions

    if aid_types:
        query["aid_type"] = {"$in": aid_types}

    if geo_level:
        query["geographic_scope.level"] = geo_level

    if texto and texto.strip():
        safe_texto = re.escape(texto.strip())
        query["descripcion"] = {"$regex": safe_texto, "$options": "i"}

    # Excluir convocatorias explícitamente cerradas a nivel de BD.
    # Los documentos con status=null (deadline no parseable) se filtran
    # en la capa UI con get_status() para capturar los derivados-cerrados.
    if exclude_closed:
        query["status"] = {"$ne": "cerrada"}

    projection = {
        "_id": 1,
        "descripcion": 1,
        "descripcionLeng": 1,
        "numeroConvocatoria": 1,
        "deadline": 1,
        "status": 1,
        "aid_type": 1,
        "geographic_scope": 1,
        "nivel3": 1,
        "beneficiaries": 1,
    }

    client = _get_client()
    try:
        col = client[DB_NAME][COLLECTION_NAME]
        return list(col.find(query, projection).limit(max_results))
    except Exception as e:
        logger.error(f"Error en búsqueda MongoDB: {e}")
        return []
    finally:
        client.close()


def get_status(doc: dict) -> tuple[str, str]:
    """
    Devuelve (status_key, status_label) para un documento.

    Si el campo `status` existe (docs procesados con la versión corregida de
    analyze_gemini.py), lo usa directamente. Si no, lo deriva de `deadline`:
    intenta parsear la fecha con dateparser (soporta YYYY-MM-DD y formatos
    en español como "15 de junio de 2026") y la compara con hoy.
    """
    status = doc.get("status")
    if status:
        labels = {
            "abierta": ("abierta", "Abierta"),
            "cerrada": ("cerrada", "Cerrada"),
            "proximamente": ("proximamente", "Próximamente"),
            "permanente": ("permanente", "Permanente"),
        }
        return labels.get(status, (status, status.capitalize()))

    deadline = doc.get("deadline", "")
    if deadline and deadline not in ("desconocido", ""):
        try:
            import dateparser
            # Sin languages=["es"] para que el parser ISO (YYYY-MM-DD) funcione;
            # dateparser lo detecta automáticamente en ambos formatos.
            parsed = dateparser.parse(str(deadline))
            if parsed:
                today = date.today()
                if parsed.date() >= today:
                    return ("abierta", "Abierta")
                else:
                    return ("cerrada", "Cerrada")
        except Exception:
            pass

    return ("desconocida", "Estado desconocido")


def get_matching_tags(doc: dict, selected_keys: dict[str, list[str]]) -> list[str]:
    """
    Dado un documento y los criterios que el usuario seleccionó,
    devuelve las etiquetas que coinciden para mostrarlas en la tarjeta.
    """
    labels: dict[str, str] = {}
    labels.update(SITUACION_LABORAL)
    labels.update(SITUACION_FAMILIAR)
    labels.update(VULNERABILIDAD)
    labels.update(COLECTIVOS)

    matching = []
    benef = doc.get("beneficiaries", {})
    for group_key, selected in selected_keys.items():
        group_data = benef.get(group_key, {})
        for field in selected:
            if group_data.get(field):
                matching.append(labels.get(field, field))
    return matching
