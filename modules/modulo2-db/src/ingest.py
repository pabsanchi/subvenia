"""
Módulo 2: Script de Ingesta para Elasticsearch.

Este script conecta con una instancia local de Elasticsearch (levantada
mediante docker-compose) y realiza la carga inicial de los datos extraídos
por el Módulo 1 (Scraper) en el índice 'ayudas_sociales'.

Funcionalidades:
  - Lectura segura de credenciales desde archivo .env local.
  - Creación del índice con un mapping estricto que incluye:
    * Campos keyword para metadatos fijos (source_id, issuer, status, etc.).
    * Campos text con analyzer 'spanish' para búsquedas full-text.
    * Campos date para las fechas de solicitud.
    * Campo dense_vector (768 dims, cosine) para futuras búsquedas
      semánticas kNN (RAG). En esta fase MVP se rellena con ceros.
  - Ingesta masiva usando la API bulk de Elasticsearch.

Uso:
    cd modules/modulo2-db
    PYTHONPATH=. python src/ingest.py
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración de rutas y constantes
# ---------------------------------------------------------------------------

# Directorio base del módulo: modules/modulo2-db
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
DATA_FILE = BASE_DIR.parent / "modulo1-scraper" / "data" / "convocatorias_full.json"

# Nombre del índice en Elasticsearch
INDEX_NAME = "ayudas_sociales_full"

# Dimensiones del vector de embedding (preparado para modelos tipo
# sentence-transformers/all-MiniLM-L6-v2 o similares de 768 dims)
EMBEDDING_DIMS = 768


def get_es_client() -> Elasticsearch:
    """
    Inicializa y retorna el cliente de Elasticsearch.

    Lee la contraseña del archivo .env del módulo y establece
    conexión con la instancia local en http://localhost:9200
    usando autenticación básica (usuario 'elastic').

    Returns:
        Instancia configurada de Elasticsearch.

    Raises:
        ValueError: Si ELASTIC_PASSWORD no está definida en el .env.
    """
    load_dotenv(ENV_PATH)
    elastic_password = os.getenv("ELASTIC_PASSWORD")

    if not elastic_password:
        raise ValueError("ELASTIC_PASSWORD no encontrada en el .env")

    es = Elasticsearch(
        "http://localhost:9200",
        basic_auth=("elastic", elastic_password)
    )
    return es


def create_index(es: Elasticsearch, index_name: str = INDEX_NAME) -> None:
    """
    Crea el índice con el mapping definido para el esquema enriquecido.

    El mapping se adapta exactamente a las convocatorias completas:
      - keyword: numeroConvocatoria, nivel1, nivel2, nivel3, codigoInvente, deadline, geographic_scope.*
      - text (spanish): descripcion, descripcionLeng, beneficiaries.other_conditions
      - date: fechaRecepcion
      - boolean: mrr, beneficiaries.requires_residency, beneficiaries.compatible_with_other_aids
      - integer: id, beneficiaries.age_min, beneficiaries.age_max
      - keyword list: beneficiaries.employment_status, beneficiaries.family_status, beneficiaries.target_groups, beneficiaries.vulnerability_status
      - dense_vector (768 dims, cosine): embedding

    Si el índice ya existe, no hace nada para evitar perder datos.

    Args:
        es: Cliente de Elasticsearch conectado.
        index_name: Nombre del índice a crear.
    """
    mapping = {
        "mappings": {
            "properties": {
                # Identificadores y metadatos básicos
                "id": {"type": "integer"},
                "mrr": {"type": "boolean"},
                "numeroConvocatoria": {"type": "keyword"},
                
                # Campos descriptivos con analizador en español
                "descripcion": {"type": "text", "analyzer": "spanish"},
                "descripcionLeng": {"type": "text", "analyzer": "spanish"},
                
                # Fechas
                "fechaRecepcion": {"type": "date"},
                
                # Organismos emisores
                "nivel1": {"type": "keyword"},
                "nivel2": {"type": "keyword"},
                "nivel3": {"type": "keyword"},
                "codigoInvente": {"type": "keyword"},
                
                # Plazos
                "deadline": {"type": "keyword"},
                
                # Ámbito geográfico estructurado
                "geographic_scope": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "keyword"},
                        "region_name": {"type": "keyword"}
                    }
                },
                
                # Beneficiarios y requisitos estructurados
                "beneficiaries": {
                    "type": "object",
                    "properties": {
                        "requires_residency": {"type": "boolean"},
                        "residency_scope": {"type": "keyword"},
                        "age_min": {"type": "integer"},
                        "age_max": {"type": "integer"},
                        "income_threshold": {"type": "keyword"},
                        "compatible_with_other_aids": {"type": "boolean"},
                        "employment_status": {"type": "keyword"},
                        "family_status": {"type": "keyword"},
                        "target_groups": {"type": "keyword"},
                        "vulnerability_status": {"type": "keyword"},
                        "other_conditions": {"type": "text", "analyzer": "spanish"}
                    }
                },

                # Vector de embedding para búsqueda semántica kNN (RAG)
                "embedding": {
                    "type": "dense_vector",
                    "dims": EMBEDDING_DIMS,
                    "similarity": "cosine",
                    "index": True
                }
            }
        }
    }

    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=mapping)
        logger.info(f"Índice '{index_name}' creado con éxito.")
    else:
        logger.info(f"El índice '{index_name}' ya existe. No se modifica.")


def process_and_ingest(es: Elasticsearch, data_path: Path, index_name: str = INDEX_NAME) -> int:
    """
    Lee las convocatorias enriquecidas del Módulo 1 (que ya incluyen embeddings)
    y realiza la ingesta masiva bulk en Elasticsearch.

    Args:
        es: Cliente de Elasticsearch conectado.
        data_path: Ruta al archivo convocatorias_full.json.
        index_name: Nombre del índice donde se insertarán los datos.

    Returns:
        Número de documentos indexados exitosamente.
    """
    if not data_path.exists():
        logger.error(f"El archivo de datos no existe: {data_path}")
        return 0

    with open(data_path, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    if not data:
        logger.warning("El archivo JSON está vacío. No hay datos que indexar.")
        return 0

    actions = []
    for doc in data:
        doc_id = str(doc.get("id"))
        if not doc_id:
            logger.warning("Documento sin 'id' encontrado. Se omite.")
            continue

        embedding = doc.get("embedding")
        if not embedding:
            logger.warning(f"La convocatoria {doc_id} no contiene el campo 'embedding'. Se omite.")
            continue

        action = {
            "_index": index_name,
            "_id": doc_id,
            "_source": doc
        }
        actions.append(action)

    if not actions:
        logger.warning("No hay acciones válidas para indexar.")
        return 0

    success, errors = helpers.bulk(es, actions)
    logger.info(f"Se han indexado correctamente {success} documentos.")
    if errors:
        logger.warning(f"Errores durante la indexación: {errors}")
    return success


def main():
    """Punto de entrada: conecta, crea índice e ingesta datos."""
    try:
        es = get_es_client()

        # Verificar conexión
        info = es.info()
        logger.info(f"Conectado a Elasticsearch versión {info['version']['number']}")

        create_index(es)
        count = process_and_ingest(es, DATA_FILE)
        logger.info(f"Proceso de ingesta finalizado. Total indexados: {count}")
    except Exception as e:
        logger.error(f"Error durante la ingesta: {e}")


if __name__ == "__main__":
    main()
