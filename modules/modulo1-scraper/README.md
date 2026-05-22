# Módulo 1: Scraper

Este módulo conforma la primera etapa del proyecto SubvenIA, encargándose de la extracción y estructuración de los datos provenientes de portales web (ej. Base de Datos Nacional de Subvenciones).

Cuenta con dos modos de funcionamiento completamente operativos:
1. **Modo Simulación (MVP)**: Raspado web simulado mediante Playwright y parsing HTML local.
2. **Modo Real (API REST + Gemini)**: Descarga incremental de convocatorias desde la API de BDNS y análisis semántico profundo empleando modelos fundacionales de Google Gemini.

---

## Arquitectura

El scraper sigue un diseño modular con separación de responsabilidades:

* **`HTMLParser`**: Componente de parseo puro. Recibe una página de Playwright y extrae los datos usando selectores CSS. Cada campo se extrae dentro de un bloque `try/except` para no romper el flujo si falla un selector.
* **`ScraperBDNS`**: Orquestador de simulación. Gestiona el ciclo de vida del navegador (Playwright) y delega la extracción al `HTMLParser`.
* **`fetch_raw.py` (Scraper Real API)**: Descarga de forma incremental todas las convocatorias oficiales del portal BDNS aplicando filtros (Comunidad Valenciana, destinatarios personas físicas). Evita duplicidades validando IDs ya existentes.
* **`analyze_gemini.py` (Análisis y Enriquecimiento)**: Lee las convocatorias raw, descarga los PDFs oficiales de cada subvención localmente de forma temporal, los sube a la API de Gemini (`gemini-2.5-flash-lite`) para realizar una extracción y clasificación de requisitos estructurada bajo un esquema JSON de tipos estrictos, y consolida los resultados enriquecidos.
* **`vectorizer.py` (Vectorización Atómica) [NUEVO]**: Toma la convocatoria enriquecida, compila todos sus campos de beneficiarios y requisitos en un texto descriptivo fluido en español, y genera de forma local el vector de embedding correspondiente (768 dimensiones) usando el modelo `intfloat/multilingual-e5-base` de `SentenceTransformer`. El vector es inyectado de forma atómica en el mismo flujo de guardado de Gemini, garantizando consistencia total de datos.

---

## Estructura

```
modulo1-scraper/
├── src/
│   ├── __init__.py
│   ├── scraper.py                    # Script MVP de simulación de raspado web (Playwright)
│   ├── fetch_raw.py                  # Script de extracción real incremental desde la API de BDNS
│   ├── analyze_gemini.py             # Script de descarga de PDFs y análisis semántico con Gemini
│   └── vectorizer.py                 # [NUEVO] Vectorizador local SentenceTransformer (E5) para guardado atómico
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py               # 15 tests unitarios organizados en 4 clases para la simulación
│   └── test_real_scraper.py          # Tests unitarios del flujo real de BDNS, vectorizador y control de errores
├── data/
│   ├── ayudas.json                   # Datos de ayudas generados por la simulación
│   ├── lista_convocatorias_raw.json  # Convocatorias crudas recogidas incrementalmente de la API
│   ├── seguimiento_procesos.json     # Registro de checkpoints y contadores de progreso
│   └── convocatorias_full.json       # Convocatorias finales enriquecidas con análisis semántico y embeddings
├── requirements.txt                  # Dependencias del módulo actualizadas (playwright, bdns-fetch, google-generativeai, sentence-transformers)
└── README.md                         # Esta documentación
```

---

## Requisitos y Configuración

Antes de ejecutar el scraper, debes activar tu entorno virtual e instalar las dependencias necesarias.

### 1. Activar el entorno virtual

```bash
source ../../venv/bin/activate
```

### 2. Instalar dependencias

Abre la terminal en la raíz de este módulo (`modules/modulo1-scraper`) y ejecuta:

```bash
pip install -r requirements.txt
```

### 3. Instalar navegadores Playwright (requerido para la simulación)

```bash
playwright install chromium
```

### 4. Configurar variables de entorno

Para utilizar el **Modo Real**, asegúrate de disponer de tu clave de API en el archivo `.env` en la raíz del proyecto o en `modules/modulo2-db/.env`:

```env
GEMINI_API_KEY=tu_clave_api_aquí
```

---

## Ejecución del Scraper

### 1. Modo Simulación (MVP)
Para iniciar la extracción simulada sobre portales HTML de ejemplo:
```bash
python src/scraper.py
```
Generará o actualizará el archivo `data/ayudas.json`.

### 2. Modo Real (API REST + Gemini)
El flujo real de recogida y procesamiento semántico se divide en dos fases independientes:

#### Fase A: Recogida Incremental Raw
Descarga de forma incremental todas las nuevas convocatorias publicadas en BDNS desde la fecha del último éxito (o por defecto desde el 1 de enero de 2026) hasta hoy:
```bash
python src/fetch_raw.py
```
Genera o actualiza el archivo `data/lista_convocatorias_raw.json` y actualiza la fecha en `data/seguimiento_procesos.json`.

#### Fase B: Análisis Semántico, Clasificación y Vectorización Atómica con Gemini
Descarga los PDFs de las convocatorias crudas pendientes de procesar, realiza el análisis semántico detallado de requisitos (colectivos, edad, nivel de administración, plazos, etc.) con Gemini, compila el texto estructurado en español y genera de forma local sus vectores de embeddings (768 dims) antes de almacenarlos. Todo se consolida y guarda de forma atómica en `data/convocatorias_full.json`:
```bash
python src/analyze_gemini.py
```

* **Vectorización Local Atómica:** Utiliza de forma local el modelo `intfloat/multilingual-e5-base` para codificar semánticamente toda la convocatoria, previniendo estados inconsistentes de almacenamiento (guardado de metadatos sin vectores).
* **Resiliencia de Checkpoint:** Su ejecución lee y actualiza el contador en `data/seguimiento_procesos.json`. Si se interrumpe el proceso, se reanudará exactamente desde donde se detuvo sin duplicar peticiones de Gemini ni de vectorización.
* **Control de Cuotas y Errores de API:** Si se agota la cuota (error 429) o el servicio de Google no está disponible (error 503), el script detiene la ejecución inmediatamente y alerta por consola para evitar descargas innecesarias y pérdida de datos.

---

## Ejecución de Pruebas

Para garantizar que el scraper funciona correctamente en ambos modos, el proyecto incorpora suites de pruebas con `pytest`.

> [!IMPORTANT]
> Para evitar errores de tipo `ModuleNotFoundError` al ejecutar pruebas en Linux, asegúrate de invocar a `pytest` usando la versión de Python del propio entorno virtual (o ejecutando con `python -m pytest`).

### 1. Ejecutar Pruebas de Simulación MVP
Valida la extracción del parser HTML, la serialización JSON y el cumplimiento del Contrato de Datos original:
```bash
python -m pytest tests/test_scraper.py -v
```

### 2. Ejecutar Pruebas del Scraper Real y Gemini
Valida la ingesta incremental sin duplicados, el enriquecimiento, la eliminación automática de PDFs locales, y la propagación de errores de cuota (429/503) empleando mocks avanzados de SDK y red:
```bash
python -m pytest tests/test_real_scraper.py -v
```
*(Alternativamente, puedes ejecutarlo de forma directa invocando al binario de Python del entorno virtual: `/home/dev/projects/subvenia/venv/bin/python -m pytest tests/test_real_scraper.py -v`)*.

---

## Contrato de Datos (Simulación)

Cada subvención guardada en `data/ayudas.json` contiene el siguiente esquema de claves inmutable:

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

---

## Contrato de Datos (Convocatorias Reales Enriquecidas)

Cada convocatoria guardada en `data/convocatorias_full.json` contiene el siguiente esquema:

### Campos Principales

| Clave                | Tipo       | Descripción                                                |
|----------------------|------------|------------------------------------------------------------|
| `id`                 | `int`      | Identificador numérico único de la convocatoria BDNS.      |
| `mrr`                | `bool`     | Indicador de Mecanismo de Recuperación y Resiliencia.       |
| `numeroConvocatoria` | `str`      | Código oficial BDNS de la convocatoria.                    |
| `descripcion`        | `str`      | Título/descripción principal de la convocatoria.           |
| `descripcionLeng`    | `str/null` | Descripción en lengua cooficial (si aplica).               |
| `fechaRecepcion`     | `str`      | Fecha de publicación (formato `YYYY-MM-DD`).               |
| `nivel1`             | `str`      | Nivel administrativo (AUTONOMICA, LOCAL, OTROS...).        |
| `nivel2`             | `str`      | Organismo o comunidad autónoma.                            |
| `nivel3`             | `str/null` | Entidad concreta (Ayuntamiento, Secretaría, etc.).         |
| `codigoInvente`      | `str/null` | Código INVENTE (si aplica).                                |
| `deadline`           | `str`      | Fecha límite de solicitud (formato flexible).              |
| `embedding`          | `list[float]` | Vector de 768 dimensiones (multilingual-e5-base).       |

### Objeto `geographic_scope`

| Clave         | Tipo  | Descripción                                         |
|---------------|-------|-----------------------------------------------------|
| `level`       | `str` | Nivel geográfico (autonomico, municipal, etc.).     |
| `region_name` | `str` | Nombre de la región o municipio.                    |

### Objeto `beneficiaries`

| Clave                      | Tipo         | Descripción                                               |
|----------------------------|--------------|-----------------------------------------------------------|
| `situacion_familiar`       | `dict[bool]` | Sub-diccionario de booleanos (familia numerosa, etc.).    |
| `situacion_laboral`        | `dict[bool]` | Sub-diccionario de booleanos (empleado, desempleado...).  |
| `vulnerabilidad`           | `dict[bool]` | Sub-diccionario de booleanos (discapacidad, violencia...).|
| `colectivos_generales`     | `dict[bool]` | Sub-diccionario de booleanos (menores, jóvenes, pymes...).|
| `age_min`                  | `int/null`   | Edad mínima requerida.                                    |
| `age_max`                  | `int/null`   | Edad máxima requerida.                                    |
| `income_threshold`         | `str/null`   | Límite de ingresos (si aplica).                           |
| `requires_residency`       | `bool/null`  | Si requiere residencia obligatoria.                       |
| `residency_scope`          | `str/null`   | Ámbito territorial de residencia requerida.               |
| `compatible_with_other_aids`| `bool/null` | Compatible con otras ayudas.                              |
| `other_conditions`         | `str/null`   | Condiciones adicionales de texto libre.                   |

