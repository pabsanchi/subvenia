"""
Módulo 2: Retroalimentación de campos Gemini en documentos existentes de MongoDB.

Los documentos procesados antes de la corrección de analyze_gemini.py carecen de
los campos `status`, `aid_type` y `granting_body_level`. Este script los deriva
a partir de los datos BDNS ya disponibles en MongoDB, sin necesidad de re-procesar
los PDFs con Gemini.

Lógica de derivación:
  - status            ← deadline  (dateparser: si la fecha pasó → cerrada, si no → abierta)
  - granting_body_level ← nivel1  (AUTONOMICA/LOCAL/ESTADO/OTROS + nivel2)
  - aid_type          ← descripcion (keyword matching por orden de especificidad)

Uso:
    python modules/modulo2-db/src/backfill_gemini_fields.py [--dry-run]

    --dry-run  Muestra qué se haría sin escribir nada en MongoDB.
"""
import os
import re
import sys
import logging
import argparse
from datetime import date
from pathlib import Path

import dateparser
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR.parent.parent / ".env"
DB_NAME = "subvenia"
COLLECTION_NAME = "convocatorias"

# ---------------------------------------------------------------------------
# Mapping nivel1 (BDNS) → granting_body_level (esquema Gemini)
# ---------------------------------------------------------------------------
_NIVEL1_MAP = {
    "AUTONOMICA": "comunidad_autonoma",
    "ESTADO":     "estado",
    "ESTATAL":    "estado",
}

# Palabras clave en nivel2 que refinan el mapeo de LOCAL u OTROS
_DIPUTACION_KEYWORDS = ["DIPUTACION", "DIPUTACIÓ"]
_UNIVERSIDAD_KEYWORDS = ["UNIVERSIDAD", "UNIVERSITAT", "UNIVERSIDADE"]
_EUROPEO_KEYWORDS = ["UNION EUROPEA", "COMISION EUROPEA", "EUROPEA"]


def derive_granting_body_level(doc: dict) -> str | None:
    nivel1 = (doc.get("nivel1") or "").strip().upper()
    nivel2 = (doc.get("nivel2") or "").strip().upper()

    if nivel1 in _NIVEL1_MAP:
        return _NIVEL1_MAP[nivel1]

    if nivel1 == "LOCAL":
        if any(kw in nivel2 for kw in _DIPUTACION_KEYWORDS):
            return "diputacion"
        return "municipio"

    if nivel1 == "OTROS":
        if any(kw in nivel2 for kw in _UNIVERSIDAD_KEYWORDS):
            # Universidades públicas valencianas → ámbito autonómico
            return "comunidad_autonoma"
        if any(kw in nivel2 for kw in _EUROPEO_KEYWORDS):
            return "union_europea"
        # Otros organismos no clasificados → autonómico por defecto para este dataset
        return "comunidad_autonoma"

    return None


# ---------------------------------------------------------------------------
# Keyword matching para aid_type
# Orden: de más específico a más genérico. El primero que coincida gana.
# ---------------------------------------------------------------------------
_AID_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("beca",             ["beca", "becas", "bolsa de práctica", "bolsa de investigación",
                          "bolsa investigacion", "bolsa prácticas", "prácticas externas",
                          "practicum", "iniciació a la investigació", "iniciacion investigacion",
                          "ayuda de matrícula", "ayuda matrícula", "ayudas de matrícula",
                          "ayudas matrícula", "financiación de la matrícula"]),
    ("ayuda_alquiler",   ["alquiler", "arrendamiento", "alquileres"]),
    ("ayuda_energia",    ["energía", "energética", "energético", "energetica", "energetico",
                          "calefacción", "calefaccion", "suministro eléctrico"]),
    ("ayuda_transporte", ["transporte", "desplazamiento", "movilidad"]),
    ("ayuda_alimentacion", ["alimentación", "alimentacion", "alimentos", "comedor"]),
    ("prestacion",       ["prestación", "prestacion", "prestaciones"]),
    ("bonificacion",     ["bonificación", "bonificacion", "bonificaciones"]),
    ("deduccion_fiscal", ["deducción fiscal", "deduccion fiscal", "irpf", "tributari"]),
    ("microcredito",     ["microcrédito", "microcredito", "micropréstamo", "microprestamo"]),
    ("subvencion",       []),   # fallback — siempre coincide al final
]


def derive_aid_type(doc: dict) -> str:
    descripcion = (doc.get("descripcion") or "").lower()

    # Concursos y certámenes son subvenciones en forma de premio
    # (no hay tipo específico en el esquema, usamos subvencion)
    for aid_type, keywords in _AID_TYPE_RULES:
        if not keywords:
            return aid_type   # fallback "subvencion"
        if any(kw in descripcion for kw in keywords):
            return aid_type

    return "subvencion"


# ---------------------------------------------------------------------------
# Derivación de status desde deadline
# ---------------------------------------------------------------------------
def derive_status(doc: dict) -> str | None:
    deadline = (doc.get("deadline") or "").strip()
    if not deadline or deadline.lower() in ("desconocido", ""):
        return None

    try:
        parsed = dateparser.parse(deadline)
        if parsed:
            return "abierta" if parsed.date() >= date.today() else "cerrada"
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------
def main(dry_run: bool = False) -> None:
    load_dotenv(ENV_PATH)
    uri = os.getenv("MONGO_URI")
    if not uri:
        logger.error("MONGO_URI no encontrada en .env")
        sys.exit(1)

    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    logger.info("Conectado a MongoDB Atlas.")

    col = client[DB_NAME][COLLECTION_NAME]

    # Seleccionar documentos donde falte al menos uno de los tres campos
    query = {
        "$or": [
            {"status": None}, {"status": {"$exists": False}},
            {"aid_type": None}, {"aid_type": {"$exists": False}},
            {"granting_body_level": None}, {"granting_body_level": {"$exists": False}},
        ]
    }
    docs = list(col.find(query, {
        "_id": 1, "descripcion": 1, "deadline": 1,
        "nivel1": 1, "nivel2": 1,
        "status": 1, "aid_type": 1, "granting_body_level": 1,
    }))

    logger.info(f"Documentos a retroalimentar: {len(docs)}")
    if not docs:
        logger.info("Nada que hacer — todos los documentos ya tienen los campos.")
        return

    # Contadores para el resumen final
    stats = {
        "status_derivado": 0, "status_desconocido": 0,
        "aid_type_beca": 0, "aid_type_subvencion": 0, "aid_type_otros": 0,
        "granting_derivado": 0, "granting_nulo": 0,
    }
    operations = []

    for doc in docs:
        doc_id = doc["_id"]
        updates = {}

        # --- status ---
        if not doc.get("status"):
            status = derive_status(doc)
            updates["status"] = status
            if status:
                stats["status_derivado"] += 1
            else:
                stats["status_desconocido"] += 1

        # --- aid_type ---
        if not doc.get("aid_type"):
            aid_type = derive_aid_type(doc)
            updates["aid_type"] = aid_type
            if aid_type == "beca":
                stats["aid_type_beca"] += 1
            elif aid_type == "subvencion":
                stats["aid_type_subvencion"] += 1
            else:
                stats["aid_type_otros"] += 1

        # --- granting_body_level ---
        if not doc.get("granting_body_level"):
            granting = derive_granting_body_level(doc)
            updates["granting_body_level"] = granting
            if granting:
                stats["granting_derivado"] += 1
            else:
                stats["granting_nulo"] += 1

        if dry_run:
            desc = (doc.get("descripcion") or "")[:60]
            logger.info(
                f"[DRY-RUN] {doc_id} | {desc}\n"
                f"          → status={updates.get('status')} | "
                f"aid_type={updates.get('aid_type')} | "
                f"granting={updates.get('granting_body_level')}"
            )
        else:
            if updates:
                operations.append(UpdateOne({"_id": doc_id}, {"$set": updates}))

    if dry_run:
        logger.info(f"\n[DRY-RUN] Se actualizarían {len(docs)} documentos. Nada escrito.")
    else:
        if operations:
            try:
                result = col.bulk_write(operations, ordered=False)
                logger.info(
                    f"Retroalimentación completada. "
                    f"Modificados: {result.modified_count} / {len(operations)}"
                )
            except BulkWriteError as e:
                logger.error(f"Errores durante la escritura: {e.details}")

    # Resumen
    logger.info("\n=== RESUMEN ===")
    logger.info(f"  status derivado:           {stats['status_derivado']}")
    logger.info(f"  status sin fecha parseable: {stats['status_desconocido']}")
    logger.info(f"  aid_type=beca:             {stats['aid_type_beca']}")
    logger.info(f"  aid_type=subvencion:       {stats['aid_type_subvencion']}")
    logger.info(f"  aid_type=otros tipos:      {stats['aid_type_otros']}")
    logger.info(f"  granting_body_level:       {stats['granting_derivado']}")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retroalimentar campos Gemini en MongoDB")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra qué se haría sin escribir en MongoDB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
