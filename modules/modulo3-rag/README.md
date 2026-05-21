# Módulo 3: Motor RAG (Retrieval-Augmented Generation)

Este módulo implementa el motor de búsqueda semántica y generación de respuestas del proyecto SubvenIA. Conecta **Elasticsearch** (búsqueda vectorial kNN) con **Ollama** (LLM local) para ofrecer respuestas fundamentadas ("grounded") sobre ayudas y subvenciones públicas.

## Arquitectura

- **`src/rag_core.py`:** Clase `RAGCore` que orquesta todo el flujo de Retrieval-Augmented Generation:
  1. Vectoriza la consulta del usuario con el modelo `intfloat/multilingual-e5-base` usando el prefijo asimétrico `query: `.
  2. Busca los documentos más relevantes en el índice `ayudas_sociales_full` de Elasticsearch mediante búsqueda kNN nativa (similitud coseno).
  3. Genera dinámicamente las URLs oficiales de la BDNS (`https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/{numeroConvocatoria}`).
  4. Compila un contexto estructurado con beneficiarios, ámbito geográfico y requisitos, y lo inyecta al LLM local (Llama 3 en Ollama) para generar la respuesta final.

## Estructura
```
modulo3-rag/
├── src/
│   ├── __init__.py
│   └── rag_core.py           # Motor RAG: vectorización de queries, búsqueda kNN y generación con Ollama
├── tests/
│   ├── __init__.py
│   └── test_rag.py           # Tests unitarios con mocks de Elasticsearch y Ollama
├── requirements.txt          # Dependencias del módulo
└── README.md                 # Esta documentación
```

## Requisitos y Configuración

### 1. Activar el entorno virtual
```bash
source ../../venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

> [!NOTE]
> La primera ejecución descargará automáticamente los pesos del modelo de embeddings `intfloat/multilingual-e5-base` (aprox. 1.1 GB). Tras la primera descarga, se cachea localmente.

### 3. Requisitos previos de infraestructura
- **Elasticsearch** debe estar levantado y con el índice `ayudas_sociales_full` poblado (ver Módulo 2).
- **Ollama** debe estar corriendo en `http://localhost:11434` con el modelo `llama3` descargado:
  ```bash
  ollama run llama3
  ```

### 4. Variables de entorno
El módulo reutiliza el archivo `.env` del Módulo 2 (`modules/modulo2-db/.env`) para leer `ELASTIC_PASSWORD`.

## Ejecución

### Prueba del Pipeline RAG
Ejecuta una consulta de prueba hardcodeada ("¿Hay ayudas para digitalizar mi comercio?") para validar la conexión completa entre Elasticsearch y Ollama:
```bash
cd modules/modulo3-rag
PYTHONPATH=. python src/rag_core.py
```
O desde la raíz del proyecto:
```bash
PYTHONPATH=. python modules/modulo3-rag/src/rag_core.py
```

### Ejecución de Pruebas (Tests)
Las pruebas usan mocks y **no requieren** que Elasticsearch ni Ollama estén encendidos:
```bash
cd modules/modulo3-rag
PYTHONPATH=. pytest tests/ -v
```

## Detalles Técnicos

### Modelo de Embeddings: `intfloat/multilingual-e5-base`
Este modelo es **asimétrico**, lo cual requiere un tratamiento especial de los prefijos:
- **Para indexar pasajes** (en el Módulo 1, `vectorizer.py`): Se usa el prefijo `passage: `.
- **Para buscar/consultar** (en este módulo, `rag_core.py`): Se usa el prefijo `query: `.

Mezclar o eliminar estos prefijos degradaría drásticamente la calidad de la búsqueda semántica.

### Generación Dinámica de URLs
En lugar de almacenar las URLs en la base de datos, el RAG las reconstruye dinámicamente a partir del campo `numeroConvocatoria`:
```
https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/{numeroConvocatoria}
```
Esto garantiza que el enlace oficial siempre apunte al portal de transparencia de la BDNS (Ministerio de Hacienda), incluso si el formato de la URL cambiase en el futuro (bastaría con actualizar la plantilla en un solo sitio).

### Contexto Estructurado para el LLM
El contexto que se inyecta a Ollama incluye campos formateados de forma legible:
- **Título y descripción** de la convocatoria.
- **Situación familiar, laboral, vulnerabilidad y colectivos generales**, extraídos dinámicamente de los sub-diccionarios de booleanos.
- **Ámbito geográfico** (nivel y región).
- **Requisitos de residencia** y otras condiciones.
- **URL oficial** generada dinámicamente.
