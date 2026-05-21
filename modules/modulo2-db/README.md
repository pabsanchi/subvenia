# Módulo 2: Base de Datos (Elasticsearch + Kibana)

Este módulo implementa la capa de persistencia y búsqueda del proyecto SubvenIA, utilizando **Elasticsearch 8.14.0** como motor de almacenamiento e indexación y **Kibana 8.14.0** como herramienta de visualización.

## Arquitectura

- **`docker-compose.yaml` (raíz del proyecto):** Define los contenedores de Elasticsearch y Kibana con seguridad habilitada (`xpack.security`).
- **`src/ingest.py`:** Script de ingesta que lee las convocatorias enriquecidas y ya vectorizadas del Módulo 1, crea el índice con un mapping estricto adaptado al esquema completo y realiza la carga masiva usando la API bulk.
- **`src/update_embeddings.py`:** *(Legacy/Obsoleto)* Script de actualización parcial de embeddings para el antiguo índice `ayudas_sociales`. Conservado como referencia histórica. Ya no es necesario porque los vectores se generan atómicamente en el Módulo 1.
- **`.env`:** Archivo de secretos locales (no se sube a git) con la contraseña de Elasticsearch y la API Key de Gemini.

## Estructura
```
modulo2-db/
├── src/
│   ├── __init__.py
│   ├── ingest.py              # Script de ingesta al índice ayudas_sociales_full
│   └── update_embeddings.py   # (Legacy) Actualización parcial de embeddings
├── tests/
│   ├── __init__.py
│   └── test_db.py             # Tests unitarios con mocks de Elasticsearch
├── .env                       # Credenciales locales (excluido de git)
├── requirements.txt           # Dependencias del módulo
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

Con los contenedores levantados, ejecutar desde la raíz del proyecto:
```bash
PYTHONPATH=. python modules/modulo2-db/src/ingest.py
```
O bien desde el directorio del módulo:
```bash
cd modules/modulo2-db
PYTHONPATH=. python src/ingest.py
```

El script:
1. Lee las credenciales del `.env`.
2. Crea el índice `ayudas_sociales_full` con el mapping adaptado al esquema enriquecido (si no existe).
3. Lee el archivo `modules/modulo1-scraper/data/convocatorias_full.json` (convocatorias ya vectorizadas por el Módulo 1).
4. Valida que cada documento contiene el campo `embedding` pre-calculado. Si algún documento carece de vector, se omite con un warning.
5. Indexa todo usando la API bulk.

> [!IMPORTANT]
> Los embeddings ya no son mocks de ceros. El Módulo 1 genera vectores reales de 768 dimensiones usando el modelo `intfloat/multilingual-e5-base` de forma atómica durante el enriquecimiento con Gemini. El script `update_embeddings.py` ya **no es necesario** en el flujo actual.

## Ejecución de Pruebas

### Pruebas Unitarias (Mock)
Los tests unitarios se ejecutan sin necesidad de tener los contenedores levantados:
```bash
cd modules/modulo2-db
PYTHONPATH=. pytest tests/test_db.py -v
```

### Pruebas de Integración (Real)
Las pruebas de integración interactúan con el contenedor real de Elasticsearch. Si el contenedor no está disponible, las pruebas se saltarán automáticamente (`SKIP`) para no romper el flujo:
```bash
cd modules/modulo2-db
PYTHONPATH=. pytest tests/test_integration.py -v
```
*(También puedes ejecutar `pytest tests/ -v` para lanzar ambas suites).*

## Mapping del Índice `ayudas_sociales_full`

El índice utiliza un mapping estricto adaptado al esquema de convocatorias completas enriquecidas:

### Campos Principales

| Campo                | Tipo           | Detalles                                                |
|----------------------|----------------|---------------------------------------------------------|
| `id`                 | `integer`      | Identificador numérico único de la convocatoria         |
| `mrr`                | `boolean`      | Indicador de Mecanismo de Recuperación y Resiliencia     |
| `numeroConvocatoria` | `keyword`      | Código oficial BDNS de la convocatoria                  |
| `descripcion`        | `text`         | Analyzer `spanish` para búsquedas full-text             |
| `descripcionLeng`    | `text`         | Analyzer `spanish`, descripción en lengua cooficial     |
| `fechaRecepcion`     | `date`         | Fecha de publicación/recepción de la convocatoria       |
| `nivel1`             | `keyword`      | Nivel administrativo (AUTONOMICA, LOCAL, OTROS...)       |
| `nivel2`             | `keyword`      | Organismo o comunidad (COMUNITAT VALENCIANA, etc.)      |
| `nivel3`             | `keyword`      | Entidad concreta (Ayuntamiento, Secretaría, etc.)       |
| `codigoInvente`      | `keyword`      | Código INVENTE (si aplica)                              |
| `deadline`           | `keyword`      | Fecha límite de solicitud (formato flexible)            |
| `embedding`          | `dense_vector` | 768 dims, cosine, indexado (kNN ready, vectores reales) |

### Objeto `geographic_scope`

| Campo         | Tipo      | Detalles                                        |
|---------------|-----------|------------------------------------------------|
| `level`       | `keyword` | Nivel geográfico (autonomico, municipal, etc.) |
| `region_name` | `keyword` | Nombre de la región o municipio                |

### Objeto `beneficiaries`

| Campo                     | Tipo      | Detalles                                                 |
|---------------------------|-----------|----------------------------------------------------------|
| `situacion_familiar`      | `object`  | Sub-diccionario de campos booleanos (familia_numerosa...)|
| `situacion_laboral`       | `object`  | Sub-diccionario de campos booleanos (empleado, paro...)  |
| `vulnerabilidad`          | `object`  | Sub-diccionario de campos booleanos (discapacidad...)    |
| `colectivos_generales`    | `object`  | Sub-diccionario de campos booleanos (menores, jovenes...)|
| `age_min`                 | `integer` | Edad mínima requerida                                    |
| `age_max`                 | `integer` | Edad máxima requerida                                    |
| `income_threshold`        | `keyword` | Límite de ingresos (si aplica)                           |
| `requires_residency`      | `boolean` | Si requiere residencia obligatoria                       |
| `residency_scope`         | `keyword` | Ámbito territorial de residencia requerida               |
| `compatible_with_other_aids` | `boolean` | Compatible con otras ayudas                            |
| `other_conditions`        | `text`    | Analyzer `spanish`, condiciones adicionales de texto libre|

> [!NOTE]
> El antiguo índice `ayudas_sociales` (del MVP original) sigue existiendo en Elasticsearch con los datos de simulación. El nuevo índice `ayudas_sociales_full` es el que utiliza el RAG en producción con convocatorias reales enriquecidas y vectorizadas.
