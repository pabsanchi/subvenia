"""
Tests unitarios para el Módulo 2: Ingesta en Elasticsearch.

Estrategia de testing:
  - Se usa unittest.mock para simular el cliente de Elasticsearch,
    de modo que los tests se ejecutan sin necesidad de tener levantado
    el contenedor Docker.
  - Se valida:
    1. Que el cliente se inicializa con las credenciales correctas del .env.
    2. Que el mapping del índice se crea correctamente, incluyendo el
       campo dense_vector de 768 dimensiones para el futuro RAG.
    3. Que no se intenta recrear un índice existente.
    4. Que el proceso de ingesta inyecta el embedding mock (768 ceros)
       y usa la API bulk correctamente.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingest import (
    get_es_client,
    create_index,
    process_and_ingest,
    INDEX_NAME,
    EMBEDDING_DIMS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_env_vars():
    """Simula las variables de entorno necesarias para la conexión."""
    with patch.dict(os.environ, {"ELASTIC_PASSWORD": "dummy_password"}):
        yield


@pytest.fixture
def mock_es_client():
    """Retorna un cliente de Elasticsearch simulado (MagicMock)."""
    return MagicMock()


@pytest.fixture
def sample_json(tmp_path):
    """Crea un JSON temporal simulando la salida del Módulo 1."""
    data = [
        {
            "source_id": "BDNS-TEST",
            "title": "Ayuda de prueba",
            "issuer": "Test Issuer",
            "description": "Desc test",
            "beneficiaries": "Benef test",
            "url": "http://test.com",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "Abierta",
            "source_type": "Portal Web Oficial",
            "region": "Comunidad Valenciana"
        }
    ]
    file_path = tmp_path / "ayudas.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file_path


# ---------------------------------------------------------------------------
# Tests de conexión
# ---------------------------------------------------------------------------

def test_get_es_client(mock_env_vars):
    """Prueba que el cliente se inicializa apuntando a localhost:9200."""
    es = get_es_client()
    assert es is not None
    nodes = es.transport.node_pool.all()
    assert len(nodes) == 1
    assert nodes[0].host == "localhost"
    assert nodes[0].port == 9200


def test_get_es_client_missing_password():
    """Prueba que lanza error si falta la contraseña en el .env."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("src.ingest.load_dotenv"):  # Evitar que lea el .env real
            with pytest.raises(ValueError, match="ELASTIC_PASSWORD"):
                get_es_client()


# ---------------------------------------------------------------------------
# Tests de creación de índice
# ---------------------------------------------------------------------------

def test_create_index_not_exists(mock_es_client):
    """Prueba la creación del índice con el mapping completo."""
    mock_es_client.indices.exists.return_value = False

    create_index(mock_es_client)

    mock_es_client.indices.exists.assert_called_once_with(index=INDEX_NAME)
    mock_es_client.indices.create.assert_called_once()

    # Verificar que el mapping incluye el campo embedding
    call_args = mock_es_client.indices.create.call_args[1]
    mapping = call_args["body"]["mappings"]["properties"]
    assert "embedding" in mapping
    assert mapping["embedding"]["type"] == "dense_vector"
    assert mapping["embedding"]["dims"] == EMBEDDING_DIMS
    assert mapping["embedding"]["similarity"] == "cosine"

    # Verificar campos keyword
    for field in ["source_id", "issuer", "status", "url", "source_type", "region"]:
        assert mapping[field]["type"] == "keyword", f"{field} debería ser keyword"

    # Verificar campos text con analyzer spanish
    for field in ["title", "description", "beneficiaries"]:
        assert mapping[field]["type"] == "text", f"{field} debería ser text"
        assert mapping[field]["analyzer"] == "spanish", f"{field} debería usar analyzer spanish"

    # Verificar campos date
    for field in ["start_date", "end_date"]:
        assert mapping[field]["type"] == "date", f"{field} debería ser date"


def test_create_index_already_exists(mock_es_client):
    """Prueba que no se intenta recrear un índice existente."""
    mock_es_client.indices.exists.return_value = True
    create_index(mock_es_client)
    mock_es_client.indices.create.assert_not_called()


# ---------------------------------------------------------------------------
# Tests de ingesta
# ---------------------------------------------------------------------------

@patch("src.ingest.helpers.bulk")
def test_process_and_ingest(mock_bulk, mock_es_client, sample_json):
    """Prueba la inyección del embedding mock y la carga en bulk."""
    mock_bulk.return_value = (1, [])

    success_count = process_and_ingest(mock_es_client, sample_json)

    assert success_count == 1
    mock_bulk.assert_called_once()

    # Extraer las acciones pasadas a bulk
    actions_arg = mock_bulk.call_args[0][1]
    actions_list = list(actions_arg)

    assert len(actions_list) == 1
    doc = actions_list[0]

    # Comprobar metadatos de indexación
    assert doc["_index"] == INDEX_NAME
    assert doc["_id"] == "BDNS-TEST"

    # Comprobar inyección del embedding mock (valores mínimos no-cero)
    assert "embedding" in doc["_source"]
    assert len(doc["_source"]["embedding"]) == EMBEDDING_DIMS
    assert all(v == 1e-7 for v in doc["_source"]["embedding"])


@patch("src.ingest.helpers.bulk")
def test_process_and_ingest_empty_file(mock_bulk, mock_es_client, tmp_path):
    """Prueba que un JSON vacío no intenta hacer bulk."""
    empty_file = tmp_path / "empty.json"
    with open(empty_file, "w") as f:
        json.dump([], f)

    result = process_and_ingest(mock_es_client, empty_file)

    assert result == 0
    mock_bulk.assert_not_called()


def test_process_and_ingest_missing_file(mock_es_client, tmp_path):
    """Prueba que un archivo inexistente devuelve 0 sin crashear."""
    missing = tmp_path / "no_existe.json"
    result = process_and_ingest(mock_es_client, missing)
    assert result == 0
