"""
Módulo 1: Scraper BDNS para SubvenIA.

Este módulo implementa un scraper modular dirigido a la BDNS
(Base de Datos Nacional de Subvenciones), enfocándose en la
extracción de ayudas para la Comunidad Valenciana.

Arquitectura:
  - ScraperBDNS: Orquestador principal. Coordina la navegación
    y la extracción de datos, volcando los resultados en un JSON local.
  - HTMLParser: Componente de parseo puro. Recibe HTML crudo y
    devuelve registros estructurados según el contrato de datos.
    Permite testear la lógica de extracción sin necesidad de un
    navegador real.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contrato de datos: claves requeridas en cada registro
# ---------------------------------------------------------------------------
REQUIRED_KEYS = {
    "source_id", "title", "issuer", "description",
    "beneficiaries", "url", "start_date", "end_date",
    "status", "source_type", "region",
}

# ---------------------------------------------------------------------------
# Constantes fijas del contrato
# ---------------------------------------------------------------------------
SOURCE_TYPE = "Portal Web Oficial"
REGION = "Comunidad Valenciana"

# ---------------------------------------------------------------------------
# URL base de la BDNS (filtrada por Comunidad Valenciana)
# ---------------------------------------------------------------------------
BDNS_BASE_URL = (
    "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatorias"
    "?ccaa=C10"  # Código de Comunitat Valenciana en BDNS
)

# ---------------------------------------------------------------------------
# HTML de ejemplo para simulación MVP
# ---------------------------------------------------------------------------
MOCK_HTML = """\
<html><body>
<div class="convocatoria-item">
    <span class="id">BDNS-712345</span>
    <h2 class="title">Subvenciones para la modernización del comercio local</h2>
    <div class="issuer">Generalitat Valenciana - Conselleria de Economía</div>
    <div class="desc">Ayudas destinadas a impulsar la transformación digital y modernización de los establecimientos comerciales en municipios de la Comunidad Valenciana.</div>
    <div class="target">Comercios minoristas y autónomos del sector comercial con establecimiento físico en la Comunitat Valenciana.</div>
    <a class="link" href="https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/712345">Ver convocatoria</a>
    <span class="start">2026-04-15</span>
    <span class="end">2026-07-15</span>
    <span class="status">Abierta</span>
</div>
<div class="convocatoria-item">
    <span class="id">BDNS-698210</span>
    <h2 class="title">Programa de ayudas a la eficiencia energética en PYMES</h2>
    <div class="issuer">Generalitat Valenciana - Conselleria de Transición Ecológica</div>
    <div class="desc">Programa de subvenciones para financiar actuaciones de mejora de la eficiencia energética y la incorporación de energías renovables en pequeñas y medianas empresas valencianas.</div>
    <div class="target">PYMES con domicilio social o centro de trabajo en la Comunitat Valenciana.</div>
    <a class="link" href="https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/698210">Ver convocatoria</a>
    <span class="start">2026-03-01</span>
    <span class="end">2026-05-31</span>
    <span class="status">Abierta</span>
</div>
<div class="convocatoria-item">
    <span class="id">BDNS-654321</span>
    <h2 class="title">Becas para la formación de jóvenes investigadores</h2>
    <div class="issuer">Generalitat Valenciana - Conselleria de Innovación</div>
    <div class="desc">Convocatoria de becas para la formación de personal investigador en universidades públicas y centros de investigación de la Comunitat Valenciana.</div>
    <div class="target">Personas físicas menores de 30 años con título universitario oficial, residentes en la Comunitat Valenciana.</div>
    <a class="link" href="https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/654321">Ver convocatoria</a>
    <span class="start">2026-01-10</span>
    <span class="end">2026-03-10</span>
    <span class="status">Cerrada</span>
</div>
</body></html>
"""


class HTMLParser:
    """
    Componente de parseo puro: recibe HTML y extrae registros estructurados.

    Funciona con Playwright Page objects (pasándoles set_content) o con
    cualquier HTML crudo que respete la estructura de selectores esperada.
    No lanza excepciones no controladas: cada campo se extrae dentro de
    un bloque try/except para evitar romper el flujo ante selectores
    ausentes o inesperados.
    """

    # Mapa de selectores CSS → clave del contrato de datos
    SELECTOR_MAP = {
        "source_id": ".id",
        "title": ".title",
        "issuer": ".issuer",
        "description": ".desc",
        "beneficiaries": ".target",
        "start_date": ".start",
        "end_date": ".end",
        "status": ".status",
    }
    URL_SELECTOR = ".link"
    ITEM_SELECTOR = ".convocatoria-item"

    def parse_page(self, page) -> List[Dict[str, str]]:
        """
        Extrae todas las convocatorias de un Playwright Page object.

        Args:
            page: Instancia de Playwright Page con el contenido cargado.

        Returns:
            Lista de diccionarios conformes al contrato de datos.
        """
        records: List[Dict[str, str]] = []

        try:
            items = page.locator(self.ITEM_SELECTOR).all()
        except Exception as e:
            logger.error(f"Error al localizar elementos convocatoria: {e}")
            return records

        for idx, item in enumerate(items):
            record = self._extract_record(item, idx)
            if record:
                records.append(record)

        logger.info(f"Parseados {len(records)} registros de la página.")
        return records

    def _extract_record(self, item, idx: int) -> Optional[Dict[str, str]]:
        """
        Extrae un único registro de un elemento locator.

        Cada campo se extrae individualmente dentro de try/except para
        no romper el flujo si falla un selector CSS/XPath.
        """
        fields: Dict[str, str] = {}

        for key, selector in self.SELECTOR_MAP.items():
            try:
                fields[key] = item.locator(selector).inner_text(timeout=3000).strip()
            except Exception as e:
                logger.warning(f"[Registro {idx}] No se pudo extraer '{key}' ({selector}): {e}")
                fields[key] = ""

        # Extraer URL (atributo href, no inner_text)
        try:
            href = item.locator(self.URL_SELECTOR).get_attribute("href", timeout=3000)
            fields["url"] = href.strip() if href else ""
        except Exception as e:
            logger.warning(f"[Registro {idx}] No se pudo extraer URL: {e}")
            fields["url"] = ""

        # Campos fijos del contrato
        fields["source_type"] = SOURCE_TYPE
        fields["region"] = REGION

        # Validar que el registro tiene al menos source_id y title
        if not fields.get("source_id") and not fields.get("title"):
            logger.warning(f"[Registro {idx}] Descartado: sin source_id ni title.")
            return None

        return fields


class ScraperBDNS:
    """
    Orquestador principal del scraping.

    Coordina la navegación con Playwright y delega el parseo al
    componente HTMLParser. Los datos se persisten en un archivo
    JSON local (MVP: sin base de datos real).
    """

    def __init__(self, use_mock: bool = True):
        # Directorio base del módulo: modules/modulo1-scraper
        self.base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.data_dir / "ayudas.json"
        self.parser = HTMLParser()
        self.use_mock = use_mock

    def scrape(self) -> List[Dict[str, str]]:
        """
        Ejecuta el proceso completo de scraping.

        En modo mock (por defecto en MVP) inyecta HTML simulado en
        el navegador. En modo real, navegaría a la URL de la BDNS.

        Returns:
            Lista de registros extraídos (conformes al contrato de datos).
        """
        logger.info("Iniciando proceso de scraping BDNS...")
        extracted_data: List[Dict[str, str]] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                if self.use_mock:
                    logger.info("Modo MVP: cargando HTML simulado.")
                    page.set_content(MOCK_HTML)
                else:
                    logger.info(f"Navegando a BDNS: {BDNS_BASE_URL}")
                    try:
                        page.goto(BDNS_BASE_URL, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except PlaywrightTimeoutError:
                        logger.warning("Timeout al cargar la página BDNS. Intentando con contenido parcial.")
                    except Exception as e:
                        logger.error(f"Error de navegación: {e}")

                # Delegar parseo al componente especializado
                extracted_data = self.parser.parse_page(page)

                browser.close()
        except Exception as e:
            logger.error(f"Error crítico en la ejecución de Playwright: {e}")

        # Guardar resultados
        self._save_to_json(extracted_data)
        return extracted_data

    def _save_to_json(self, data: List[Dict[str, str]]) -> None:
        """Persiste la lista de registros en el archivo JSON de salida."""
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Datos exportados exitosamente a {self.output_file} ({len(data)} registros)")
        except Exception as e:
            logger.error(f"Error al guardar archivo JSON: {e}")


# ---------------------------------------------------------------------------
# Ejecución directa
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scraper = ScraperBDNS(use_mock=True)
    results = scraper.scrape()
    print(f"\n✅ Extracción completada: {len(results)} registros guardados.")
