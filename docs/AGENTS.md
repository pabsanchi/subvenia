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
- **Agente RAG / Backend (Próximos módulos):** Encargado de ingerir los datos en formato JSON, procesarlos y exponerlos. Debe asumir que los datos de entrada cumplen el contrato definido por el Scraper.
