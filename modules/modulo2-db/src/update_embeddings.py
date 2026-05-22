"""
Script para actualizar el campo 'embedding' de los documentos existentes en Elasticsearch.

Uso:
    cd modules/modulo2-db
    PYTHONPATH=. python src/update_embeddings.py --file ../modulo1-scraper/data/ayudas_con_vector.json
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
ENV_PATH = BASE_DIR.parent.parent / ".env"
INDEX_NAME = "ayudas_sociales"


def get_es_client() -> Elasticsearch:
    """Inicializa y retorna el cliente de Elasticsearch."""
    load_dotenv(ENV_PATH)
    elastic_password = os.getenv("ELASTIC_PASSWORD")

    if not elastic_password:
        raise ValueError("ELASTIC_PASSWORD no encontrada en el .env")

    es = Elasticsearch(
        "http://localhost:9200",
        basic_auth=("elastic", elastic_password)
    )
    return es


def update_embeddings(es: Elasticsearch, data_path: Path, index_name: str = INDEX_NAME) -> int:
    """
    Lee un JSON y actualiza exclusivamente el campo 'embedding' 
    de los documentos correspondientes en Elasticsearch mediante la API bulk de update.
    """
    if not data_path.exists():
        logger.error(f"El archivo JSON no existe: {data_path}")
        return 0

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Si el JSON es un solo diccionario (un solo registro), lo convertimos a lista
    if isinstance(data, dict):
        data = [data]

    if not data:
        logger.warning("El archivo JSON está vacío.")
        return 0

    actions = []
    for doc in data:
        # Detectar de manera flexible el ID del documento
        doc_id = doc.get("source_id") or doc.get("id")
        
        # Detectar de manera flexible el campo del vector
        vector = doc.get("embedding") or doc.get("float_vector")
        
        if not doc_id:
            logger.warning("Documento sin 'source_id' o 'id' encontrado. Se omite.")
            continue
            
        if not vector:
            logger.warning(f"Documento con ID {doc_id} no tiene campo de vector ('embedding' o 'float_vector'). Se omite.")
            continue

        # Usamos la operación "update" para actualizar solo el campo deseado sin sobreescribir el resto
        action = {
            "_op_type": "update",
            "_index": index_name,
            "_id": doc_id,
            "doc": {
                "embedding": vector
            }
        }
        actions.append(action)

    if not actions:
        logger.warning("No hay acciones válidas para actualizar.")
        return 0

    success, errors = helpers.bulk(es, actions)
    logger.info(f"Se han actualizado correctamente {success} documentos.")
    if errors:
        logger.warning(f"Errores durante la actualización: {errors}")
    return success


def main():
    parser = argparse.ArgumentParser(description="Actualizar campo de embeddings en Elasticsearch")
    parser.add_argument("--file", type=str, required=True, help="Ruta al archivo JSON con los vectores")
    args = parser.parse_args()

    data_file = Path(args.file)
    
    try:
        es = get_es_client()
        
        # Verificar conexión
        info = es.info()
        logger.info(f"Conectado a Elasticsearch versión {info['version']['number']}")
        
        count = update_embeddings(es, data_file)
        logger.info(f"Proceso de actualización finalizado. Total actualizados: {count}")
    except Exception as e:
        logger.error(f"Error durante la actualización: {e}")


if __name__ == "__main__":
    main()
