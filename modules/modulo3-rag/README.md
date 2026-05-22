# Módulo 3: Motor RAG (Retrieval-Augmented Generation)

Este módulo implementa el motor de búsqueda semántica y generación de respuestas del proyecto SubvenIA. Conecta **MongoDB Atlas** (búsqueda vectorial mediante `$vectorSearch`) con **Ollama** (LLM local) para ofrecer respuestas fundamentadas ("grounded") sobre ayudas y subvenciones públicas.

## Arquitectura

- **`src/rag_core.py`:** Clase `RAGCore` que orquesta todo el flujo de Retrieval-Augmented Generation:
  1. Vectoriza la consulta del usuario con el modelo `intfloat/multilingual-e5-base` usando el prefijo asimétrico `query: `.
  2. Busca los documentos más relevantes en la colección `convocatorias` de MongoDB Atlas mediante el pipeline `$vectorSearch`.
  3. Genera dinámicamente las URLs oficiales de la BDNS (`https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/{numeroConvocatoria}`).
  4. Compila un contexto estructurado con beneficiarios booleanos, ámbito geográfico y requisitos, y lo inyecta al LLM local (Ollama) para generar la respuesta final.
- **`src/warmup_ollama.py`:** Script auxiliar que "despierta" el modelo de Ollama forzándolo a cargarse en memoria RAM, resolviendo el problema del *cold start* (arranque lento en la primera pregunta).

## Estructura
```
modulo3-rag/
├── src/
│   ├── __init__.py
│   ├── rag_core.py           # Motor RAG principal
│   └── warmup_ollama.py      # Script de calentamiento para Ollama
├── tests/
│   ├── __init__.py
│   └── test_rag.py           # Tests unitarios
├── requirements.txt          # Dependencias del módulo
└── README.md                 # Esta documentación
```

## Requisitos y Configuración

### 1. Activar el entorno virtual e instalar
```bash
source ../../venv/bin/activate
pip install -r requirements.txt
```

### 2. Requisitos previos de infraestructura
- **MongoDB Atlas** debe tener los datos ingestados (ver Módulo 2) y el índice `vector_index` creado.
- **Ollama** debe estar corriendo en `http://localhost:11434` con el modelo `llama3` descargado (`ollama run llama3`).

### 3. Variables de entorno
El módulo lee `MONGO_URI` del archivo `.env` del Módulo 2.

## Ejecución (Pruebas Manuales)

### Warmup de Ollama (Cold Start Fix)
Para evitar que la primera consulta tarde demasiado:
```bash
python modules/modulo3-rag/src/warmup_ollama.py
```

### Prueba del Pipeline RAG
Ejecuta una consulta de prueba hardcodeada ("¿Hay ayudas para digitalizar mi comercio?"):
```bash
python modules/modulo3-rag/src/rag_core.py
```
