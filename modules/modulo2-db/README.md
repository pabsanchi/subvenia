# Módulo 2: Base de Datos (Elasticsearch + Kibana)

Este módulo implementa la capa de persistencia y búsqueda del proyecto SubvenIA, utilizando **Elasticsearch 8.14.0** como motor de almacenamiento e indexación y **Kibana 8.14.0** como herramienta de visualización.

## Arquitectura

- **`docker-compose.yaml` (raíz del proyecto):** Define los contenedores de Elasticsearch y Kibana con seguridad habilitada (`xpack.security`).
- **`src/ingest.py`:** Script de ingesta que lee los datos del Módulo 1, crea el índice con un mapping estricto y realiza la carga masiva usando la API bulk.
- **`.env`:** Archivo de secretos locales (no se sube a git) con la contraseña de Elasticsearch.

## Estructura
```
modulo2-db/
├── src/
│   ├── __init__.py
│   └── ingest.py         # Script de ingesta y creación de índice
├── tests/
│   ├── __init__.py
│   └── test_db.py        # Tests unitarios con mocks de Elasticsearch
├── .env                  # Credenciales locales (excluido de git)
├── requirements.txt      # Dependencias del módulo
└── README.md             # Esta documentación
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

### 3. Levantar los contenedores (⚠️ Obligatorio para la ingesta real)
El archivo `docker-compose.yaml` está en la raíz del proyecto:
```bash
cd /home/dev/projects/subvenia
docker compose up -d
```
Esto levantará:
- **Elasticsearch** en `http://localhost:9200`
- **Kibana** en `http://localhost:5601`

## Ejecución de la Ingesta

Con los contenedores levantados, ejecutar:
```bash
PYTHONPATH=. python src/ingest.py
```
El script:
1. Lee las credenciales del `.env`.
2. Crea el índice `ayudas_sociales` con el mapping definido (si no existe).
3. Lee el archivo `modules/modulo1-scraper/data/ayudas.json`.
4. Inyecta un embedding mock (768 ceros) a cada documento.
5. Indexa todo usando la API bulk.

## Ejecución de Pruebas

Los tests se ejecutan sin necesidad de tener los contenedores levantados:
```bash
PYTHONPATH=. pytest tests/ -v
```

## Mapping del Índice `ayudas_sociales`

| Campo           | Tipo           | Detalles                                    |
|-----------------|----------------|---------------------------------------------|
| `source_id`     | `keyword`      | Filtros exactos por ID de la ayuda          |
| `issuer`        | `keyword`      | Filtros exactos por órgano convocante       |
| `status`        | `keyword`      | "Abierta" o "Cerrada"                       |
| `url`           | `keyword`      | Enlace absoluto a la fuente oficial         |
| `source_type`   | `keyword`      | Fijo: "Portal Web Oficial"                  |
| `region`        | `keyword`      | Fijo: "Comunidad Valenciana"                |
| `title`         | `text`         | Analyzer `spanish` para búsquedas full-text |
| `description`   | `text`         | Analyzer `spanish` para búsquedas full-text |
| `beneficiaries` | `text`         | Analyzer `spanish` para búsquedas full-text |
| `start_date`    | `date`         | Fecha de inicio de solicitudes              |
| `end_date`      | `date`         | Fecha límite de solicitudes                 |
| `embedding`     | `dense_vector` | 768 dims, cosine, indexado (kNN ready)      |
