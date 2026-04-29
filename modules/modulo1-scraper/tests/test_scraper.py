import json
import pytest
from pathlib import Path
from src.scraper import ScraperBDNS

@pytest.fixture
def scraper():
    return ScraperBDNS()

def test_scraper_generates_valid_json(scraper):
    # Ejecutar scraping
    data = scraper.scrape()
    
    # 1. Comprobar que hay datos
    assert len(data) > 0, "El scraper no devolvió datos"
    
    # 2. Comprobar existencia del fichero
    assert scraper.output_file.exists(), "No se generó el archivo JSON"
    
    # 3. Leer los datos y verificar que se guardaron correctamente
    with open(scraper.output_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    assert len(saved_data) == len(data), "Los datos guardados difieren de los devueltos"

    # 4. Validar el contrato de datos estrictamente
    expected_keys = {
        "source_id", "title", "issuer", "description", 
        "beneficiaries", "url", "start_date", "end_date", 
        "status", "source_type", "region"
    }

    for item in saved_data:
        item_keys = set(item.keys())
        
        # Todas las claves esperadas deben estar presentes
        missing_keys = expected_keys - item_keys
        assert not missing_keys, f"Faltan claves requeridas: {missing_keys}"
        
        # No debe haber claves extras
        extra_keys = item_keys - expected_keys
        assert not extra_keys, f"Hay claves extra no permitidas: {extra_keys}"

        # Comprobación de campos fijos
        assert item["source_type"] == "Portal Web Oficial"
        assert item["region"] == "Comunidad Valenciana"

def test_scraper_exception_handling():
    # Solo para asegurar que se puede instanciar y ejecutar sin crashear el proceso
    scraper = ScraperBDNS()
    try:
        data = scraper.scrape()
        assert isinstance(data, list)
    except Exception as e:
        pytest.fail(f"El scraper lanzó una excepción no controlada: {e}")
