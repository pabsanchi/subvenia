"""
Tests de Integración para el Módulo 2: Elasticsearch.

Estos tests interactúan con el contenedor real de Elasticsearch.
Si el contenedor no está levantado, los tests se saltan (SKIP)
automáticamente para no romper la suite de CI/CD.
"""

import os
import time
import json
import uuid
import pytest
from elasticsearch import exceptions

from src.ingest import (
    get_es_client,
    create_index,
    process_and_ingest,
    EMBEDDING_DIMS,
)


@pytest.fixture(scope="module")
def real_es_client():
    """
    Intenta obtener un cliente real de ES. Si no hay conexión
    o las credenciales no están, salta los tests de este módulo.
    """
    try:
        es = get_es_client()
        es.info()  # Falla si no hay conexión
        return es
    except (exceptions.ConnectionError, ValueError) as e:
        pytest.skip(f"Elasticsearch no está disponible para tests de integración: {e}")


@pytest.fixture
def test_index(real_es_client):
    """
    Genera un nombre de índice único para cada test y lo borra al terminar,
    evitando ensuciar el entorno de desarrollo o producción.
    """
    index_name = f"test_ayudas_sociales_{uuid.uuid4().hex[:8]}"
    yield index_name
    
    # Teardown: borrar el índice después del test
    if real_es_client.indices.exists(index=index_name):
        real_es_client.indices.delete(index=index_name)


@pytest.fixture
def sample_json(tmp_path):
    """Crea un JSON temporal simulando la salida del Scraper."""
    data = [
        {
            "source_id": "BDNS-INT-1",
            "title": "Ayuda de Integración 1",
            "issuer": "Test Issuer",
            "description": "Prueba de búsqueda full-text en español.",
            "beneficiaries": "Programadores",
            "url": "http://test.com/1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "Abierta",
            "source_type": "Portal Web Oficial",
            "region": "Comunidad Valenciana"
        },
        {
            "source_id": "BDNS-INT-2",
            "title": "Ayuda de Integración 2",
            "issuer": "Test Issuer",
            "description": "Otra prueba.",
            "beneficiaries": "Empresas",
            "url": "http://test.com/2",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "Cerrada",
            "source_type": "Portal Web Oficial",
            "region": "Comunidad Valenciana"
        }
    ]
    file_path = tmp_path / "ayudas_int.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file_path


def test_real_create_index(real_es_client, test_index):
    """Verifica que el índice se crea en el contenedor real con el mapping correcto."""
    create_index(real_es_client, index_name=test_index)
    
    assert real_es_client.indices.exists(index=test_index)
    
    # Obtener el mapping real del servidor
    mapping = real_es_client.indices.get_mapping(index=test_index)
    properties = mapping[test_index]["mappings"]["properties"]
    
    # Validar que los campos de IA están correctamente configurados
    assert "embedding" in properties
    assert properties["embedding"]["type"] == "dense_vector"
    assert properties["embedding"]["dims"] == EMBEDDING_DIMS
    
    # Validar analizador de texto
    assert properties["description"]["type"] == "text"
    assert properties["description"]["analyzer"] == "spanish"


def test_real_ingest_and_search(real_es_client, test_index, sample_json):
    """Verifica que los datos se ingieren y pueden ser buscados."""
    # 1. Crear índice
    create_index(real_es_client, index_name=test_index)
    
    # 2. Ingestar datos
    success_count = process_and_ingest(real_es_client, sample_json, index_name=test_index)
    assert success_count == 2
    
    # Elasticsearch es near-real-time, hay que forzar un refresh para que
    # los documentos estén inmediatamente disponibles para búsqueda
    real_es_client.indices.refresh(index=test_index)
    
    # 3. Buscar (Test de Búsqueda Full-Text con el analyzer spanish)
    search_res = real_es_client.search(
        index=test_index,
        query={"match": {"description": "búsqueda"}}
    )
    
    hits = search_res["hits"]["hits"]
    assert len(hits) == 1
    assert hits[0]["_source"]["source_id"] == "BDNS-INT-1"
    
    # Validar que el embedding inyectado tiene los valores correctos (1e-7 mock)
    assert len(hits[0]["_source"]["embedding"]) == EMBEDDING_DIMS
    assert hits[0]["_source"]["embedding"][0] == 1e-7
