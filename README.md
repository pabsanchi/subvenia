# SubvenIA — Repositorio Principal

SubvenIA es un sistema basado en IA diseñado para ayudar a los ciudadanos de la Comunitat Valenciana a encontrar ayudas públicas, subvenciones y recursos sociales. Combina un motor RAG conversacional para usuarios con poca experiencia digital con un buscador filtrado avanzado y un mapa de recursos sociales físicos.

Este proyecto sigue una arquitectura **Monorepo** y ha migrado su capa de datos a **MongoDB Atlas**.

---

## Guía de instalación: 

Si es la primera vez que descargas el repositorio, simplemente ejecuta el instalador automatizado. Este script preparará el entorno virtual, instalará todas las dependencias cruzadas y creará un archivo `.env` de plantilla:
```bash
./install.sh
```

> [!IMPORTANT]
> **Configuración obligatoria:** Abre el archivo `.env` generado en la raíz y configura tus credenciales (`GEMINI_API_KEY` y `MONGO_URI`). Sin datos en MongoDB el asistente no puede responder.

---

## Guía rápida de ejecución (paso a paso)

### Paso 0: Entorno

```bash
source venv/bin/activate
```

### Paso 1: Recogida de Convocatorias (Scraper)
Este script se conecta a la API oficial de la BDNS para descargar nuevas convocatorias de forma incremental (sin duplicados).
```bash
python modules/modulo1-scraper/src/fetch_raw.py
```

### Paso 2: Análisis semántico y vectorización (Gemini)

Descarga los PDFs oficiales, los procesa con Gemini y genera vectores localmente:

```bash
python modules/modulo1-scraper/src/analyze_gemini.py
```

### Paso 3: Subida a la base de datos (MongoDB Atlas)

```bash
python modules/modulo2-db/src/ingest.py
```

*(Requiere `MONGO_URI` en `.env` y el índice vectorial `autoembed_index` creado en Atlas.)*

### Paso 4: Levantar la aplicación

```bash
./start_frontEnd.sh
```

> [!TIP]
> Para detener: `./stop_frontEnd.sh` o simplemente `control + c`

---

## Modos de uso

SubvenIA ofrece tres herramientas accesibles desde la barra lateral de navegación:

### Asistente de ayudas
**Para:** Usuarios con poca experiencia digital (personas mayores, etc.)  
**Cómo funciona:** El usuario describe su situación en lenguaje natural y recibe una respuesta personalizada. Sin necesidad de conocer categorías ni filtros.  
**Fuente de datos:** BDNS (vía MongoDB Atlas + Ollama/Llama3)

### Buscador de ayudas
**Para:** Usuarios que prefieren explorar con filtros  
**Cómo funciona:** El usuario selecciona su perfil (situación laboral, familiar, colectivo, vulnerabilidad) y aplica filtros adicionales (tipo de ayuda, ámbito geográfico). Muestra las convocatorias abiertas de la BDNS que coinciden, paginadas de 20 en 20.  
**Fuente de datos:** BDNS (vía MongoDB Atlas, Módulo 5)

### Recursos sociales
**Para:** Usuarios de cualquier perfil que necesiten saber dónde ir en persona  
**Cómo funciona:** Mapa interactivo y listado de centros, asociaciones y servicios sociales del Ayuntamiento de Valencia, filtrable por colectivo. Clic en un punto del mapa o en un botón del listado para ver los detalles y centrar el mapa.  
**Fuente de datos:** Portal de Datos Abiertos del Ayuntament de València (`opendata.vlci.valencia.es`), categoría Sociedad y Bienestar, licencia CC BY 4.0

---

## Documentación para agentes y desarrolladores

- **[docs/AGENTS.md](./docs/AGENTS.md):** Reglas de comportamiento, arquitectura y roles para agentes IA.
- **[docs/SKILLS.md](./docs/SKILLS.md):** Comandos de entorno virtual y testing.

---

## Estado del proyecto y módulos

### Módulo 1: Scraper (`modules/modulo1-scraper/`)
**Estado:** Operativo

- Descarga convocatorias de la BDNS via API oficial (`bdns-fetch`).
- Usa `gemini-2.5-flash-lite` (`google-genai`) para extraer estructura semántica: beneficiarios (booleanos por colectivo), tipo de ayuda, estado, ámbito geográfico, fecha límite.
- El prompt de Gemini está en `src/prompt.txt` — editarlo directamente para ajustar la clasificación sin tocar código Python.
- El prompt incluye definiciones detalladas por categoría para evitar errores frecuentes (ej: `personas_mayores` solo aplica a tercera edad, no a "mayores de X años" genérico) y fuerza clasificación multi-etiqueta.
- Vectoriza con `intfloat/multilingual-e5-base` (768 dimensiones).
- **Los campos `status`, `aid_type`, `frequency` y `granting_body_level` se guardan desde esta versión** para habilitar el buscador filtrado (Módulo 5).

### Módulo 2: Ingesta en base de datos (`modules/modulo2-db/`)
**Estado:** Operativo

- Upsert masivo a MongoDB Atlas con el `id` de la convocatoria como `_id`.
- Búsqueda semántica via índice `autoembed_index` (Atlas Vector Search).
- `backfill_gemini_fields.py` — script de retroalimentación para documentos procesados antes de la corrección de `analyze_gemini.py`. Deriva `status` (desde `deadline` con dateparser), `aid_type` (keyword matching en `descripcion`) y `granting_body_level` (desde `nivel1` BDNS) sin necesidad de re-procesar los PDFs. Idempotente: solo actualiza campos ausentes. Admite `--dry-run`.

### Módulo 3: Motor RAG (`modules/modulo3-rag/`)
**Estado:** Operativo

- Convierte la pregunta del usuario en vector → `$vectorSearch` en MongoDB (umbral 0.85) → contexto estructurado → Ollama Llama 3 → respuesta en lenguaje natural.
- Filtra convocatorias cerradas en el pipeline de agregación (`$match status != "cerrada"` tras `$vectorSearch`). El `limit` interno se multiplica por 3 para compensar los descartados.
- Incluye warmup de Ollama (`warmup_ollama.py`).

### Módulo 4: Frontend Streamlit (`modules/modulo4-frontend/`)
**Estado:** Operativo

Estructura multi-página con navegación centralizada (`st.navigation()`). Tema visual en `.streamlit/config.toml` (paleta cálida de 7 niveles, no tech). Todos los textos visibles centralizados en `_texts.py`.

**Archivos clave:**

| Archivo | Rol |
|---|---|
| `app.py` | Router de navegación (`st.navigation()`). Llama a `set_page_config` y `_styles.apply()` una sola vez para todas las páginas. |
| `pages/0_Inicio.py` | Landing: título, subtítulo y las 3 tarjetas de acceso. |
| `pages/1_Asistente.py` | Chat conversacional (Módulo 3). |
| `pages/2_Buscador.py` | Buscador filtrado (Módulo 5). Paginación 20 en 20, botón limpiar filtros, tarjetas con badges de estado y colectivo. |
| `pages/3_Recursos.py` | Mapa de recursos (Módulo 6). |
| `buscador_tab.py` | Lógica de UI del buscador (importada por `pages/2_Buscador.py`). |
| `recursos_tab.py` | Lógica de UI del mapa (importada por `pages/3_Recursos.py`). |
| `_texts.py` | **Centralización de todos los strings visibles.** Editar aquí para cambiar cualquier texto sin tocar la lógica de páginas. Incluye los nombres de las pestañas de la barra lateral. |
| `_styles.py` | Inyección de CSS global: paleta de color, tarjetas con marcadores, contenedor scrollable del listado. |

**Interacción del mapa de recursos:**
- Clic en botón del listado → el mapa hace zoom (nivel 14) al recurso seleccionado y muestra su detalle.
- Clic en punto del mapa → muestra el detalle de ese punto. No reinicializa la vista.
- Ambas interacciones comparten el mismo estado (`rec_sel` en `session_state`): se sobreescriben mutuamente sin conflicto.

**Paleta de color** (`.streamlit/config.toml`):

| Variable | Color | Uso |
|---|---|---|
| `primaryColor` | `#ca9f7f` | Botones, links |
| `pageBackgroundColor` | `#EDD9C0` | Fondo de página |
| `secondaryBackgroundColor` | `#F5EAD8` | Sidebar, contenedor de lista |
| `containerBackgroundColor` | `#FBF4E8` | Tarjetas, panel de detalle |
| `listContainerBgColor` | `#FDFAF4` | Ítems del listado de recursos |
| `inputBackgroundColor` | `#FFFFFF` | Campos de texto |
| `textColor` | `#2C2416` | Texto principal |

### Módulo 5: Buscador filtrado (`modules/modulo5-buscador/`)
**Estado:** Operativo

- Consulta MongoDB con filtros estructurados basados en los campos booleanos de `beneficiaries`.
- Lógica OR para filtros de perfil: muestra convocatorias relevantes para cualquiera de los criterios seleccionados.
- Tarjetas con badge de estado coloreado (verde/amarillo/azul), organismo prominente, chips de colectivos coincidentes y referencia BDNS.
- Paginación de 20 resultados por página con botones Anterior/Siguiente.

---

## 🔧 Solución de problemas conocidos

### El asistente responde de forma genérica sin usar convocatorias

**Síntoma:** El asistente ignora la pregunta y responde con frases genéricas del tipo "no tengo información suficiente" o similar, sin mencionar ninguna convocatoria concreta.

**Causa más probable:** El índice de búsqueda vectorial `autoembed_index` ha desaparecido del cluster de MongoDB Atlas. Ocurre en clusters gratuitos por inactividad prolongada o cambios en el cluster. Los documentos y embeddings quedan intactos — solo falta el índice.

**Diagnóstico:**
```python
source venv/bin/activate
python -c "
from pymongo import MongoClient
from dotenv import load_dotenv
import os
load_dotenv('.env')
col = MongoClient(os.getenv('MONGO_URI'))['subvenia']['convocatorias']
print('Índices de búsqueda:', list(col.list_search_indexes()))
# Si devuelve [] → el índice ha desaparecido
"
```

**Solución** (no requiere la UI de Atlas, se ejecuta desde terminal):
```python
python -c "
from pymongo import MongoClient
from dotenv import load_dotenv
import os, time
load_dotenv('.env')
col = MongoClient(os.getenv('MONGO_URI'))['subvenia']['convocatorias']
col.create_search_index({
    'name': 'autoembed_index',
    'type': 'vectorSearch',
    'definition': {
        'fields': [{'type': 'vector', 'path': 'embedding', 'numDimensions': 768, 'similarity': 'cosine'}]
    }
})
print('Creando índice...')
while True:
    idx = list(col.list_search_indexes())
    if idx and idx[0]['status'] == 'READY':
        print('Índice READY — reinicia la app')
        break
    print('.', end='', flush=True)
    time.sleep(5)
"
```

---

### Módulo 6: Mapa de recursos sociales (`modules/modulo6-recursos/`)
**Estado:** Operativo

- Obtiene los datos de 17 categorías (~1.038 recursos) a través de la **API datastore de CKAN** (`opendata.vlci.valencia.es`), ya que el geoportal GeoJSON ha dejado de estar disponible.
- Convierte coordenadas UTM ETRS89/Zona 30N (EPSG:25830) a WGS84 con `pyproj`.
- Mapa interactivo con `pydeck` (`ScatterplotLayer`, radio en metros, tooltip al hover) con filtros por colectivo y búsqueda de texto.
- Datos bajo licencia CC BY 4.0. Caché de 1 hora para evitar peticiones repetidas.
- Cumple el requisito de uso de datos del portal `opendata.vlci.valencia.es` para los Premios de Datos Abiertos del Ayuntament de València 2026 (AD.TR.15).
