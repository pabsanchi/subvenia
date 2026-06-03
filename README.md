# 🏛️ SubvenIA — Repositorio Principal

SubvenIA es un sistema basado en IA diseñado para ayudar a los ciudadanos de la Comunitat Valenciana a encontrar ayudas públicas, subvenciones y recursos sociales. Combina un motor RAG conversacional para usuarios con poca experiencia digital con un buscador filtrado avanzado y un mapa de recursos físicos.

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

## 🚀 Guía rápida de ejecución (paso a paso)

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
> Para detener: `./stop_frontEnd.sh`

---

## 🖥️ Modos de uso

SubvenIA ofrece tres modos de acceso desde la misma interfaz (tabs):

### 🤖 Modo 1 — Asistente conversacional (RAG)
**Para:** Usuarios con poca experiencia digital (personas mayores, etc.)  
**Cómo funciona:** El usuario describe su situación en lenguaje natural y recibe una respuesta personalizada. Sin necesidad de conocer categorías ni filtros.  
**Fuente de datos:** BDNS (vía MongoDB Atlas + Ollama/Llama3)

### 🔍 Modo 2 — Buscador filtrado
**Para:** Usuarios con conocimientos básicos de informática  
**Cómo funciona:** El usuario selecciona su perfil (situación laboral, familiar, colectivo, vulnerabilidad) y aplica filtros adicionales (tipo de ayuda, ámbito geográfico). Muestra las convocatorias de la BDNS que coinciden.  
**Fuente de datos:** BDNS (vía MongoDB Atlas, Módulo 5)

### 🗺️ Modo 3 — Mapa de recursos sociales
**Para:** Usuarios de cualquier perfil que necesiten saber dónde ir en persona  
**Cómo funciona:** Muestra un mapa interactivo y una lista de centros, asociaciones y servicios sociales del Ayuntamiento de Valencia, filtrable por colectivo. Complementa los otros dos modos.  
**Fuente de datos:** Portal de Datos Abiertos del Ayuntament de València (`opendata.vlci.valencia.es`), categoría Sociedad y Bienestar, licencia CC BY 4.0

---

## 📖 Documentación para agentes y desarrolladores

- **[docs/AGENTS.md](./docs/AGENTS.md):** Reglas de comportamiento, arquitectura y roles para agentes IA.
- **[docs/SKILLS.md](./docs/SKILLS.md):** Comandos de entorno virtual y testing.

---

## 📊 Estado del proyecto y módulos

### 🟢 Módulo 1: Scraper (`modules/modulo1-scraper/`)
**Estado:** Completado ✅

- Descarga convocatorias de la BDNS via API oficial (`bdns-fetch`).
- Usa `gemini-2.5-flash-lite` (`google-genai`) para extraer estructura semántica: beneficiarios (booleanos por colectivo), tipo de ayuda, estado, ámbito geográfico, fecha límite.
- El prompt de Gemini está en `src/prompt.txt` — editarlo directamente para ajustar la clasificación sin tocar código Python.
- El prompt incluye definiciones detalladas por categoría para evitar errores frecuentes (ej: `personas_mayores` solo aplica a tercera edad, no a "mayores de X años" genérico) y fuerza clasificación multi-etiqueta.
- Vectoriza con `intfloat/multilingual-e5-base` (768 dimensiones).
- **Los campos `status`, `aid_type`, `frequency` y `granting_body_level` se guardan desde esta versión** para habilitar el buscador filtrado (Módulo 5).

### 🟢 Módulo 2: Ingesta en base de datos (`modules/modulo2-db/`)
**Estado:** Migrado a MongoDB Atlas ✅

- Upsert masivo a MongoDB Atlas con el `id` de la convocatoria como `_id`.
- Búsqueda semántica via índice `autoembed_index` (Atlas Vector Search).
- `backfill_gemini_fields.py` — script de retroalimentación para documentos procesados antes de la corrección de `analyze_gemini.py`. Deriva `status` (desde `deadline` con dateparser), `aid_type` (keyword matching en `descripcion`) y `granting_body_level` (desde `nivel1` BDNS) sin necesidad de re-procesar los PDFs. Idempotente: solo actualiza campos ausentes. Admite `--dry-run`.

### 🟢 Módulo 3: Motor RAG (`modules/modulo3-rag/`)
**Estado:** Operativo ✅

- Convierte la pregunta del usuario en vector → `$vectorSearch` en MongoDB (umbral 0.85) → contexto estructurado → Ollama Llama 3 → respuesta en lenguaje natural.
- Incluye warmup de Ollama (`warmup_ollama.py`).

### 🟢 Módulo 4: Frontend Streamlit (`modules/modulo4-frontend/`)
**Estado:** Actualizado con 3 tabs ✅

- **Tab 1:** Chat RAG conversacional (Módulo 3).
- **Tab 2:** Buscador filtrado (Módulo 5) — acceso directo a los datos de MongoDB con filtros por perfil.
- **Tab 3:** Mapa de recursos sociales (Módulo 6) — datos del portal opendata.vlci.valencia.es.

### 🟢 Módulo 5: Buscador filtrado (`modules/modulo5-buscador/`)
**Estado:** Nuevo ✅

- Consulta MongoDB con filtros estructurados basados en los campos booleanos de `beneficiaries`.
- Lógica OR para filtros de perfil: muestra convocatorias relevantes para cualquiera de los criterios seleccionados.
- Muestra tarjetas con estado (derivado de `deadline` si `status` no está disponible), organismo, condiciones adicionales y referencia BDNS.

### 🟢 Módulo 6: Mapa de recursos sociales (`modules/modulo6-recursos/`)
**Estado:** Nuevo ✅

- Descarga datasets GeoJSON de la categoría «Sociedad y Bienestar» del portal de datos abiertos del Ayuntament de València.
- Muestra centros y asociaciones sociales en un mapa interactivo con filtros por colectivo y búsqueda de texto.
- Datos bajo licencia CC BY 4.0. Caché de 1 hora para evitar peticiones repetidas.
- Cumple el requisito de uso de datos del portal `opendata.vlci.valencia.es` para los Premios de Datos Abiertos del Ayuntament de València 2026 (AD.TR.15).
