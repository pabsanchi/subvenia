# Módulo 1: Scraper

Este módulo conforma la primera etapa del proyecto SubvenIA, encargándose de la extracción y estructuración de los datos provenientes de portales web (ej. Base de Datos Nacional de Subvenciones). 
En su versión actual, opera bajo un enfoque MVP (Minimum Viable Product), extrayendo ayudas orientadas a la **Comunidad Valenciana** y persistiendo la información localmente en un formato JSON estricto.

## Estructura
```
modulo1-scraper/
├── src/
│   └── scraper.py        # Script principal que extrae la información
├── tests/
│   └── test_scraper.py   # Batería de pruebas unitarias
├── data/
│   └── ayudas.json       # Datos extraídos siguiendo el contrato (generado dinámicamente)
├── requirements.txt      # Dependencias del módulo
└── README.md             # Esta documentación
```

## Requisitos y Configuración

Antes de ejecutar el scraper, debes instalar sus dependencias en Python y asegurarte de tener disponibles los navegadores para Playwright.

### 1. Instalar dependencias

Abre la terminal en la raíz de este módulo y ejecuta:

```bash
pip install -r requirements.txt
```

### 2. Instalar navegadores Playwright (Obligatorio)

Tras instalar las dependencias, es indispensable ejecutar el siguiente comando para que Playwright descargue los binarios del navegador web (ej. Chromium):

```bash
playwright install
```

## Ejecución del Scraper

Para iniciar la extracción, simplemente corre el script principal de la siguiente forma:

```bash
python src/scraper.py
```
Este proceso simulará la navegación/extracción y creará o actualizará el fichero `data/ayudas.json`.

## Ejecución de Pruebas

Para garantizar que el scraper funciona correctamente y que el archivo generado cumple estrictamente al 100% con el contrato de datos requerido, lanza `pytest`:

```bash
pytest tests/
```

## Contrato de Datos

Cada subvención guardada en `data/ayudas.json` debe contener el siguiente esquema de claves inmutable:

- `source_id`: ID oficial de la ayuda (ej. código BDNS).
- `title`: Título completo de la subvención.
- `issuer`: Órgano que la convoca (ej. Generalitat Valenciana).
- `description`: Texto descriptivo general.
- `beneficiaries`: A quién va dirigida o requisitos clave.
- `url`: Enlace directo y absoluto a la fuente oficial.
- `start_date`: Fecha de inicio de solicitudes.
- `end_date`: Fecha límite de solicitudes.
- `status`: Estado de la convocatoria ("Abierta" o "Cerrada").
- `source_type`: Origen de los datos (Fijo: "Portal Web Oficial").
- `region`: Zona a la que aplica (Fijo: "Comunidad Valenciana").
