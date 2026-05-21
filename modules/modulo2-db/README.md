# Módulo 2: Base de Datos (MongoDB Atlas)

Este módulo implementa la capa de persistencia y búsqueda del proyecto SubvenIA, utilizando **MongoDB Atlas** como motor de almacenamiento y permitiendo búsquedas vectoriales nativas en la nube.

## Arquitectura

- **`src/ingest.py`:** Script de ingesta que lee las convocatorias enriquecidas y ya vectorizadas del Módulo 1 y realiza la carga masiva usando `pymongo` (función `insert_many`).
- **`.env`:** Archivo de secretos locales (no se sube a git) que debe contener la variable `MONGO_URI`.

## Estructura
```
modulo2-db/
├── src/
│   ├── __init__.py
│   └── ingest.py              # Script de ingesta hacia MongoDB Atlas
├── tests/
│   ├── __init__.py
│   └── test_db.py             # Tests unitarios
├── .env                       # Credenciales locales (excluido de git)
├── requirements.txt           # Dependencias del módulo (pymongo)
└── README.md                  # Esta documentación
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

### 3. Configurar MongoDB Atlas
Debes tener un clúster creado en MongoDB Atlas y agregar tu URI de conexión al archivo `.env`:
```env
MONGO_URI="mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
```

## Ejecución de la Ingesta

Ejecutar desde la raíz del proyecto:
```bash
PYTHONPATH=. python modules/modulo2-db/src/ingest.py
```

El script:
1. Lee la credencial `MONGO_URI` del `.env`.
2. Se conecta al clúster y limpia la colección antigua (para evitar duplicados en el MVP).
3. Inserta todos los documentos validados en la base de datos `subvenia`, colección `convocatorias`.

## Creación del Índice Vectorial (MUY IMPORTANTE)

Para que el Módulo 3 (RAG) funcione, **DEBES** crear un Vector Search Index en la interfaz de MongoDB Atlas:
1. Ve a **Atlas Search**.
2. Haz clic en **Create Search Index** -> **JSON Editor**.
3. Selecciona la colección `convocatorias` y ponle de nombre `vector_index`.
4. Pega este JSON:
```json
{
  "fields": [
    {
      "numDimensions": 768,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    }
  ]
}
```
