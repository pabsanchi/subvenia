# 🏛️ SubvenIA - Repositorio Principal

SubvenIA es un sistema basado en RAG (Retrieval-Augmented Generation) diseñado para la extracción, indexación y consulta de ayudas públicas y subvenciones (con foco inicial en la Comunidad Valenciana).

Este proyecto sigue una arquitectura **Monorepo** y se desarrolla bajo un enfoque iterativo **MVP** (Minimum Viable Product).

---

## 📖 Documentación para Agentes y Desarrolladores

La documentación core del proyecto está organizada en la carpeta `docs/` para no ensuciar la raíz del proyecto. **Es de obligada lectura para retomar el trabajo:**

- **[docs/AGENTS.md](./docs/AGENTS.md):** Reglas estrictas de comportamiento, arquitectura y roles para los agentes IA que programen en este repositorio.
- **[docs/SKILLS.md](./docs/SKILLS.md):** Comandos esenciales para entornos virtuales, resolución de dependencias de Playwright en Ubuntu y comandos de testing.

---

## 📊 Estado del Proyecto y Módulos

### 🟢 Módulo 1: Scraper (`modules/modulo1-scraper/`)
**Estado:** MVP Completado + Modo Real + Vectorización Atómica ✅

**Capacidades Actuales:**
- **Modo Simulación MVP:** Extractor basado en Playwright y un parser HTML desacoplado resiliente que extrae 11 campos obligatorios inmutables en `data/ayudas.json`, respaldado por 15 tests unitarios.
- **Modo Real Integrado:**
  - **Extracción Raw Incremental (`fetch_raw.py`):** Lógica que descarga de forma incremental convocatorias reales desde la API REST oficial de BDNS (mediante `bdns-fetch`), previniendo duplicados por ID de manera inteligente para actualizar `data/lista_convocatorias_raw.json`.
  - **Enriquecimiento Semántico con Gemini (`analyze_gemini.py`):** Descarga temporalmente los documentos PDF asociados a cada convocatoria, procesa su contenido semántico mediante `gemini-2.5-flash-lite` bajo un esquema estructurado estricto, y consolida los resultados en `data/convocatorias_full.json`.
  - **Vectorización Atómica Local (`vectorizer.py`) [NUEVO]:** Genera de forma local embeddings de 768 dimensiones para cada convocatoria enriquecida usando el modelo `intfloat/multilingual-e5-base`. Los vectores se inyectan de forma atómica en el mismo flujo de guardado, garantizando que ninguna convocatoria se almacene sin su vector.
  - **Resiliencia & Control de Flujo:** Registro de checkpoints (`data/seguimiento_procesos.json`) para reanudar el análisis desde donde se interrumpió, y parada inmediata ante errores de cuota agotada (429) o disponibilidad (503).
  - **Suite de Pruebas Reales (`test_real_scraper.py`):** Suite automatizada robusta con mocks avanzados para validar la persistencia, la ingesta incremental, la compilación de texto para vectorización, y el control/propagación de errores de API.

---

### 🟢 Módulo 2: Ingesta, Base de Datos y Visualización (`modules/modulo2-db/`)
**Estado:** Actualizado con Ingesta Directa de Vectores Reales ✅
**Objetivo:** Consumir las convocatorias enriquecidas y ya vectorizadas del Módulo 1, crear el índice `ayudas_sociales_full` en Elasticsearch con un mapping adaptado al esquema completo (objetos anidados `geographic_scope`, `beneficiaries`), y almacenar los embeddings pre-calculados para la búsqueda kNN nativa.

**Capacidades Actuales:**
- **Infraestructura:** Elasticsearch y Kibana (v8.14.0) dockerizados y configurados localmente con seguridad nativa (`xpack.security`). Kibana es accesible en `http://localhost:5601`.
- **Ingesta Directa con Vectores Reales:** Script `ingest.py` que lee `data/convocatorias_full.json` (ya con embeddings de 768 dims), valida que cada documento contiene su vector, crea el índice `ayudas_sociales_full` con mapping estricto, e indexa todo usando la API Bulk. **Ya no se usan vectores mock de ceros.**
- **Mapping Enriquecido:** El índice `ayudas_sociales_full` mapea campos `keyword` (organismos, ámbito geográfico, colectivos), campos `text` con analyzer `spanish` (descripciones y condiciones), campos `boolean` e `integer` (requisitos de residencia, rango de edad), y el vector `dense_vector` de 768 dimensiones con similitud `cosine` indexado para kNN.
- **Testing Aislado e Integración:** Batería de pruebas unitarias (`test_db.py`) que mockea la conexión, y **pruebas de integración** (`test_integration.py`) que interactúan directamente con el contenedor real (haciendo un `SKIP` automático si Docker no está encendido).

---

### 🟢 Módulo 3: Interfaz LLM y Retrieval (RAG) (`modules/modulo3-rag/`)
**Estado:** Actualizado con Búsqueda Semántica en `ayudas_sociales_full` ✅
**Objetivo:** Motor de Retrieval-Augmented Generation (`rag_core.py`) que recibe una pregunta del usuario, la vectoriza usando `sentence-transformers` (con prefijo asimétrico `query: `), busca en el índice `ayudas_sociales_full` de Elasticsearch el contexto más relevante mediante búsqueda kNN nativa, genera dinámicamente las URLs oficiales de la BDNS, y usa un modelo de lenguaje local (Ollama - `llama3`) para formular una respuesta fundamentada ("grounded") exclusivamente en el contexto recuperado.

**Capacidades Actuales:**
- **Búsqueda Semántica kNN:** Consulta directa al índice `ayudas_sociales_full` con vectores de consulta generados localmente.
- **Generación Dinámica de URLs:** Reconstruye el enlace oficial directo de cada convocatoria en el portal de transparencia de la BDNS: `https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/{numeroConvocatoria}`.
- **Contexto Estructurado para el LLM:** Inyecta al modelo información precisa sobre colectivos destinatarios, situación laboral, requisitos de residencia, ámbito geográfico y condiciones adicionales.

---

### 🟢 Módulo 4: Frontend (Streamlit)
**Estado:** MVP Completado y Funcional ✅
**Objetivo:** Interfaz gráfica final orientada al usuario desarrollada con Streamlit (`app.py`). Actúa como la capa visual que consume el motor RAG del Módulo 3, manteniendo el historial de la conversación (memoria de sesión) y proporcionando una experiencia conversacional interactiva (chat) donde el usuario puede exponer su situación y recibir asesoramiento respaldado por las convocatorias oficiales.
