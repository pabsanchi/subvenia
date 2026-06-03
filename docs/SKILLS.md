# 🛠️ Habilidades y Comandos (SKILLS.md)

Este documento centraliza las "skills" o flujos de trabajo habituales en el repositorio para que los agentes o desarrolladores puedan retomarlos rápidamente.

## Entorno Virtual
Para operar en este proyecto, siempre se debe usar el entorno virtual centralizado:
```bash
source /home/dev/projects/subvenia/venv/bin/activate
```

## Módulo 1: Scraper

### Ejecutar Pruebas (Tests)

> [!IMPORTANT]
> Para evitar errores de tipo `ModuleNotFoundError` en entornos Linux, ejecuta siempre `pytest` invocando al intérprete de Python del entorno virtual (`python -m pytest` o usando la ruta absoluta).

1. **Pruebas de Simulación MVP:** Validan la persistencia JSON, parseo de HTML y el Contrato de Datos:
```bash
cd modules/modulo1-scraper
python -m pytest tests/test_scraper.py -v
```

2. **Pruebas del Scraper Real y Gemini:** Validan la lógica de recogida incremental, enriquecimiento con Gemini, limpieza local de PDFs temporales y propagación de errores de cuota/API:
```bash
cd modules/modulo1-scraper
python -m pytest tests/test_real_scraper.py -v
```
*(De forma explícita: `/home/dev/projects/subvenia/venv/bin/python -m pytest tests/test_real_scraper.py -v`)*.

### Ejecutar el Scraper (Modo Simulación)
Genera el archivo `data/ayudas.json` usando el HTML simulado de la BDNS.
```bash
cd modules/modulo1-scraper
python src/scraper.py
```

### Ejecutar el Scraper (Modo Real)

1. **Fase A: Extracción Incremental Raw** (descarga y guarda convocatorias raw desde la API de BDNS sin duplicados):
```bash
cd modules/modulo1-scraper
python src/fetch_raw.py
```

2. **Fase B: Análisis, Enriquecimiento Semántico y Vectorización Atómica** (descarga de PDFs, categorización estructurada con Gemini, y vectorización local con `intfloat/multilingual-e5-base`, con checkpoints resilientes):
```bash
cd modules/modulo1-scraper
python src/analyze_gemini.py
```

## Módulo 5: Buscador filtrado

### Ejecutar Tests
```bash
cd modules/modulo5-buscador
python -m pytest tests/test_buscador.py -v
```

## Módulo 6: Mapa de recursos sociales

### Ejecutar Tests
```bash
cd modules/modulo6-recursos
python -m pytest tests/test_recursos.py -v
```

## Módulo 2: Ingesta en MongoDB Atlas

### Ejecución de Pruebas (Tests)

1. **Unitarias (Mock):** Validan la lógica de ingesta y manejo de errores sin conexión real:
```bash
cd modules/modulo2-db
python -m pytest tests/test_db.py -v
```

2. **Integración (Real):** Requieren `MONGO_URI` configurado. Si no hay conexión, hacen `SKIP` automáticamente:
```bash
cd modules/modulo2-db
python -m pytest tests/test_integration.py -v
```

### Ejecutar la Ingesta
```bash
python modules/modulo2-db/src/ingest.py
```

### Retroalimentar campos Gemini (documentos existentes)
Para añadir `status`, `aid_type` y `granting_body_level` a documentos procesados antes del fix:
```bash
# Previsualizar sin escribir
python modules/modulo2-db/src/backfill_gemini_fields.py --dry-run
# Ejecutar
python modules/modulo2-db/src/backfill_gemini_fields.py
```

## Módulo 3: Motor RAG (Retrieval-Augmented Generation)

Este módulo conecta Elasticsearch (índice `ayudas_sociales_full`) y Ollama para generar respuestas contextuales con URLs oficiales de la BDNS.

### Requisitos Previos
1. Contenedores de Elasticsearch levantados y con los datos vectorizados indexados en el índice `ayudas_sociales_full`.
2. Servidor local de Ollama corriendo en el puerto `11434` con el modelo `llama3` descargado (`ollama run llama3`).

### Ejecutar el Motor RAG (Prueba)
Ejecutará una pregunta de prueba hardcodeada para validar la búsqueda semántica kNN en `ayudas_sociales_full` y la generación de respuesta con Ollama. Nota: la primera ejecución descargará los pesos del modelo de embeddings `intfloat/multilingual-e5-base` (aprox. 1.1GB).
```bash
cd modules/modulo3-rag
python src/rag_core.py
```

### Ejecutar Pruebas (Tests)
Las pruebas usan mocks y no requieren que Elasticsearch u Ollama estén encendidos:
```bash
cd modules/modulo3-rag
pytest tests/ -v
```

## Módulo 4: Frontend (Streamlit)

Este módulo proporciona la interfaz gráfica web para interactuar con el motor RAG. 

### Ejecutar la Interfaz de Usuario
Asegúrate de que los contenedores de Elasticsearch están levantados y Ollama está corriendo.
```bash
cd modules/modulo4-frontend
../../venv/bin/streamlit run src/app.py
```
La aplicación estará disponible en `http://localhost:8501`.