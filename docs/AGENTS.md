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

## Roles Definidos

- **Agente Scraper (Módulo 1):** Encargado de la extracción de datos. Debe priorizar la resiliencia (uso de `try/except` en la extracción) y garantizar el contrato de datos estricto para evitar envenenar el RAG.
- **Agente DB (Módulo 2):** Responsable de la persistencia de datos. Debe levantar la base de datos usando contenedores.
- **Agente RAG / Backend (Próximos módulos):** Encargado de ingerir los datos en formato JSON, procesarlos y exponerlos. Debe asumir que los datos de entrada cumplen el contrato definido por el Scraper.

## Reglas Específicas: Fase 2 (Base de Datos)
- **Infraestructura:** La base de datos es Elasticsearch (v8.14.0) y debe levantarse localmente mediante `docker-compose`.
- **Seguridad:** Se debe usar `xpack.security.enabled=true` leyendo contraseñas de un `.env`, pero `xpack.security.http.ssl.enabled=false` para agilizar el MVP.
- **Mapping y Embeddings:** El script de ingesta (Python) debe crear el índice `ayudas_sociales` y mapear los campos extraídos del Módulo 1. Es obligatorio incluir un campo `embedding` de tipo `dense_vector` (768 dimensiones, similitud `cosine`) para preparar el futuro RAG. **Importante:** La similitud `cosine` rechaza vectores de magnitud cero, por lo que el mock de embeddings en la fase MVP debe usar valores mínimos no-cero (ej. `1e-7`).
- **Compatibilidad de Cliente:** Asegurar que la versión de la librería `elasticsearch` en Python está anclada (`pinned`) a la versión `8.14.x` para que coincida exactamente con la versión del servidor en Docker. Versiones mayores del cliente pueden causar cuelgues (hangs) debido a comprobaciones internas de compatibilidad de producto.

## Siguientes Pasos: Fase 3 y 4 (Frontend / Consumo del RAG)
El Motor RAG (Módulo 3) ya está construido en `modules/modulo3-rag/`, implementando la búsqueda vectorial contra Elasticsearch y la generación de respuestas mediante Ollama (modelo `llama3`). 

El próximo Agente deberá:
1. Diseñar e implementar una interfaz de usuario (UI) o API para que los usuarios finales interactúen con el RAG.
2. Afinar los *prompts* y ajustar el número de resultados (`top_k`) si es necesario para mejorar la calidad de las respuestas.
