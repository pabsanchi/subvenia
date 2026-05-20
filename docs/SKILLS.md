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
PYTHONPATH=. python src/scraper.py
```

### Ejecutar el Scraper (Modo Real)

1. **Fase A: Extracción Incremental Raw** (descarga y guarda convocatorias raw desde la API de BDNS sin duplicados):
```bash
cd modules/modulo1-scraper
PYTHONPATH=. python src/fetch_raw.py
```

2. **Fase B: Análisis, Enriquecimiento Semántico y Vectorización Atómica** (descarga de PDFs, categorización estructurada con Gemini, y vectorización local con `intfloat/multilingual-e5-base`, con checkpoints resilientes):
```bash
cd modules/modulo1-scraper
PYTHONPATH=. python src/analyze_gemini.py
```

### Instalar/Actualizar Dependencias de Playwright en Linux
Si hay problemas con Playwright en Ubuntu (especialmente en versiones recientes como 24.04 Noble), se deben instalar las versiones `t64` de las librerías del sistema:
```bash
sudo apt-get install -y libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libatspi2.0-0t64 libcairo2 libcups2t64 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0t64 libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2
```
Seguido de la descarga de binarios en el venv:
```bash
playwright install chromium
```
## Módulo 2: Ingesta, Base de Datos y Visualización (Elasticsearch + Kibana en Docker)

### Gestión de Contenedores
El archivo `docker-compose.yaml` está en la raíz del proyecto. Los comandos Docker deben ejecutarse desde ahí:
```bash
cd /home/dev/projects/subvenia
# Levantar en segundo plano
docker compose up -d
# Ver logs de un contenedor
docker logs subvenia_elasticsearch
# Apagar todo
docker compose down
```

### Ejecución de Pruebas (Tests)
El Módulo 2 cuenta con dos suites de pruebas:

1. **Unitarias (Mock):** Validan el mapping y manejo de errores sin levantar Elasticsearch:
```bash
cd modules/modulo2-db
PYTHONPATH=. pytest tests/test_db.py -v
```

2. **Integración (Real):** Interactúan con el contenedor de Elasticsearch insertando datos en un índice temporal y verificando búsquedas reales. Si el contenedor está apagado, hacen `SKIP`.
```bash
cd modules/modulo2-db
PYTHONPATH=. pytest tests/test_integration.py -v
```

### Ejecutar la Ingesta
El script leerá `convocatorias_full.json` del Módulo 1 (ya con vectores reales de 768 dims) y lo inyectará en el índice `ayudas_sociales_full` de Elasticsearch. **Los contenedores deben estar levantados antes de ejecutar esto:**
```bash
cd modules/modulo2-db
PYTHONPATH=. python src/ingest.py
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
PYTHONPATH=. python src/rag_core.py
```

### Ejecutar Pruebas (Tests)
Las pruebas usan mocks y no requieren que Elasticsearch u Ollama estén encendidos:
```bash
cd modules/modulo3-rag
PYTHONPATH=. pytest tests/ -v
```

## Módulo 4: Frontend (Streamlit)

Este módulo proporciona la interfaz gráfica web para interactuar con el motor RAG. 

### Ejecutar la Interfaz de Usuario
Asegúrate de que los contenedores de Elasticsearch están levantados y Ollama está corriendo.
```bash
cd modules/modulo4-frontend
PYTHONPATH=. ../../venv/bin/streamlit run src/app.py
```
La aplicación estará disponible en `http://localhost:8501`.