"""
Tests de integración para el Módulo 2: Ingesta en MongoDB Atlas.

Estos tests requieren una conexión real a MongoDB Atlas (MONGO_URI en .env).
Si no hay conexión disponible, los tests se saltan automáticamente (SKIP)
para no romper la suite de CI/CD en entornos sin credenciales.
"""

import json
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from src.ingest import get_mongo_client, process_and_ingest

# Nombre de colección temporal para los tests — no contamina datos reales
TEST_COLLECTION = "test_integration_tmp"


@pytest.fixture(scope="module")
def real_mongo_client():
    """
    Intenta conectar a MongoDB Atlas. Si no hay conexión o falta MONGO_URI,
    salta los tests de este módulo.
    """
    load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
    uri = os.getenv("MONGO_URI")
    if not uri:
        pytest.skip("MONGO_URI no configurada — tests de integración omitidos.")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client
    except (ConnectionFailure, Exception) as e:
        pytest.skip(f"MongoDB no disponible: {e}")


@pytest.fixture(autouse=True)
def cleanup(real_mongo_client):
    """Elimina la colección de test antes y después de cada test."""
    real_mongo_client["subvenia"][TEST_COLLECTION].drop()
    yield
    real_mongo_client["subvenia"][TEST_COLLECTION].drop()


@pytest.fixture
def sample_json(tmp_path):
    """JSON temporal con dos convocatorias de prueba."""
    data = [
        {
            "id": 99000001,
            "descripcion": "TEST — Becas investigación",
            "numeroConvocatoria": "T001",
            "deadline": "2026-12-31",
            "status": "abierta",
            "aid_type": "beca",
            "embedding": [0.1] * 768,
        },
        {
            "id": 99000002,
            "descripcion": "TEST — Subvención comercio",
            "numeroConvocatoria": "T002",
            "deadline": "2025-01-01",
            "status": "cerrada",
            "aid_type": "subvencion",
            "embedding": [0.2] * 768,
        },
    ]
    p = tmp_path / "test_data.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _ingest_to_test_collection(client, data_path):
    """Wrapper que dirige la ingesta a la colección temporal de test."""
    from pymongo import UpdateOne
    from pymongo.errors import BulkWriteError
    import logging

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = client["subvenia"]
    col = db[TEST_COLLECTION]
    operations = []
    for doc in data:
        if not doc.get("id"):
            continue
        doc["_id"] = doc["id"]
        doc_without_id = {k: v for k, v in doc.items() if k != "_id"}
        operations.append(UpdateOne(
            {"_id": doc["_id"]},
            {"$set": doc_without_id, "$setOnInsert": {"rag_retrieval_count": 0}},
            upsert=True,
        ))
    if not operations:
        return 0
    result = col.bulk_write(operations, ordered=False)
    return result.upserted_count + result.modified_count


def test_real_ingest_inserts_documents(real_mongo_client, sample_json):
    """Verifica que los documentos se insertan correctamente en MongoDB."""
    count = _ingest_to_test_collection(real_mongo_client, sample_json)
    assert count == 2

    col = real_mongo_client["subvenia"][TEST_COLLECTION]
    assert col.count_documents({}) == 2


def test_real_ingest_upsert_is_idempotent(real_mongo_client, sample_json):
    """Ingestar dos veces no debe duplicar documentos."""
    _ingest_to_test_collection(real_mongo_client, sample_json)
    _ingest_to_test_collection(real_mongo_client, sample_json)

    col = real_mongo_client["subvenia"][TEST_COLLECTION]
    assert col.count_documents({}) == 2


def test_real_ingest_id_field_is_set(real_mongo_client, sample_json):
    """El campo '_id' debe coincidir con el campo 'id' del documento."""
    _ingest_to_test_collection(real_mongo_client, sample_json)

    col = real_mongo_client["subvenia"][TEST_COLLECTION]
    doc = col.find_one({"_id": 99000001})
    assert doc is not None
    assert doc["descripcion"] == "TEST — Becas investigación"


def test_real_ingest_initializes_rag_counter(real_mongo_client, sample_json):
    """Los documentos nuevos deben tener rag_retrieval_count = 0."""
    _ingest_to_test_collection(real_mongo_client, sample_json)

    col = real_mongo_client["subvenia"][TEST_COLLECTION]
    for doc in col.find({}):
        assert doc.get("rag_retrieval_count") == 0
