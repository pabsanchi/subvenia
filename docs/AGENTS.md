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
- **Índice Principal:** El índice de producción actual es `ayudas_sociales_full`, que contiene convocatorias reales enriquecidas con Gemini y vectorizadas con `intfloat/multilingual-e5-base`. El antiguo índice `ayudas_sociales` (datos de simulación) se mantiene como referencia pero ya no es consultado por el RAG.
- **Mapping Enriquecido:** El mapping incluye objetos anidados (`geographic_scope`, `beneficiaries`) con campos `keyword` para filtros, campos `text` con analyzer `spanish` para búsquedas full-text, y un campo `embedding` de tipo `dense_vector` (768 dimensiones, similitud `cosine`, indexado para kNN) que contiene vectores reales pre-calculados por el Módulo 1.
- **Compatibilidad de Cliente:** Asegurar que la versión de la librería `elasticsearch` en Python está anclada (`pinned`) a la versión `8.14.x` para que coincida exactamente con la versión del servidor en Docker. Versiones mayores del cliente pueden causar cuelgues (hangs) debido a comprobaciones internas de compatibilidad de producto.

## Siguientes Pasos
El **MVP está completado (Fases 1 a 4)** y la integración de vectorización atómica con ingesta directa ha sido implementada exitosamente. Todos los módulos operativos (Scraper + Vectorizador, DB con `ayudas_sociales_full`, RAG Core con búsqueda kNN y URLs dinámicas de la BDNS, y Frontend) están funcionando de extremo a extremo.

Futuros Agentes podrán centrarse en:
- Escalabilidad y recolección masiva de datos (ejecución periódica del scraper real).
- Mejoras del prompt del RAG y ajuste de la calidad de respuesta.
- Filtros avanzados en RAG (por ámbito geográfico, colectivo destinatario, rango de edad, etc.).
- Autenticación o despliegue en la nube.
