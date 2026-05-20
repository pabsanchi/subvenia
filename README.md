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
**Estado:** MVP Completado y Funcional + Modo Real Integrado ✅

**Capacidades Actuales:**
- **Modo Simulación MVP:** Extractor basado en Playwright y un parser HTML desacoplado resiliente que extrae 11 campos obligatorios inmutables en `data/ayudas.json`, respaldado por 15 tests unitarios.
- **Modo Real Integrado [NUEVO]:**
  - **Extracción Raw Incremental (`fetch_raw.py`):** Lógica que descarga de forma incremental convocatorias reales desde la API REST oficial de BDNS (mediante `bdns-fetch`), previniendo duplicados por ID de manera inteligente para actualizar `data/lista_convocatorias_raw.json`.
  - **Enriquecimiento Semántico con Gemini (`analyze_gemini.py`):** Descarga temporalmente los documentos PDF asociados a cada convocatoria, procesa su contenido semántico mediante `gemini-2.5-flash-lite` bajo un esquema estructurado estricto, y consolida los resultados en `data/convocatorias_full.json`.
  - **Resiliencia & Control de Flujo:** Registro de checkpoints (`data/seguimiento_procesos.json`) para reanudar el análisis desde donde se interrumpió, y parada inmediata ante errores de cuota agotada (429) o disponibilidad (503).
  - **Suite de Pruebas Reales (`test_real_scraper.py`):** Suite automatizada robusta con mocks avanzados para validar la persistencia, la ingesta incremental y el control/propagación de errores de API.

---

### 🟢 Módulo 2: Ingesta, Base de Datos y Visualización (`modules/modulo2-db/`)
**Estado:** MVP Completado y Funcional ✅
**Objetivo:** Consumir el archivo `ayudas.json` generado por el Módulo 1, crear embeddings text-to-vector para cada subvención y almacenarlos utilizando **Elasticsearch**. Se aprovecharán las capacidades nativas de búsqueda vectorial (kNN) de Elasticsearch para cubrir las necesidades del RAG, empleando además **Kibana** para construir los dashboards visuales de analítica.

**Capacidades Actuales:**
- **Infraestructura:** Elasticsearch y Kibana (v8.14.0) dockerizados y configurados localmente con seguridad nativa (`xpack.security`). Kibana es accesible en `http://localhost:5601`.
- **Ingesta Segura:** Script `ingest.py` que lee los datos generados por el scraper, establece conexión segura usando variables `.env` y emplea la API Bulk de Elasticsearch. **Integración verificada:** se ha ejecutado exitosamente contra el contenedor real, indexando 3 subvenciones.
- **Mapping y RAG Ready:** Índice `ayudas_sociales` configurado con mapeos de campos específicos (`keyword`, `text` con analyzer `spanish`, `date`) y, de forma crítica, un campo `embedding` (tipo `dense_vector`, 768 dims, similitud `cosine`) preparado para la futura generación real de embeddings. **Nota técnica:** se usa `1e-7` como mock, ya que la similitud `cosine` rechaza vectores de magnitud cero (`0.0`).
- **Testing Aislado e Integración:** Batería de pruebas unitarias (`test_db.py`) que mockea la conexión, y **pruebas de integración** (`test_integration.py`) que interactúan directamente con el contenedor real (haciendo un `SKIP` automático si Docker no está encendido). El cliente Python (`elasticsearch`) se ha fijado a la versión `8.14.x` para prevenir bloqueos de compatibilidad con el servidor.

⚠️ **Siguiente Paso Crítico (Post-MVP)**
Cuando el proyecto avance a la Fase 3 (RAG), los embeddings mock (ceros) deberán reemplazarse por vectores reales:
1. **Modelo de Embeddings:** Integrar un modelo de tipo sentence-transformers (ej. `all-MiniLM-L6-v2` o similar de 768 dims) para generar vectores semánticos de cada subvención.
2. **Actualización de Embeddings:** Utilizar el script `src/update_embeddings.py` que permite inyectar (vía API bulk update) los vectores reales generados, sin sobreescribir el resto de los metadatos.
3. **Dashboards Kibana:** Configurar visualizaciones en Kibana (accesible en `http://localhost:5601`) para explorar las subvenciones indexadas.

### 🟢 Módulo 3: Interfaz LLM y Retrieval (RAG)
**Estado:** MVP Completado y Funcional ✅
**Objetivo:** Motor de Retrieval-Augmented Generation (`rag_core.py`) que recibe una pregunta del usuario, la vectoriza usando `sentence-transformers`, busca en Elasticsearch el contexto de las ayudas más relevantes mediante similitud coseno (kNN), y usa un modelo de lenguaje local (Ollama - `llama3`) para formular una respuesta fundamentada ("grounded") exclusivamente en el contexto recuperado.

### 🟢 Módulo 4: Frontend (Streamlit)
**Estado:** MVP Completado y Funcional ✅
**Objetivo:** Interfaz gráfica final orientada al usuario desarrollada con Streamlit (`app.py`). Actúa como la capa visual que consume el motor RAG del Módulo 3, manteniendo el historial de la conversación (memoria de sesión) y proporcionando una experiencia conversacional interactiva (chat) donde el usuario puede exponer su situación y recibir asesoramiento respaldado por las convocatorias oficiales.
