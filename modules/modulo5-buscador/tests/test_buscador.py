"""
Tests unitarios para el Módulo 5: Buscador filtrado.

Estrategia de testing:
  - Las funciones puras (get_status, get_matching_tags) se testean directamente.
  - buscar_convocatorias se testea con un cliente MongoDB mockeado para
    verificar que la query se construye correctamente sin conexión real.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from buscador_client import (
    get_status,
    get_matching_tags,
    buscar_convocatorias,
    SITUACION_LABORAL,
    COLECTIVOS,
)


# ---------------------------------------------------------------------------
# Tests de get_status
# ---------------------------------------------------------------------------

class TestGetStatus:

    def test_uses_native_status_field_when_present(self):
        """Si el documento tiene campo `status`, debe usarlo directamente."""
        assert get_status({"status": "abierta"}) == ("abierta", "Abierta")
        assert get_status({"status": "cerrada"}) == ("cerrada", "Cerrada")
        assert get_status({"status": "proximamente"}) == ("proximamente", "Próximamente")
        assert get_status({"status": "permanente"}) == ("permanente", "Permanente")

    def test_derives_open_from_future_iso_date(self):
        """deadline ISO en el futuro → abierta."""
        key, _ = get_status({"deadline": "2099-01-01"})
        assert key == "abierta"

    def test_derives_closed_from_past_iso_date(self):
        """deadline ISO en el pasado → cerrada."""
        key, _ = get_status({"deadline": "2000-01-01"})
        assert key == "cerrada"

    def test_derives_open_from_spanish_text_date(self):
        """deadline en texto español con fecha futura → abierta."""
        key, _ = get_status({"deadline": "15 de enero de 2099"})
        assert key == "abierta"

    def test_derives_closed_from_spanish_text_date(self):
        """deadline en texto español con fecha pasada → cerrada."""
        key, _ = get_status({"deadline": "1 de enero de 2000"})
        assert key == "cerrada"

    def test_unknown_for_relative_deadline(self):
        """deadline con texto relativo no parseable → desconocida."""
        key, _ = get_status({"deadline": "15 días hábiles desde la publicación"})
        assert key == "desconocida"

    def test_unknown_for_desconocido_string(self):
        """deadline='desconocido' → desconocida."""
        key, _ = get_status({"deadline": "desconocido"})
        assert key == "desconocida"

    def test_unknown_for_missing_deadline(self):
        """Documento sin deadline ni status → desconocida."""
        key, _ = get_status({})
        assert key == "desconocida"

    def test_native_status_overrides_deadline(self):
        """El campo `status` tiene prioridad sobre `deadline`."""
        doc = {"status": "permanente", "deadline": "2000-01-01"}
        key, _ = get_status(doc)
        assert key == "permanente"


# ---------------------------------------------------------------------------
# Tests de get_matching_tags
# ---------------------------------------------------------------------------

class TestGetMatchingTags:

    def _doc_with(self, group: str, field: str, value: bool = True) -> dict:
        return {"beneficiaries": {group: {field: value}}}

    def test_returns_label_for_true_field(self):
        """Campos con True deben devolver la etiqueta legible correspondiente."""
        doc = self._doc_with("situacion_laboral", "desempleado")
        selected = {"situacion_laboral": ["desempleado"]}
        tags = get_matching_tags(doc, selected)
        assert "Desempleado/a" in tags

    def test_returns_empty_for_false_field(self):
        """Campos con False no deben generar etiqueta."""
        doc = self._doc_with("situacion_laboral", "desempleado", False)
        selected = {"situacion_laboral": ["desempleado"]}
        tags = get_matching_tags(doc, selected)
        assert tags == []

    def test_returns_empty_when_no_filters_selected(self):
        """Sin filtros seleccionados, no hay etiquetas de coincidencia."""
        doc = self._doc_with("colectivos_generales", "jovenes")
        tags = get_matching_tags(doc, {})
        assert tags == []

    def test_multiple_matches_across_groups(self):
        """Debe retornar etiquetas de múltiples grupos a la vez."""
        doc = {
            "beneficiaries": {
                "situacion_laboral": {"desempleado": True},
                "colectivos_generales": {"jovenes": True},
            }
        }
        selected = {
            "situacion_laboral": ["desempleado"],
            "colectivos_generales": ["jovenes"],
        }
        tags = get_matching_tags(doc, selected)
        assert len(tags) == 2
        assert "Desempleado/a" in tags
        assert "Jóvenes" in tags

    def test_only_selected_fields_are_checked(self):
        """Solo se comprueban los campos que el usuario seleccionó, aunque otros sean True."""
        doc = {
            "beneficiaries": {
                "situacion_laboral": {"desempleado": True, "empleado": True},
            }
        }
        selected = {"situacion_laboral": ["desempleado"]}
        tags = get_matching_tags(doc, selected)
        assert len(tags) == 1
        assert "Desempleado/a" in tags


# ---------------------------------------------------------------------------
# Tests de buscar_convocatorias (MongoDB mockeado)
# ---------------------------------------------------------------------------

class TestBuscarConvocatorias:

    def _make_mock_client(self, docs: list) -> MagicMock:
        """Devuelve un MongoClient mock cuyo find() devuelve `docs`."""
        client = MagicMock()
        collection = client.__getitem__.return_value.__getitem__.return_value
        cursor = MagicMock()
        cursor.__iter__ = MagicMock(return_value=iter(docs))
        collection.find.return_value.limit.return_value = cursor
        return client

    @patch("buscador_client._get_client")
    def test_empty_filters_exclude_closed_by_default(self, mock_get_client):
        """Sin filtros de perfil, la query solo debe excluir cerradas."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias()

        col = mock_client["subvenia"]["convocatorias"]
        query_used = col.find.call_args[0][0]
        assert query_used == {"status": {"$ne": "cerrada"}}

    @patch("buscador_client._get_client")
    def test_exclude_closed_false_produces_empty_query(self, mock_get_client):
        """Con exclude_closed=False y sin filtros, la query debe ser {}."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias(exclude_closed=False)

        col = mock_client["subvenia"]["convocatorias"]
        query_used = col.find.call_args[0][0]
        assert query_used == {}

    @patch("buscador_client._get_client")
    def test_exclude_closed_combines_with_profile_filters(self, mock_get_client):
        """exclude_closed debe coexistir con los filtros $or de perfil."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias(situacion_laboral=["desempleado"])

        col = mock_client["subvenia"]["convocatorias"]
        query_used = col.find.call_args[0][0]
        assert "$or" in query_used
        assert query_used.get("status") == {"$ne": "cerrada"}

    @patch("buscador_client._get_client")
    def test_profile_filters_generate_or_query(self, mock_get_client):
        """Filtros de perfil deben generar una query con $or."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias(situacion_laboral=["desempleado", "jubilado_o_pensionista"])

        col = mock_client["subvenia"]["convocatorias"]
        query_used = col.find.call_args[0][0]
        assert "$or" in query_used
        or_fields = [list(c.keys())[0] for c in query_used["$or"]]
        assert "beneficiaries.situacion_laboral.desempleado" in or_fields
        assert "beneficiaries.situacion_laboral.jubilado_o_pensionista" in or_fields

    @patch("buscador_client._get_client")
    def test_texto_adds_regex_filter(self, mock_get_client):
        """El filtro de texto debe añadir un $regex sobre 'descripcion'."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias(texto="alquiler")

        col = mock_client["subvenia"]["convocatorias"]
        query_used = col.find.call_args[0][0]
        assert "descripcion" in query_used
        assert "$regex" in query_used["descripcion"]

    @patch("buscador_client._get_client")
    def test_aid_type_filter_uses_in(self, mock_get_client):
        """El filtro de tipo de ayuda debe usar $in."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias(aid_types=["beca"])

        col = mock_client["subvenia"]["convocatorias"]
        query_used = col.find.call_args[0][0]
        assert "aid_type" in query_used
        assert query_used["aid_type"] == {"$in": ["beca"]}

    @patch("buscador_client._get_client")
    def test_returns_empty_list_on_mongo_error(self, mock_get_client):
        """Si MongoDB lanza una excepción, debe devolver [] sin propagar el error."""
        client = MagicMock()
        col = client.__getitem__.return_value.__getitem__.return_value
        col.find.side_effect = Exception("Connection refused")
        mock_get_client.return_value = client

        result = buscar_convocatorias()
        assert result == []

    @patch("buscador_client._get_client")
    def test_max_results_is_applied(self, mock_get_client):
        """El límite de resultados debe pasarse a .limit()."""
        mock_client = self._make_mock_client([])
        mock_get_client.return_value = mock_client

        buscar_convocatorias(max_results=10)

        col = mock_client["subvenia"]["convocatorias"]
        col.find.return_value.limit.assert_called_once_with(10)
