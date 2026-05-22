# 🏛️ SubvenIA - Repositorio Principal

SubvenIA es un sistema basado en RAG (Retrieval-Augmented Generation) diseñado para la extracción, indexación y consulta de ayudas públicas y subvenciones (con foco inicial en la Comunidad Valenciana).

Este proyecto sigue una arquitectura **Monorepo** y ha migrado su capa de datos a **MongoDB Atlas**.

---

## Guía de instalación: 

Si es la primera vez que descargas el repositorio, simplemente ejecuta el instalador automatizado. Este script preparará el entorno virtual, instalará todas las dependencias cruzadas y creará un archivo `.env` de plantilla:
```bash
./install.sh
```
> [!IMPORTANT]
> **Configuración Obligatoria:** Abre el archivo `.env` generado en la raíz y configura tus credenciales (`GEMINI_API_KEY` y `MONGO_URI`). Si la base de datos de MongoDB no tiene datos (no haces los Pasos 1, 2 y 3), el asistente virtual no podrá responder.


## 🚀 Guía Rápida de Ejecución (Paso a Paso)

Para arrancar el proyecto completo desde cero y actualizar las convocatorias, sigue estos pasos en orden:

### Paso 0: Entorno

simplemente activa el entorno:
```bash
source venv/bin/activate
```

### Paso 1: Recogida de Convocatorias (Scraper)
Este script se conecta a la API oficial de la BDNS para descargar nuevas convocatorias de forma incremental (sin duplicados).
```bash
python modules/modulo1-scraper/src/fetch_raw.py
```

### Paso 2: Análisis Semántico y Vectorización (Gemini)
Este script toma las convocatorias descargadas, baja sus PDFs oficiales, los procesa con **Gemini** (usando el nuevo SDK `google-genai`) para estructurar sus requisitos (forzando etiquetas de booleanos) y genera localmente el vector semántico (768 dimensiones).
```bash
python modules/modulo1-scraper/src/analyze_gemini.py
```

### Paso 3: Subida a la Base de Datos (MongoDB Atlas)
Una vez extraídos los datos y generados los vectores, este script los sube de forma masiva a tu clúster de MongoDB Atlas.
```bash
python modules/modulo2-db/src/ingest.py
```
*(Nota: Requiere que tengas configurado el `MONGO_URI` en tu archivo `.env` y el índice vectorial `$vectorSearch` creado en Atlas).*

### Paso 4: Levantar la Aplicación (Ollama + Frontend)
Hemos creado un script que automáticamente "despierta" (warmup) el modelo local en Ollama y luego levanta la interfaz gráfica de Streamlit para que puedas chatear.
```bash
./start_app.sh
```

> [!TIP]
> **Para detener la aplicación:** Cuando termines de usarla, puedes ejecutar `./stop_app.sh` para matar el proceso de Streamlit y detener el servicio local de Ollama, liberando así los recursos de tu ordenador.

---

## 📖 Documentación para Agentes y Desarrolladores

La documentación core del proyecto está organizada en la carpeta `docs/` para no ensuciar la raíz del proyecto. **Es de obligada lectura para retomar el trabajo:**

- **[docs/AGENTS.md](./docs/AGENTS.md):** Reglas estrictas de comportamiento, arquitectura y roles para los agentes IA que programen en este repositorio.
- **[docs/SKILLS.md](./docs/SKILLS.md):** Comandos esenciales para entornos virtuales y comandos de testing.

---

## 📊 Estado del Proyecto y Módulos

### 🟢 Módulo 1: Scraper (`modules/modulo1-scraper/`)
**Estado:** Completado + Extracción Estructurada con Gemini ✅
- Se encarga de descargar las convocatorias desde la BDNS.
- Emplea `gemini-2.5-flash-lite` (a través del SDK oficial `google-genai`) para extraer los datos obligando a un modelo estricto de diccionarios de booleanos (colectivos, situación laboral, vulnerabilidad).
- Vectoriza los textos generados utilizando `intfloat/multilingual-e5-base`.

### 🟢 Módulo 2: Ingesta en Base de Datos (`modules/modulo2-db/`)
**Estado:** Migrado a MongoDB Atlas ✅
- Se conecta a la nube mediante `pymongo`.
- Vuelca el JSON enriquecido completo utilizando la estructura dinámica de Mongo y el `_id` oficial de la convocatoria.
- La búsqueda semántica depende de la creación manual del **Atlas Vector Search Index** en la plataforma.

### 🟢 Módulo 3: Interfaz LLM y Retrieval (RAG) (`modules/modulo3-rag/`)
**Estado:** Actualizado con `$vectorSearch` de MongoDB ✅
- Convierte la pregunta del usuario en un vector.
- Utiliza la etapa de agregación `$vectorSearch` nativa de MongoDB Atlas para encontrar las ayudas más similares.
- Pasa el contexto altamente estructurado al LLM local (Ollama - Llama 3) para generar la respuesta en lenguaje natural.
- Incluye script de calentamiento (`warmup_ollama.py`) para evitar tiempos de espera largos en la primera consulta.

### 🟢 Módulo 4: Frontend (Streamlit)
**Estado:** MVP Completado y Funcional ✅
- Interfaz gráfica (chat) que consume el motor RAG del Módulo 3 y mantiene el historial conversacional.
