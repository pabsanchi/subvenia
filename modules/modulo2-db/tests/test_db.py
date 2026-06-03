"""
Tests unitarios para el Módulo 2: Ingesta en MongoDB Atlas.

Estrategia de testing:
  - Se usa unittest.mock para simular el cliente de MongoDB,
    de modo que los tests se ejecutan sin necesidad de conexión real.
  - Se valida:
    1. Que get_mongo_client lanza ValueError si falta MONGO_URI.
    2. Que process_and_ingest genera las operaciones de upsert correctamente.
    3. Que documentos con campo 'id' reciben '_id' y se ignoran sin 'id'.
    4. Que un JSON vacío o inexistente devuelve 0 sin crashear.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingest import get_mongo_client, process_and_ingest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_json(tmp_path):
    """JSON temporal simulando la salida del Módulo 1 con embeddings."""
    data = [
        {
            "id": 123456,
            "descripcion": "BECAS PARA JÓVENES INVESTIGADORES 2026",
            "numeroConvocatoria": "906001",
            "deadline": "2026-12-31",
            "status": "abierta",
            "aid_type": "beca",
            "beneficiaries": {
                "situacion_laboral": {"desempleado": False},
                "colectivos_generales": {"jovenes": True, "estudiantes_o_investigadores": True},
            },
            "geographic_scope": {"level": "autonomico", "region_name": "Comunitat Valenciana"},
            "embedding": [0.1] * 768,
        },
        {
            "id": 789012,
            "descripcion": "SUBVENCIONES COMERCIO LOCAL 2026",
            "numeroConvocatoria": "906002",
            "deadline": "2026-06-30",
            "status": "cerrada",
            "aid_type": "subvencion",
            "beneficiaries": {},
            "geographic_scope": {"level": "municipal", "region_name": "Valencia"},
            "embedding": [0.2] * 768,
        },
    ]
    p = tmp_path / "convocatorias_full.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def mock_mongo_client():
    """Cliente de MongoDB simulado que acepta bulk_write."""
    client = MagicMock()
    collection = client.__getitem__.return_value.__getitem__.return_value
    bulk_result = MagicMock()
    bulk_result.upserted_count = 2
    bulk_result.modified_count = 0
    collection.bulk_write.return_value = bulk_result
    return client


# ---------------------------------------------------------------------------
# Tests de conexión
# ---------------------------------------------------------------------------

class TestGetMongoClient:

    def test_raises_if_mongo_uri_missing(self):
        """Debe lanzar ValueError si MONGO_URI no está configurada."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.ingest.load_dotenv"):
                with pytest.raises(ValueError, match="MONGO_URI"):
                    get_mongo_client()


# ---------------------------------------------------------------------------
# Tests de ingesta
# ---------------------------------------------------------------------------

class TestProcessAndIngest:

    def test_ingest_returns_correct_count(self, mock_mongo_client, sample_json):
        """Debe devolver el número de documentos insertados/actualizados."""
        count = process_and_ingest(mock_mongo_client, sample_json)
        assert count == 2

    def test_ingest_calls_bulk_write(self, mock_mongo_client, sample_json):
        """Debe llamar a bulk_write con las operaciones correctas."""
        process_and_ingest(mock_mongo_client, sample_json)
        collection = mock_mongo_client["subvenia"]["convocatorias"]
        collection.bulk_write.assert_called_once()

    def test_ingest_sets_id_from_id_field(self, mock_mongo_client, sample_json):
        """Cada documento con campo 'id' debe usar ese valor como '_id'."""
        process_and_ingest(mock_mongo_client, sample_json)
        collection = mock_mongo_client["subvenia"]["convocatorias"]
        ops = collection.bulk_write.call_args[0][0]

        ids_used = [op._filter["_id"] for op in ops]
        assert 123456 in ids_used
        assert 789012 in ids_used

    def test_ingest_skips_docs_without_id(self, mock_mongo_client, tmp_path):
        """Documentos sin campo 'id' deben ser ignorados."""
        data = [{"descripcion": "Sin ID", "embedding": [0.0] * 768}]
        p = tmp_path / "sin_id.json"
        p.write_text(json.dumps(data), encoding="utf-8")

        count = process_and_ingest(mock_mongo_client, p)
        collection = mock_mongo_client["subvenia"]["convocatorias"]
        collection.bulk_write.assert_not_called()
        assert count == 0

    def test_ingest_empty_file_returns_zero(self, mock_mongo_client, tmp_path):
        """Un JSON vacío debe devolver 0 sin llamar a bulk_write."""
        p = tmp_path / "vacio.json"
        p.write_text("[]", encoding="utf-8")

        count = process_and_ingest(mock_mongo_client, p)
        assert count == 0
        mock_mongo_client["subvenia"]["convocatorias"].bulk_write.assert_not_called()

    def test_ingest_missing_file_returns_zero(self, mock_mongo_client, tmp_path):
        """Un archivo inexistente debe devolver 0 sin crashear."""
        missing = tmp_path / "no_existe.json"
        count = process_and_ingest(mock_mongo_client, missing)
        assert count == 0

    def test_ingest_warns_missing_embedding(self, mock_mongo_client, tmp_path, caplog):
        """Debe emitir warning si un documento no tiene embedding."""
        data = [{"id": 1, "descripcion": "Sin vector", "embedding": None}]
        p = tmp_path / "sin_vector.json"
        p.write_text(json.dumps(data), encoding="utf-8")

        import logging
        with caplog.at_level(logging.WARNING):
            process_and_ingest(mock_mongo_client, p)

        assert any("sin vector" in m.lower() or "embedding" in m.lower()
                   for m in caplog.messages)
