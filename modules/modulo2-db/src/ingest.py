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
DATA_FILE = BASE_DIR.parent / "modulo1-scraper" / "data" / "ayudas.json"

# Nombre del índice en Elasticsearch
INDEX_NAME = "ayudas_sociales"

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
    Crea el índice con el mapping definido.

    El mapping se ajusta al contrato de datos del Módulo 1:
      - keyword: source_id, issuer, status, url, source_type, region
      - text (spanish): title, description, beneficiaries
      - date: start_date, end_date
      - dense_vector (768 dims, cosine): embedding

    Si el índice ya existe, no hace nada para evitar perder datos.

    Args:
        es: Cliente de Elasticsearch conectado.
        index_name: Nombre del índice a crear.
    """
    mapping = {
        "mappings": {
            "properties": {
                # Campos de metadatos fijos — tipo keyword para filtros exactos
                "source_id": {"type": "keyword"},
                "issuer": {"type": "keyword"},
                "status": {"type": "keyword"},
                "url": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "region": {"type": "keyword"},

                # Campos descriptivos — tipo text con analyzer español
                "title": {"type": "text", "analyzer": "spanish"},
                "description": {"type": "text", "analyzer": "spanish"},
                "beneficiaries": {"type": "text", "analyzer": "spanish"},

                # Fechas de la convocatoria
                "start_date": {"type": "date"},
                "end_date": {"type": "date"},

                # Vector de embedding para búsqueda semántica kNN (RAG)
                # En esta fase MVP se rellena con ceros (mock)
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
    Lee el JSON del Módulo 1, inyecta embeddings mock y hace bulk insert.

    Para cada documento del archivo ayudas.json:
      1. Añade un campo 'embedding' con un array de EMBEDDING_DIMS ceros
         flotantes (mock para esta fase MVP).
      2. Usa el source_id como _id del documento en Elasticsearch.
      3. Envía todo en una única operación bulk para máximo rendimiento.

    Args:
        es: Cliente de Elasticsearch conectado.
        data_path: Ruta al archivo ayudas.json generado por el Módulo 1.
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

    # Mock embedding: vector con valores mínimos no-cero.
    # La similitud coseno de Elasticsearch rechaza vectores de magnitud cero,
    # por lo que usamos un valor ínfimo (1e-7) que no afectará a los
    # resultados de búsqueda cuando se reemplacen por embeddings reales.
    mock_embedding = [1e-7] * EMBEDDING_DIMS

    actions = []
    for doc in data:
        doc["embedding"] = mock_embedding

        action = {
            "_index": index_name,
            "_id": doc.get("source_id"),
            "_source": doc
        }
        actions.append(action)

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
