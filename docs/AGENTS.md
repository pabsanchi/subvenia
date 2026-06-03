# 🤖 Guía para Agentes IA (AGENTS.md)

Este documento define las reglas estrictas de comportamiento y desarrollo para cualquier Agente IA que opere en el proyecto **SubvenIA**.

## Reglas Globales

1. **Monorepo y Aislamiento:** Todo el trabajo de un módulo debe ocurrir de forma contenida dentro de su respectivo directorio en `modules/`. Un agente trabajando en el Módulo 1 no debe alterar archivos del Módulo 2 sin una razón justificada explícitamente por el usuario.
2. **Enfoque MVP (Minimum Viable Product):**
   - Programa solo lo estrictamente necesario.
   - Usa mocks locales antes de integraciones reales (ej. no usar APIs reales o bases de datos si un JSON mock es suficiente para probar la lógica).
   - El objetivo es validar el pipeline y la arquitectura antes de la implementación final.
3. **Inmutabilidad del Contexto:** Si se modifica un archivo existente, NO se deben borrar ni editar los comentarios originales, docstrings o explicaciones que dejó un agente anterior, a menos que el código cambie drásticamente y el comentario quede obsoleto.
4. **Testing Obligatorio:** Ningún código se da por válido o "terminado" si no incluye tests automatizados (ej. `pytest`) que validen la lógica de negocio y los contratos de datos.
5. **Documentación Obligatoria:** Cualquier cambio significativo debe actualizarse en `README.md` y en este archivo (`AGENTS.md`). Dejar constancia de qué cambió, en qué módulo y por qué.

## Arquitectura de Módulos

```
modulo1-scraper/   → Scraper BDNS + análisis Gemini + vectorización
modulo2-db/        → Ingesta y upsert en MongoDB Atlas
modulo3-rag/       → Motor RAG (embeddings + vectorSearch + Ollama)
modulo4-frontend/  → Interfaz Streamlit (3 tabs: RAG, Buscador, Mapa)
modulo5-buscador/  → Lógica de consulta filtrada a MongoDB
modulo6-recursos/  → Cliente GeoJSON del portal opendata.vlci.valencia.es
```

### Dependencias entre módulos (frontend)

`app.py` (modulo4) importa:
- `rag_core.py` de modulo3 vía `sys.path`
- `buscador_tab.py` de modulo4 (que a su vez importa modulo5)
- `recursos_tab.py` de modulo4 (que a su vez importa modulo6)

## Roles Definidos

- **Agente Scraper (Módulo 1):** Extracción de datos. Prioriza resiliencia (`try/except`) y garantiza el contrato de datos estricto. **Debe guardar todos los campos de la extracción Gemini** (`status`, `aid_type`, `frequency`, `granting_body_level`, además de `beneficiaries`, `deadline`, `geographic_scope`).
- **Agente DB (Módulo 2):** Persistencia de datos. Upsert idempotente en MongoDB Atlas.
- **Agente RAG (Módulo 3):** Motor de recuperación semántica y generación de respuestas con Ollama.
- **Agente Buscador (Módulo 5):** Consultas filtradas a MongoDB con lógica OR para perfil de usuario. Sin lógica de UI.
- **Agente Recursos (Módulo 6):** Descarga y unificación de GeoJSON del portal opendata.vlci.valencia.es. Sin lógica de UI.
- **Agente Frontend (Módulo 4):** Interfaz Streamlit. Orquesta los módulos 3, 5 y 6. No contiene lógica de negocio propia.

## Reglas Específicas: Base de Datos (MongoDB Atlas)

- **Conexión:** `MONGO_URI` en `.env` (raíz del proyecto). Cargar siempre con `load_dotenv`.
- **Base de datos:** `subvenia`
- **Colección principal:** `convocatorias`
- **ID de documento:** campo `id` de la convocatoria BDNS se usa como `_id` de Mongo.
- **Índice vectorial:** `autoembed_index` sobre el campo `embedding` (768 dimensiones, similitud coseno). Creación manual en Atlas Vector Search.
- **Campo de trazabilidad:** `rag_retrieval_count` — se incrementa cada vez que el RAG recupera un documento.

## Reglas Específicas: Módulo 5 (Buscador)

- **Lógica de filtrado:** OR dentro del perfil del usuario, AND para filtros adicionales (`aid_type`, `geographic_scope.level`).
- **Campo `status`:** Si no existe en el documento (documentos procesados antes del fix de `guardar_convocatoria_full`), se deriva de `deadline` comparando con la fecha de hoy.
- **Campo `aid_type`:** Solo disponible en documentos procesados con la versión corregida de `analyze_gemini.py`. Los documentos más antiguos mostrarán "Ayuda" como tipo genérico.
- **Búsqueda de texto:** Usa `$regex` sobre `descripcion` (no requiere índice de texto).

## Reglas Específicas: Módulo 6 (Recursos)

- **Fuente:** `https://geoportal.valencia.es/apps/OpenData/SociedadBienestar/SS_*.json`
- **Datasets:** Definidos en `DATASETS` de `recursos_client.py`. Los URLs no confirmados se intentan y se omiten silenciosamente si fallan.
- **Caché:** `@st.cache_data(ttl=3600)` — los datos se recargan cada hora.
- **Licencia:** CC BY 4.0 — siempre mostrar atribución en la UI.

## Siguientes Pasos Recomendados

- **Retroalimentar documentos existentes en MongoDB** con `status` y `aid_type`: requiere un script de migración que re-procese los PDFs con Gemini (costoso en cuota de API) o que intente derivar estos campos de los datos BDNS disponibles.
- **Mejorar la calidad de clasificación Gemini:** Refinar el prompt para reducir falsos negativos en los campos booleanos de beneficiarios (muchas convocatorias con lenguaje legal genérico no se etiquetan correctamente).
- **Añadir filtros avanzados en el buscador:** por rango de edad (`age_min`/`age_max`), por umbral de ingresos (`income_threshold`), por compatibilidad con otras ayudas.
- **Tests para Módulos 5 y 6:** Añadir `tests/` en cada módulo nuevo siguiendo el patrón existente.
- **Escalabilidad del scraper:** Ejecución periódica automatizada del pipeline completo (cron o GitHub Actions).
