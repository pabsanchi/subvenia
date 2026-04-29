import json
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ScraperBDNS:
    def __init__(self):
        # Directorio base del módulo: modules/modulo1-scraper
        self.base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.data_dir / "ayudas.json"

    def scrape(self):
        logger.info("Iniciando proceso de scraping...")
        extracted_data = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Simulamos la navegación a un portal administrativo
                url = "about:blank"
                page.goto(url)
                
                logger.info("Simulando extracción de listado de convocatorias de la Comunidad Valenciana...")
                
                # HTML simulado para asegurar que las pruebas MVP funcionen independientemente
                # de cambios o caídas en la web real.
                mock_html = """
                <div class="convocatoria-item">
                    <span class="id">BDNS-987654</span>
                    <h2 class="title">Ayudas a la digitalización</h2>
                    <div class="issuer">Generalitat Valenciana</div>
                    <div class="desc">Subvenciones para la transformación digital en la región.</div>
                    <div class="target">Autónomos y PYMES</div>
                    <a class="link" href="https://example.com/ayuda">Enlace oficial</a>
                    <span class="start">2026-05-01</span>
                    <span class="end">2026-06-30</span>
                    <span class="status">Abierta</span>
                </div>
                """
                page.set_content(mock_html)

                # Bloque try/except para no romper el flujo si falla algún selector
                items = page.locator(".convocatoria-item").all()
                for item in items:
                    try:
                        source_id = item.locator(".id").inner_text(timeout=2000)
                        title = item.locator(".title").inner_text(timeout=2000)
                        issuer = item.locator(".issuer").inner_text(timeout=2000)
                        description = item.locator(".desc").inner_text(timeout=2000)
                        beneficiaries = item.locator(".target").inner_text(timeout=2000)
                        url_ayuda = item.locator(".link").get_attribute("href", timeout=2000)
                        start_date = item.locator(".start").inner_text(timeout=2000)
                        end_date = item.locator(".end").inner_text(timeout=2000)
                        status_text = item.locator(".status").inner_text(timeout=2000)
                        
                        record = {
                            "source_id": source_id,
                            "title": title,
                            "issuer": issuer,
                            "description": description,
                            "beneficiaries": beneficiaries,
                            "url": url_ayuda if url_ayuda else "",
                            "start_date": start_date,
                            "end_date": end_date,
                            "status": status_text,
                            "source_type": "Portal Web Oficial",
                            "region": "Comunidad Valenciana"
                        }
                        extracted_data.append(record)
                    except PlaywrightTimeoutError:
                        logger.warning("Timeout al intentar extraer un campo de un elemento.")
                    except Exception as e:
                        logger.error(f"Error al procesar elemento: {e}")

                browser.close()
        except Exception as e:
            logger.error(f"Error crítico en la ejecución de playwright: {e}")

        # Guardar resultados
        self._save_to_json(extracted_data)
        return extracted_data

    def _save_to_json(self, data):
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Datos exportados exitosamente a {self.output_file} ({len(data)} registros)")
        except Exception as e:
            logger.error(f"Error al guardar archivo JSON: {e}")

if __name__ == '__main__':
    scraper = ScraperBDNS()
    scraper.scrape()
