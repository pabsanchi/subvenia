# -*- coding: utf-8 -*-
"""
Tests unitarios para la integración real del Módulo 1 (Scraper Real & Gemini).

Valida:
  - Inicialización y actualización de fechas de seguimiento.
  - Ingesta incremental de convocatorias raw libre de duplicados.
  - Lógica de combinación de metadatos y extracción de Gemini.
  - Robustez del control de errores de la API (429, 503) y parada controlada.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Importamos las funciones a testear
from src.fetch_raw import (
    inicializar_seguimiento as f_init_seg,
    obtener_fecha_guardada as f_get_fecha,
    actualizar_fecha_actualizacion as f_set_fecha,
    actualizar_json_convocatorias as f_update_raw,
    flujo_obtencion_convocatorias_raw,
)

from src.analyze_gemini import (
    inicializar_seguimiento as a_init_seg,
    obtener_raws_rellenadas as a_get_rellenadas,
    incrementar_raws_rellenadas as a_inc_rellenadas,
    actualizar_convocatorias_full as a_update_full,
    obtener_convocatoria_raw_por_numero_convocatoria as a_get_by_num,
    completar_convocatoria,
    flujo_completado_masivo_convocatorias,
)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Genera rutas de archivos temporales para evitar alterar los reales."""
    paths = {
        "raw_file": tmp_path / "lista_convocatorias_raw.json",
        "tracking_file": tmp_path / "seguimiento_procesos.json",
        "full_file": tmp_path / "convocatorias_full.json",
        "pdf_dir": tmp_path / "PDFdescargados",
    }
    paths["pdf_dir"].mkdir(parents=True, exist_ok=True)
    return paths


# ===========================================================================
# TESTS DE RECUPERACIÓN RAW (fetch_raw.py)
# ===========================================================================

def test_fetch_raw_seguimiento(tmp_data_dir):
    track_f = tmp_data_dir["tracking_file"]
    
    # 1. Inicializar por primera vez
    f_init_seg(track_f)
    assert track_f.exists()
    
    with open(track_f, "r", encoding="utf-8") as f:
        datos = json.load(f)
    assert datos["raws_rellenadas"] == 0
    
    # 2. Guardar y leer fecha
    assert f_get_fecha(track_f) is None
    f_set_fecha(track_f)
    
    fecha_guardada = f_get_fecha(track_f)
    assert isinstance(fecha_guardada, tuple)
    assert len(fecha_guardada) == 3


def test_fetch_raw_evita_duplicados(tmp_data_dir):
    raw_f = tmp_data_dir["raw_file"]
    
    convs_initial = [
        {"id": 111, "numeroConvocatoria": "111", "descripcion": "Ayuda 1"},
        {"id": 222, "numeroConvocatoria": "222", "descripcion": "Ayuda 2"},
    ]
    
    # Ingesta inicial
    f_update_raw(convs_initial, raw_f)
    
    with open(raw_f, "r", encoding="utf-8") as f:
        datos = json.load(f)
    assert len(datos) == 2
    
    # Ingesta posterior con un duplicado y una nueva
    convs_new = [
        {"id": 222, "numeroConvocatoria": "222", "descripcion": "Ayuda 2 Duplicada"},
        {"id": 333, "numeroConvocatoria": "333", "descripcion": "Ayuda 3"},
    ]
    f_update_raw(convs_new, raw_f)
    
    with open(raw_f, "r", encoding="utf-8") as f:
        datos_finales = json.load(f)
    assert len(datos_finales) == 3
    assert {c["id"] for c in datos_finales} == {111, 222, 333}


# ===========================================================================
# TESTS DE ENRIQUECIMIENTO (analyze_gemini.py)
# ===========================================================================

def test_analyze_gemini_seguimiento(tmp_data_dir):
    track_f = tmp_data_dir["tracking_file"]
    
    a_init_seg(track_f)
    assert a_get_rellenadas(track_f) == 0
    
    a_inc_rellenadas(track_f)
    assert a_get_rellenadas(track_f) == 1


def test_actualizar_convocatorias_full(tmp_data_dir):
    full_f = tmp_data_dir["full_file"]
    
    entrada = {
        "id": 123,
        "numeroConvocatoria": "123456",
        "beneficiaries": {"target_groups": ["jovenes"]},
        "deadline": "2026-12-31",
        "geographic_scope": {"level": "autonomico", "region_name": "Comunidad Valenciana"}
    }
    
    a_update_full(entrada, full_f)
    
    with open(full_f, "r", encoding="utf-8") as f:
        datos = json.load(f)
    assert len(datos) == 1
    assert datos[0]["numeroConvocatoria"] == "123456"
    assert datos[0]["beneficiaries"]["target_groups"] == ["jovenes"]


@patch("src.analyze_gemini.genai.GenerativeModel")
@patch("src.analyze_gemini.genai.upload_file")
@patch("src.analyze_gemini.genai.get_file")
@patch("src.analyze_gemini.genai.delete_file")
@patch("src.analyze_gemini.client")
def test_completar_convocatoria_exito(mock_client, mock_delete, mock_get, mock_upload, mock_model_class, tmp_data_dir):
    # Mockear BDNSClient
    mock_client.fetch_convocatorias.return_value = [{"documentos": [{"id": 999}]}]
    mock_client.fetch_convocatorias_documentos.return_value = b"bytes-pdf-ficticio"
    
    # Mockear subida a Gemini
    mock_file = MagicMock()
    mock_file.state.name = "SUCCESS"
    mock_file.name = "files/mock-id"
    mock_upload.return_value = mock_file
    mock_get.return_value = mock_file
    
    # Mockear GenerativeModel
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "beneficiaries": {
            "target_groups": ["autonomos"],
            "employment_status": ["autonomo_activo"],
            "family_status": [],
            "vulnerability_status": [],
            "age_min": None,
            "age_max": None,
            "income_threshold": None,
            "requires_residency": True,
            "residency_scope": "municipal",
            "compatible_with_other_aids": None,
            "other_conditions": None
        },
        "aid_type": "subvencion",
        "granting_body_level": "municipio",
        "status": "abierta",
        "frequency": "pago_unico",
        "deadline": "2026-06-30",
        "geographic_scope": {"level": "municipal", "region_name": "Valencia"}
    })
    mock_model_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model_instance
    
    # Configurar archivos raw temporales
    raw_f = tmp_data_dir["raw_file"]
    with open(raw_f, "w", encoding="utf-8") as f:
        json.dump([{"id": 777, "numeroConvocatoria": "887288", "descripcion": "Ayuda Digital"}], f)
        
    # Ejecutar parcheando constantes globales en src.analyze_gemini
    with patch("src.analyze_gemini.RAW_FILE", raw_f), \
         patch("src.analyze_gemini.TRACKING_FILE", tmp_data_dir["tracking_file"]), \
         patch("src.analyze_gemini.FULL_FILE", tmp_data_dir["full_file"]), \
         patch("src.analyze_gemini.PDF_DIR", tmp_data_dir["pdf_dir"]):
             
        resultado = completar_convocatoria("887288")
        
        assert resultado[0] == 0
        assert resultado[1]["aid_type"] == "subvencion"
        assert tmp_data_dir["full_file"].exists()
        
        # Verificar que el PDF temporal local fue eliminado
        pdf_path = tmp_data_dir["pdf_dir"] / "convocatoria999.pdf"
        assert not pdf_path.exists()
        
        # Verificar que se liberó el archivo en el servidor de Gemini
        mock_delete.assert_called_once_with("files/mock-id")


@patch("src.analyze_gemini.genai.GenerativeModel")
@patch("src.analyze_gemini.genai.upload_file")
@patch("src.analyze_gemini.genai.get_file")
@patch("src.analyze_gemini.genai.delete_file")
@patch("src.analyze_gemini.client")
def test_completar_convocatoria_cuota_agotada(mock_client, mock_delete, mock_get, mock_upload, mock_model_class, tmp_data_dir):
    # Mockear BDNSClient
    mock_client.fetch_convocatorias.return_value = [{"documentos": [{"id": 999}]}]
    mock_client.fetch_convocatorias_documentos.return_value = b"bytes-pdf-ficticio"
    
    # Mockear subida a Gemini
    mock_file = MagicMock()
    mock_file.state.name = "SUCCESS"
    mock_file.name = "files/mock-id"
    mock_upload.return_value = mock_file
    mock_get.return_value = mock_file
    
    # Simular error 429 de cuota agotada
    from google.api_core.exceptions import ResourceExhausted
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.side_effect = ResourceExhausted("Simulated 429 quota exceeded")
    mock_model_class.return_value = mock_model_instance
    
    # Configurar archivos raw temporales
    raw_f = tmp_data_dir["raw_file"]
    with open(raw_f, "w", encoding="utf-8") as f:
        json.dump([{"id": 777, "numeroConvocatoria": "887288", "descripcion": "Ayuda Digital"}], f)
        
    with patch("src.analyze_gemini.RAW_FILE", raw_f), \
         patch("src.analyze_gemini.TRACKING_FILE", tmp_data_dir["tracking_file"]), \
         patch("src.analyze_gemini.FULL_FILE", tmp_data_dir["full_file"]), \
         patch("src.analyze_gemini.PDF_DIR", tmp_data_dir["pdf_dir"]):
             
        resultado = completar_convocatoria("887288")
        
        # El código devuelto debe ser 2 (cuota agotada) y no lanzar excepción
        assert resultado[0] == 2
        assert "Quota exhausted" in resultado[1] or "quota" in resultado[1].lower()
        
        # El PDF temporal local debe seguir limpio
        pdf_path = tmp_data_dir["pdf_dir"] / "convocatoria999.pdf"
        assert not pdf_path.exists()
        
        # Debe haber llamado a la limpieza en el servidor
        mock_delete.assert_called_once_with("files/mock-id")
