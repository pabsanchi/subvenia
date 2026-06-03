"""
Tests unitarios para el Módulo 6: Recursos sociales del portal de Valencia.

Estrategia de testing:
  - Se mockea requests.get para simular respuestas del geoportal sin
    realizar peticiones HTTP reales.
  - Se valida el contrato de datos del DataFrame resultante y el manejo
    de errores de red.
"""

import sys
from pathlib import Path
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
from recursos_client import _fetch_dataset, load_all_resources, DATASETS, CATEGORY_COLORS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_geojson_response(features: list) -> MagicMock:
    """Simula una respuesta HTTP con un GeoJSON válido."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"type": "FeatureCollection", "features": features}
    return resp


def _make_feature(descripcion: str, titularidad: str | None,
                  lon: float = -0.37, lat: float = 39.47) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"descripcion": descripcion, "titularidad": titularidad},
    }


# ---------------------------------------------------------------------------
# Tests de _fetch_dataset
# ---------------------------------------------------------------------------

class TestFetchDataset:

    @patch("recursos_client.requests.get")
    def test_returns_correct_number_of_records(self, mock_get):
        features = [
            _make_feature("Centro A", "Ayuntamiento"),
            _make_feature("Centro B", "Cáritas"),
        ]
        mock_get.return_value = _make_geojson_response(features)

        records = _fetch_dataset("Mayores", "SS_MAYORES.json")
        assert len(records) == 2

    @patch("recursos_client.requests.get")
    def test_record_has_required_fields(self, mock_get):
        mock_get.return_value = _make_geojson_response(
            [_make_feature("Residencia Sol", "ONCE")]
        )
        records = _fetch_dataset("Mayores", "SS_MAYORES.json")
        record = records[0]

        assert record["categoria"] == "Mayores"
        assert "Residencia Sol" in record["descripcion"]
        assert record["titularidad"] == "ONCE"
        assert record["lat"] == pytest.approx(39.47)
        assert record["lon"] == pytest.approx(-0.37)
        assert "color" in record

    @patch("recursos_client.requests.get")
    def test_handles_null_titularidad(self, mock_get):
        """titularidad=null en el GeoJSON debe resultar en string vacío."""
        mock_get.return_value = _make_geojson_response(
            [_make_feature("Albergue Norte", None)]
        )
        records = _fetch_dataset("Personas sin Techo", "SS_SINTECHO.json")
        assert records[0]["titularidad"] == ""

    @patch("recursos_client.requests.get")
    def test_description_is_title_cased(self, mock_get):
        """Las descripciones deben normalizarse con title case."""
        mock_get.return_value = _make_geojson_response(
            [_make_feature("ASOCIACIÓN VALENCIANA DE AYUDA", "Test")]
        )
        records = _fetch_dataset("Mujeres", "SS_MUJERES.json")
        assert records[0]["descripcion"] == "Asociación Valenciana De Ayuda"

    @patch("recursos_client.requests.get")
    def test_network_error_propagates(self, mock_get):
        """Si requests.get falla, la excepción debe propagarse."""
        mock_get.side_effect = Exception("Timeout")
        with pytest.raises(Exception, match="Timeout"):
            _fetch_dataset("Mayores", "SS_MAYORES.json")

    @patch("recursos_client.requests.get")
    def test_color_assigned_from_category(self, mock_get):
        """El color del registro debe coincidir con CATEGORY_COLORS para esa categoría."""
        mock_get.return_value = _make_geojson_response(
            [_make_feature("Centro X", "Test")]
        )
        records = _fetch_dataset("Mujeres", "SS_MUJERES.json")
        assert records[0]["color"] == CATEGORY_COLORS["Mujeres"]


# ---------------------------------------------------------------------------
# Tests de load_all_resources
# ---------------------------------------------------------------------------

class TestLoadAllResources:

    @patch("recursos_client.requests.get")
    def test_returns_dataframe(self, mock_get):
        """Debe devolver un DataFrame, nunca None."""
        mock_get.return_value = _make_geojson_response(
            [_make_feature("Recurso A", "Test")]
        )
        df = load_all_resources()
        assert isinstance(df, pd.DataFrame)

    @patch("recursos_client.requests.get")
    def test_dataframe_has_required_columns(self, mock_get):
        """El DataFrame debe tener exactamente las columnas del contrato."""
        mock_get.return_value = _make_geojson_response(
            [_make_feature("Recurso A", "Test")]
        )
        df = load_all_resources()
        required = {"categoria", "descripcion", "titularidad", "lat", "lon", "color"}
        assert required.issubset(set(df.columns))

    @patch("recursos_client.requests.get")
    def test_failed_datasets_are_skipped(self, mock_get):
        """Si algunos datasets fallan, el resto se carga igualmente."""
        def side_effect(url, timeout):
            if "SS_MAYORES" in url:
                return _make_geojson_response([_make_feature("Recurso A", "X")])
            raise Exception("Not found")

        mock_get.side_effect = side_effect
        df = load_all_resources()

        assert not df.empty
        assert set(df["categoria"].unique()) == {"Mayores"}

    @patch("recursos_client.requests.get")
    def test_all_datasets_fail_returns_empty_dataframe(self, mock_get):
        """Si todos los datasets fallan, debe devolver un DataFrame vacío (no crashear)."""
        mock_get.side_effect = Exception("No network")
        df = load_all_resources()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    @patch("recursos_client.requests.get")
    def test_empty_descriptions_are_filtered(self, mock_get):
        """Registros con descripción vacía deben ser eliminados del resultado."""
        mock_get.return_value = _make_geojson_response([
            _make_feature("Recurso válido", "Test"),
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [-0.37, 39.47]},
             "properties": {"descripcion": "", "titularidad": "Test"}},
        ])
        df = load_all_resources()
        # Solo debe quedar el registro con descripción no vacía
        assert all(df["descripcion"].str.strip() != "")

    @patch("recursos_client.requests.get")
    def test_categoria_comes_from_dataset_key(self, mock_get):
        """La columna 'categoria' debe coincidir con la clave del DATASETS dict."""
        def side_effect(url, timeout):
            if "SS_MAYORES" in url:
                return _make_geojson_response([_make_feature("Centro A", "X")])
            raise Exception("skip")
        mock_get.side_effect = side_effect

        df = load_all_resources()
        assert (df["categoria"] == "Mayores").all()
