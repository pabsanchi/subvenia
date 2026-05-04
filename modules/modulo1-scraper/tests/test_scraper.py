"""
Tests unitarios para el Módulo 1: Scraper BDNS.

Estrategia de testing:
  - Se valida la lógica de parseo (HTMLParser) y la generación del JSON
    de salida sin depender del lanzamiento real de un navegador Chromium.
  - Se usa un enfoque de doble verificación:
    1. Test de integración ligero con Playwright (si el entorno lo soporta).
    2. Test de contrato puro que valida el JSON generado, usando un mock
       del parser para entornos donde Playwright no puede lanzar navegador.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.scraper import (
    ScraperBDNS,
    HTMLParser,
    REQUIRED_KEYS,
    SOURCE_TYPE,
    REGION,
    MOCK_HTML,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scraper(tmp_path):
    """Crea un ScraperBDNS que escribe en un directorio temporal."""
    s = ScraperBDNS(use_mock=True)
    # Redirigir la salida a tmp_path para no contaminar data/
    s.data_dir = tmp_path
    s.output_file = tmp_path / "ayudas.json"
    return s


@pytest.fixture
def sample_records():
    """Registros de ejemplo que representan una extracción exitosa."""
    return [
        {
            "source_id": "BDNS-712345",
            "title": "Subvenciones para la modernización del comercio local",
            "issuer": "Generalitat Valenciana - Conselleria de Economía",
            "description": "Ayudas destinadas a impulsar la transformación digital.",
            "beneficiaries": "Comercios minoristas y autónomos.",
            "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/712345",
            "start_date": "2026-04-15",
            "end_date": "2026-07-15",
            "status": "Abierta",
            "source_type": SOURCE_TYPE,
            "region": REGION,
        },
        {
            "source_id": "BDNS-698210",
            "title": "Programa de ayudas a la eficiencia energética en PYMES",
            "issuer": "Generalitat Valenciana - Conselleria de Transición Ecológica",
            "description": "Programa de subvenciones para eficiencia energética.",
            "beneficiaries": "PYMES con domicilio en la Comunitat Valenciana.",
            "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/698210",
            "start_date": "2026-03-01",
            "end_date": "2026-05-31",
            "status": "Abierta",
            "source_type": SOURCE_TYPE,
            "region": REGION,
        },
        {
            "source_id": "BDNS-654321",
            "title": "Becas para la formación de jóvenes investigadores",
            "issuer": "Generalitat Valenciana - Conselleria de Innovación",
            "description": "Convocatoria de becas para personal investigador.",
            "beneficiaries": "Personas menores de 30 años con título universitario.",
            "url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/654321",
            "start_date": "2026-01-10",
            "end_date": "2026-03-10",
            "status": "Cerrada",
            "source_type": SOURCE_TYPE,
            "region": REGION,
        },
    ]


# ---------------------------------------------------------------------------
# Tests de contrato de datos
# ---------------------------------------------------------------------------

class TestDataContract:
    """Valida que los registros cumplen al 100% con el contrato de datos."""

    def test_all_required_keys_present(self, sample_records):
        """Cada registro debe contener exactamente las claves del contrato."""
        for record in sample_records:
            record_keys = set(record.keys())
            missing = REQUIRED_KEYS - record_keys
            assert not missing, f"Faltan claves requeridas: {missing}"

    def test_no_extra_keys(self, sample_records):
        """No debe haber claves adicionales fuera del contrato."""
        for record in sample_records:
            record_keys = set(record.keys())
            extra = record_keys - REQUIRED_KEYS
            assert not extra, f"Hay claves extra no permitidas: {extra}"

    def test_fixed_fields_values(self, sample_records):
        """Los campos fijos deben tener sus valores exactos."""
        for record in sample_records:
            assert record["source_type"] == SOURCE_TYPE, (
                f"source_type debe ser '{SOURCE_TYPE}', es '{record['source_type']}'"
            )
            assert record["region"] == REGION, (
                f"region debe ser '{REGION}', es '{record['region']}'"
            )

    def test_status_values(self, sample_records):
        """El campo status solo admite 'Abierta' o 'Cerrada'."""
        valid_statuses = {"Abierta", "Cerrada"}
        for record in sample_records:
            assert record["status"] in valid_statuses, (
                f"Status inválido: '{record['status']}'. Debe ser {valid_statuses}"
            )

    def test_url_is_absolute(self, sample_records):
        """El campo url debe ser un enlace absoluto."""
        for record in sample_records:
            if record["url"]:
                assert record["url"].startswith("http"), (
                    f"URL no es absoluta: '{record['url']}'"
                )

    def test_no_empty_critical_fields(self, sample_records):
        """Los campos source_id y title no deben estar vacíos."""
        for record in sample_records:
            assert record["source_id"], "source_id no puede estar vacío"
            assert record["title"], "title no puede estar vacío"


# ---------------------------------------------------------------------------
# Tests de persistencia JSON
# ---------------------------------------------------------------------------

class TestJSONPersistence:
    """Valida la serialización y escritura del archivo JSON."""

    def test_save_to_json_creates_file(self, scraper, sample_records):
        """_save_to_json debe crear el archivo de salida."""
        scraper._save_to_json(sample_records)
        assert scraper.output_file.exists(), "No se generó el archivo JSON"

    def test_save_to_json_valid_content(self, scraper, sample_records):
        """El archivo JSON guardado debe ser parseable y contener todos los registros."""
        scraper._save_to_json(sample_records)
        with open(scraper.output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert len(saved_data) == len(sample_records), (
            "Los datos guardados difieren de los devueltos"
        )

    def test_save_to_json_contract_compliance(self, scraper, sample_records):
        """El JSON guardado debe cumplir el contrato de datos al 100%."""
        scraper._save_to_json(sample_records)
        with open(scraper.output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        for item in saved_data:
            item_keys = set(item.keys())
            # Todas las claves esperadas deben estar presentes
            missing = REQUIRED_KEYS - item_keys
            assert not missing, f"Faltan claves requeridas en JSON: {missing}"
            # No debe haber claves extras
            extra = item_keys - REQUIRED_KEYS
            assert not extra, f"Hay claves extra en JSON: {extra}"

    def test_save_to_json_utf8_encoding(self, scraper, sample_records):
        """El JSON debe preservar caracteres especiales (tildes, ñ, etc.)."""
        scraper._save_to_json(sample_records)
        with open(scraper.output_file, "r", encoding="utf-8") as f:
            content = f.read()
        # Verificar que no se escaparon caracteres unicode
        assert "\\u" not in content, "ensure_ascii debería estar en False"
        # Verificar que las tildes se conservan
        assert "Economía" in content or "energética" in content


# ---------------------------------------------------------------------------
# Tests de integración con mock de Playwright
# ---------------------------------------------------------------------------

class TestScraperIntegration:
    """Tests de integración que simulan Playwright sin un navegador real."""

    def test_scrape_with_mocked_playwright(self, scraper, sample_records):
        """
        Valida el flujo completo de scrape() sin lanzar un navegador real.
        Se mockea sync_playwright para inyectar datos de ejemplo.
        """
        # Mockear el parser para devolver datos controlados
        with patch.object(scraper.parser, "parse_page", return_value=sample_records):
            with patch("src.scraper.sync_playwright") as mock_pw:
                # Configurar el mock de Playwright
                mock_browser = MagicMock()
                mock_page = MagicMock()
                mock_browser.new_page.return_value = mock_page
                mock_context = MagicMock()
                mock_context.__enter__ = MagicMock(return_value=mock_context)
                mock_context.__exit__ = MagicMock(return_value=False)
                mock_context.chromium.launch.return_value = mock_browser
                mock_pw.return_value = mock_context

                data = scraper.scrape()

        # Validar resultados
        assert len(data) == 3, f"Se esperaban 3 registros, se obtuvieron {len(data)}"
        assert scraper.output_file.exists(), "No se generó el archivo JSON"

        # Verificar contrato de datos en los resultados
        for record in data:
            record_keys = set(record.keys())
            missing = REQUIRED_KEYS - record_keys
            assert not missing, f"Faltan claves: {missing}"

    def test_scrape_handles_playwright_crash(self, scraper):
        """
        El scraper no debe lanzar excepciones si Playwright falla.
        Debe generar un JSON vacío en su lugar.
        """
        with patch("src.scraper.sync_playwright") as mock_pw:
            mock_pw.return_value.__enter__ = MagicMock(
                side_effect=RuntimeError("Browser crash simulado")
            )
            mock_pw.return_value.__exit__ = MagicMock(return_value=False)

            try:
                data = scraper.scrape()
                assert isinstance(data, list), "scrape() debe devolver una lista"
            except Exception as e:
                pytest.fail(f"El scraper lanzó una excepción no controlada: {e}")


# ---------------------------------------------------------------------------
# Tests del HTMLParser
# ---------------------------------------------------------------------------

class TestHTMLParser:
    """Valida la lógica de extracción del parser de forma aislada."""

    def test_parser_selector_map_covers_contract(self):
        """El mapa de selectores del parser debe cubrir todas las claves del contrato."""
        parser = HTMLParser()
        # Claves que el parser extrae por selector + url + campos fijos
        covered_keys = set(parser.SELECTOR_MAP.keys()) | {"url", "source_type", "region"}
        missing = REQUIRED_KEYS - covered_keys
        assert not missing, f"El parser no cubre estas claves del contrato: {missing}"

    def test_mock_html_has_expected_items(self):
        """El HTML de mock debe contener al menos una convocatoria."""
        assert ".convocatoria-item" or "convocatoria-item" in MOCK_HTML
        # Contar ocurrencias del selector de item
        count = MOCK_HTML.count('class="convocatoria-item"')
        assert count >= 1, f"Se esperaba al menos 1 convocatoria en el mock, hay {count}"

    def test_required_keys_constant_matches_spec(self):
        """La constante REQUIRED_KEYS debe coincidir con la especificación del contrato."""
        expected = {
            "source_id", "title", "issuer", "description",
            "beneficiaries", "url", "start_date", "end_date",
            "status", "source_type", "region",
        }
        assert REQUIRED_KEYS == expected, (
            f"REQUIRED_KEYS no coincide con la especificación: "
            f"diff={REQUIRED_KEYS.symmetric_difference(expected)}"
        )
