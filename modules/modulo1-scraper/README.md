# Módulo 1: Scraper

Este módulo conforma la primera etapa del proyecto SubvenIA, encargándose de la extracción y estructuración de los datos provenientes de portales web (ej. Base de Datos Nacional de Subvenciones). 
En su versión actual, opera bajo un enfoque MVP (Minimum Viable Product), extrayendo ayudas orientadas a la **Comunidad Valenciana** y persistiendo la información localmente en un formato JSON estricto.

## Arquitectura

El scraper sigue un diseño modular con separación de responsabilidades:

- **`HTMLParser`**: Componente de parseo puro. Recibe una página de Playwright y extrae los datos usando selectores CSS. Cada campo se extrae dentro de un bloque `try/except` para no romper el flujo si falla un selector.
- **`ScraperBDNS`**: Orquestador principal. Gestiona el ciclo de vida del navegador (Playwright) y delega la extracción al `HTMLParser`. Soporta modo mock (MVP) y modo real (futuro).

## Estructura
```
modulo1-scraper/
├── src/
│   ├── __init__.py
│   └── scraper.py        # Script principal (HTMLParser + ScraperBDNS)
├── tests/
│   ├── __init__.py
│   └── test_scraper.py   # 15 tests unitarios organizados en 4 clases
├── data/
│   └── ayudas.json       # Datos extraídos siguiendo el contrato (generado dinámicamente)
├── requirements.txt      # Dependencias del módulo
└── README.md             # Esta documentación
```

## Requisitos y Configuración

Antes de ejecutar el scraper, debes instalar sus dependencias en Python y asegurarte de tener disponibles los navegadores para Playwright.

### 1. Activar el entorno virtual

```bash
source ../../venv/bin/activate
```

### 2. Instalar dependencias

Abre la terminal en la raíz de este módulo y ejecuta:

```bash
pip install -r requirements.txt
```

### 3. Instalar navegadores Playwright (⚠️ Obligatorio)

Tras instalar las dependencias, es **indispensable** ejecutar el siguiente comando para que Playwright descargue los binarios del navegador web (ej. Chromium):

```bash
playwright install
```

> **Nota**: En algunos entornos Linux también será necesario instalar las dependencias del sistema operativo con `sudo playwright install-deps` o `sudo apt-get install` de las librerías necesarias.

## Ejecución del Scraper

Para iniciar la extracción, simplemente corre el script principal de la siguiente forma:

```bash
python src/scraper.py
```
Este proceso simulará la navegación/extracción y creará o actualizará el fichero `data/ayudas.json`.

## Ejecución de Pruebas

Para garantizar que el scraper funciona correctamente y que el archivo generado cumple estrictamente al 100% con el contrato de datos requerido, lanza `pytest`:

```bash
PYTHONPATH=. pytest tests/ -v
```

Los tests están organizados en 4 clases:
- **TestDataContract** — Valida que cada registro cumple al 100% con las claves del contrato.
- **TestJSONPersistence** — Verifica la serialización y escritura del archivo JSON.
- **TestScraperIntegration** — Tests de integración con Playwright mockeado (no requieren navegador).
- **TestHTMLParser** — Valida la cobertura del parser sobre el contrato de datos.

## Contrato de Datos

Cada subvención guardada en `data/ayudas.json` debe contener el siguiente esquema de claves inmutable:

| Clave          | Descripción                                            |
|----------------|--------------------------------------------------------|
| `source_id`    | ID oficial de la ayuda (ej. código BDNS).              |
| `title`        | Título completo de la subvención.                      |
| `issuer`       | Órgano que la convoca (ej. Generalitat Valenciana).    |
| `description`  | Texto descriptivo general.                             |
| `beneficiaries`| A quién va dirigida o requisitos clave.                |
| `url`          | Enlace directo y absoluto a la fuente oficial.         |
| `start_date`   | Fecha de inicio de solicitudes.                        |
| `end_date`     | Fecha límite de solicitudes.                           |
| `status`       | Estado de la convocatoria ("Abierta" o "Cerrada").     |
| `source_type`  | Origen de los datos (Fijo: "Portal Web Oficial").      |
| `region`       | Zona a la que aplica (Fijo: "Comunidad Valenciana").   |
