"""
Módulo 2: Script de Ingesta para MongoDB Atlas.

Este script conecta con una instancia de MongoDB Atlas y realiza la carga
de los datos extraídos por el Módulo 1 (Scraper).

Funcionalidades:
  - Lectura segura de credenciales desde archivo .env local.
  - Ingesta masiva usando insert_many.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuración de rutas y constantes
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
DATA_FILE = BASE_DIR.parent / "modulo1-scraper" / "data" / "convocatorias_full.json"
DB_NAME = "subvenia"
COLLECTION_NAME = "convocatorias"

def get_mongo_client() -> MongoClient:
    """Inicializa y retorna el cliente de MongoDB."""
    load_dotenv(ENV_PATH)
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI no encontrada en el .env")
    return MongoClient(mongo_uri)

def process_and_ingest(client: MongoClient, data_path: Path) -> int:
    """Lee las convocatorias y las inserta en MongoDB."""
    if not data_path.exists():
        logger.error(f"El archivo de datos no existe: {data_path}")
        return 0

    with open(data_path, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    if not data:
        logger.warning("El archivo JSON está vacío.")
        return 0

    # Usar 'id' como '_id' en Mongo para identificar unívocamente
    for doc in data:
        if "id" in doc:
            doc["_id"] = doc["id"]
        
        # Eliminar si existe para no estorbar, aunque _id ya lo gestiona
        if not doc.get("embedding"):
            logger.warning(f"Convocatoria {doc.get('_id')} sin vector. Podría fallar el RAG.")

    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    logger.info("Borrando documentos antiguos de la colección (reingesta limpia)...")
    collection.delete_many({})

    try:
        result = collection.insert_many(data, ordered=False)
        count = len(result.inserted_ids)
        logger.info(f"Se han indexado correctamente {count} documentos.")
        return count
    except BulkWriteError as bwe:
        logger.warning(f"Errores durante la indexación: {bwe.details}")
        return bwe.details['nInserted']

def main():
    """Punto de entrada: conecta e ingesta datos."""
    try:
        client = get_mongo_client()
        # Ping
        client.admin.command('ping')
        logger.info("Conectado a MongoDB Atlas exitosamente.")
        
        count = process_and_ingest(client, DATA_FILE)
        logger.info(f"Proceso de ingesta finalizado. Total indexados: {count}")
    except Exception as e:
        logger.error(f"Error durante la ingesta: {e}")

if __name__ == "__main__":
    main()
