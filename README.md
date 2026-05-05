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
**Estado:** MVP Completado y Funcional ✅

**Capacidades Actuales:**
- **Infraestructura lista:** Orquestador basado en Playwright (Python) capaz de levantar un navegador Chromium real en modo headless.
- **Extracción Resiliente:** Parser HTML desacoplado que usa bloques `try/except` individuales para no detener la ejecución si falta un campo.
- **Contrato de Datos Estricto:** Garantiza la generación de un JSON (`data/ayudas.json`) con 11 campos inmutables obligatorios.
- **Testing Robusto:** 15 pruebas unitarias automatizadas (`pytest`) que mockean el navegador.
- **Modo Simulación (Mock):** Actualmente con `use_mock=True` para inyectar HTML de ejemplo simulando la BDNS.

⚠️ **Siguiente Paso Crítico (Post-MVP)**
Cuando el proyecto necesite salir de la fase de simulación para recopilar datos reales, **EL PRIMER PASO ABSOLUTO** para el Módulo 1 será:
1. **Análisis del DOM Real:** Navegar manualmente o con herramientas de dev a las páginas reales de ayudas (ej. portal de la Generalitat o BDNS).
2. **Ajuste de Selectores:** Asegurarse de que el scraper sea capaz de extraer la información buscada modificando las constantes de `HTMLParser.SELECTOR_MAP` y `HTMLParser.ITEM_SELECTOR` (`src/scraper.py`) para que hagan "match" exacto con las tablas/etiquetas de la página oficial.
3. Cambiar `use_mock=False` e implementar lógica de paginación si hubiera múltiples hojas de resultados.

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
2. **Re-indexación:** Actualizar el script de ingesta para generar los embeddings reales a partir de los campos `title` + `description`, y re-indexar los documentos.
3. **Dashboards Kibana:** Configurar visualizaciones en Kibana (accesible en `http://localhost:5601`) para explorar las subvenciones indexadas.

### ⚪ Módulo 3: Interfaz LLM y Retrieval (RAG)
**Estado:** Pendiente ⏳
**Objetivo:** Interfaz conversacional/backend que recibe la pregunta del usuario, busca en Elasticsearch el contexto de las ayudas más relevantes (búsqueda híbrida/vectorial) y usa un LLM para formular una respuesta fundamentada ("grounded") en la convocatoria real.
