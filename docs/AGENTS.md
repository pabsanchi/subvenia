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
modulo4-frontend/  → Interfaz Streamlit multi-página con st.navigation()
modulo5-buscador/  → Lógica de consulta filtrada a MongoDB
modulo6-recursos/  → Cliente CKAN datastore del portal opendata.vlci.valencia.es (17 datasets, ~1.038 recursos)
```

### Estructura del frontend (modulo4)

```
src/
  app.py              ← router: st.navigation() + set_page_config + _styles.apply()
  _texts.py           ← todos los strings visibles de la UI (editar aquí para cambiar texto)
  _styles.py          ← CSS global inyectado vía st.markdown()
  buscador_tab.py     ← lógica + UI del buscador (sin set_page_config)
  recursos_tab.py     ← lógica + UI del mapa de recursos (sin set_page_config)
  pages/
    0_Inicio.py       ← landing: título + 3 tarjetas de acceso
    1_Asistente.py    ← chat conversacional (Módulo 3)
    2_Buscador.py     ← importa buscador_tab.render()
    3_Recursos.py     ← importa recursos_tab.render()
```

### Dependencias entre módulos (frontend)

`app.py` define la navegación y ejecuta la página seleccionada:
- `pages/1_Asistente.py` importa `rag_core.py` de modulo3 vía `sys.path`
- `pages/2_Buscador.py` importa `buscador_tab.py`, que importa `buscador_client.py` de modulo5
- `pages/3_Recursos.py` importa `recursos_tab.py`, que importa `recursos_client.py` de modulo6
- Todas las páginas importan `_texts.py` para los strings visibles

## Roles Definidos

- **Agente Scraper (Módulo 1):** Extracción de datos. Prioriza resiliencia (`try/except`) y garantiza el contrato de datos estricto. **Debe guardar todos los campos de la extracción Gemini** (`status`, `aid_type`, `frequency`, `granting_body_level`, además de `beneficiaries`, `deadline`, `geographic_scope`).
- **Agente DB (Módulo 2):** Persistencia de datos. Upsert idempotente en MongoDB Atlas.
- **Agente RAG (Módulo 3):** Motor de recuperación semántica y generación de respuestas con Ollama.
- **Agente Buscador (Módulo 5):** Consultas filtradas a MongoDB con lógica OR para perfil de usuario. Sin lógica de UI.
- **Agente Recursos (Módulo 6):** Obtiene datos de 17 categorías de recursos sociales a través de la API datastore de CKAN (`opendata.vlci.valencia.es`). Convierte coordenadas UTM (EPSG:25830) a WGS84 con `pyproj`. Sin lógica de UI.
- **Agente Frontend (Módulo 4):** Interfaz Streamlit multi-página. `app.py` es el router de navegación (`st.navigation()`); la landing está en `pages/0_Inicio.py`. Orquesta los módulos 3, 5 y 6. No contiene lógica de negocio propia. Reglas críticas:
  - **Todo string visible debe provenir de `_texts.py`.** No hardcodear texto en archivos de página.
  - **No llamar `st.set_page_config()` ni `_styles.apply()` en páginas individuales** — se llaman una sola vez en `app.py`.
  - Los nombres de las pestañas de la barra lateral se configuran en `_texts.py` → sección `"nav"` → consumidos por `st.navigation()` en `app.py`.
  - La paleta de color se define en `.streamlit/config.toml` con variables propias (`pageBackgroundColor`, `containerBackgroundColor`, `listContainerBgColor`); `_styles.py` las lee con `tomllib` y las aplica vía CSS inyectado.

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

- **Fuente:** API datastore de CKAN — `https://opendata.vlci.valencia.es/api/3/action/datastore_search`. El geoportal GeoJSON (`geoportal.valencia.es/apps/OpenData/`) ha dejado de servir los ficheros (404).
- **Datasets:** 17 categorías mapeadas en `DATASETS` de `recursos_client.py` como `{categoria: resource_id}`. Los resource IDs son estables; si un dataset falla se omite sin interrumpir los demás.
- **Coordenadas:** los datos originales vienen en UTM ETRS89/Zona 30N (EPSG:25830, campos `X`/`Y`). Se convierten a WGS84 con `pyproj.Transformer`. El transformer `_UTM_TO_WGS84` se instancia a nivel de módulo para reutilizarlo.
- **Caché:** `@st.cache_data(ttl=3600)` — los datos se recargan cada hora.
- **Licencia:** CC BY 4.0 — siempre mostrar atribución en la UI.

## Siguientes Pasos Recomendados

- **Mejorar la calidad de clasificación Gemini:** Refinar el prompt para reducir falsos negativos en los campos booleanos de beneficiarios (muchas convocatorias con lenguaje legal genérico no se etiquetan correctamente).
- **Añadir filtros avanzados en el buscador:** por rango de edad (`age_min`/`age_max`), por umbral de ingresos (`income_threshold`), por compatibilidad con otras ayudas.
- **Añadir filtros avanzados en el mapa:** filtrar por titularidad pública/privada, búsqueda por dirección o barrio.
- **Escalabilidad del scraper:** Ejecución periódica automatizada del pipeline completo (cron o GitHub Actions).
