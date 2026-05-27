import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuraciones Base
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
# Ahora el .env está en la raíz del proyecto
ENV_PATH = BASE_DIR.parent.parent / ".env"
DB_NAME = "subvenia"
COLLECTION_NAME = "convocatorias"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "intfloat/multilingual-e5-base"

# Umbral mínimo de similitud para considerar un documento relevante.
# Elasticsearch devuelve scores coseno normalizados entre 0 y 1.
# 0.75 es un buen equilibrio: captura resultados genuinamente relevantes
# sin devolver ruido. Ajustar según la experiencia del usuario.
MIN_SIMILARITY_SCORE = 0.85

# URL del buscador general de la BDNS (el portal no soporta deep links directos)
BDNS_SEARCH_URL = "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatorias"


class RAGCore:
    def __init__(self):
        """Inicializa los clientes de Elasticsearch y el modelo de embeddings."""
        # 1. Cargar Variables de Entorno
        if not ENV_PATH.exists():
            logger.warning(f"No se encontró el archivo .env en {ENV_PATH}. Intentando variables del sistema.")
        load_dotenv(ENV_PATH)
        
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI no encontrada en el entorno.")

        # 2. Conectar a MongoDB
        self.client = MongoClient(mongo_uri)
        try:
            self.client.admin.command('ping')
            logger.info("Conexión a MongoDB Atlas exitosa.")
        except Exception as e:
            logger.error(f"No se pudo conectar a MongoDB: {e}")

        # 3. Cargar Modelo de Embeddings
        logger.info(f"Cargando modelo de embeddings: {MODEL_NAME}...")
        self.encoder = SentenceTransformer(MODEL_NAME)
        logger.info("Modelo de embeddings cargado correctamente.")

    def buscar_ayudas(self, pregunta: str, max_results: int = 1, min_score: float = MIN_SIMILARITY_SCORE) -> List[Dict[str, Any]]:
        """
        Convierte la pregunta a vector y busca en Elasticsearch mediante kNN.
        Devuelve TODOS los documentos cuya similitud coseno supere el umbral min_score,
        en lugar de un número fijo (top_k).
        
        Args:
            pregunta: Texto de la consulta del usuario.
            max_results: Número máximo de candidatos a evaluar (límite de seguridad).
            min_score: Umbral mínimo de similitud (0.0-1.0). Solo se devuelven docs por encima.
        """
        logger.info(f"Buscando contexto para la pregunta: '{pregunta}' (umbral de similitud: {min_score})")
        
        # El modelo multilingual-e5 recomienda prefijar las queries con "query: "
        texto_query = f"query: {pregunta}"
        vector_query = self.encoder.encode(texto_query).tolist()

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "autoembed_index",
                    "path": "embedding",
                    "queryVector": vector_query,
                    "numCandidates": 100,
                    "limit": max_results
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "descripcion": 1,
                    "descripcionLeng": 1,
                    "geographic_scope": 1,
                    "beneficiaries": 1,
                    "numeroConvocatoria": 1,
                    "deadline": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        db = self.client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        resultados = []
        ids_recuperados = []
        try:
            cursor = collection.aggregate(pipeline)
            for doc in cursor:
                score = doc.get("score", 0)
                # Filtrar por umbral de similitud
                if score < min_score:
                    logger.debug(f"Documento descartado por baja similitud ({score:.4f} < {min_score})")
                    continue
                    
                doc["_score"] = score
                
                n_conv = doc.get("numeroConvocatoria")
                if n_conv:
                    doc["referencia_busqueda"] = f"Convocatoria BDNS nº {n_conv}"
                    doc["portal_url"] = BDNS_SEARCH_URL
                else:
                    doc["referencia_busqueda"] = "Número de convocatoria no disponible"
                    doc["portal_url"] = BDNS_SEARCH_URL
                    
                resultados.append(doc)
                if "_id" in doc:
                    ids_recuperados.append(doc["_id"])
                    
            if ids_recuperados:
                try:
                    collection.update_many(
                        {"_id": {"$in": ids_recuperados}},
                        {"$inc": {"rag_retrieval_count": 1}}
                    )
                    logger.debug(f"Se incrementó rag_retrieval_count para {len(ids_recuperados)} documentos.")
                except Exception as e:
                    logger.error(f"Error actualizando el contador RAG: {e}")
                    
        except Exception as e:
            logger.error(f"Error durante $vectorSearch: {e}")

        logger.info(f"Se han recuperado {len(resultados)} documentos por encima del umbral de similitud ({min_score}).")
        if not resultados:
            logger.warning("Ningún documento superó el umbral de similitud. Considera bajar MIN_SIMILARITY_SCORE.")
        return resultados

    def generar_respuesta(self, pregunta: str, contexto_docs: List[Dict[str, Any]]) -> str:
        """
        Genera una respuesta usando Ollama basada estrictamente en el contexto.
        """
        logger.info("Generando respuesta con Ollama...")

        # Construimos el texto del contexto a partir de los campos estructurados
        contexto_texto = ""
        for i, doc in enumerate(contexto_docs, 1):
            contexto_texto += f"\n--- Convocatoria {i} de {len(contexto_docs)} ---\n"
            contexto_texto += f"Título: {doc.get('descripcion', 'N/A')}\n"
            
            # Formatear la descripción alternativa o regional si está disponible
            desc_leng = doc.get('descripcionLeng')
            if desc_leng:
                contexto_texto += f"Descripción Lengua Cooficial: {desc_leng}\n"

            # Plazo de solicitud
            deadline = doc.get('deadline')
            if deadline:
                contexto_texto += f"Plazo de solicitud: {deadline}\n"
                
            # Formatear beneficiarios estructurados para dar la máxima precisión al LLM
            benef = doc.get('beneficiaries', {})
            benef_str = "N/A"
            if isinstance(benef, dict):
                b_parts = []
                fam = benef.get("situacion_familiar", {})
                fam_labels = [k for k, v in fam.items() if v]
                if fam_labels:
                    b_parts.append(f"Situación familiar: {', '.join(fam_labels).replace('_', ' ')}")
                    
                lab = benef.get("situacion_laboral", {})
                lab_labels = [k for k, v in lab.items() if v]
                if lab_labels:
                    b_parts.append(f"Situación laboral: {', '.join(lab_labels).replace('_', ' ')}")

                vul = benef.get("vulnerabilidad", {})
                vul_labels = [k for k, v in vul.items() if v]
                if vul_labels:
                    b_parts.append(f"Vulnerabilidad: {', '.join(vul_labels).replace('_', ' ')}")
                    
                col = benef.get("colectivos_generales", {})
                col_labels = [k for k, v in col.items() if v]
                if col_labels:
                    b_parts.append(f"Colectivos: {', '.join(col_labels).replace('_', ' ')}")

                age_min = benef.get("age_min")
                age_max = benef.get("age_max")
                if age_min is not None or age_max is not None:
                    if age_min is not None and age_max is not None:
                        b_parts.append(f"Edad requerida: entre {age_min} y {age_max} años")
                    elif age_min is not None:
                        b_parts.append(f"Edad mínima: {age_min} años")
                    else:
                        b_parts.append(f"Edad máxima: {age_max} años")
                    
                req_res = benef.get("requires_residency")
                res_scope = benef.get("residency_scope")
                if req_res:
                    res_str = "Requiere residencia obligatoria"
                    if res_scope:
                        res_str += f" en {res_scope}"
                    b_parts.append(res_str)
                    
                other = benef.get("other_conditions")
                if other:
                    b_parts.append(f"Otras condiciones: {other}")
                    
                if b_parts:
                    benef_str = "; ".join(b_parts)
            contexto_texto += f"Beneficiarios y Requisitos: {benef_str}\n"

            # Formatear ámbito geográfico
            geo = doc.get('geographic_scope', {})
            geo_str = "N/A"
            if isinstance(geo, dict):
                level = geo.get("level", "")
                region = geo.get("region_name", "")
                if level or region:
                    geo_str = f"{level} ({region})"
            contexto_texto += f"Ámbito Geográfico: {geo_str}\n"
            
            # Referencia de búsqueda en el portal oficial
            contexto_texto += f"Referencia: {doc.get('referencia_busqueda', 'N/A')}\n"
            contexto_texto += f"Portal oficial para consultar: {doc.get('portal_url', BDNS_SEARCH_URL)}\n"

        prompt_path = Path(__file__).resolve().parent / "prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        prompt = f"Contexto:\n{contexto_texto}\n\nPregunta: {pregunta}\nRespuesta:"

        payload = {
            "model": "llama3",
            "system": system_prompt,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=600)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Error: No se recibió respuesta del LLM.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al conectar con Ollama: {e}")
            return f"Error en el servicio de generación: {str(e)}"


if __name__ == "__main__":
    # Prueba de ejecución hardcodeada para validar el pipeline MVP
    pregunta_prueba = "¿Hay ayudas para digitalizar mi comercio?"
    
    try:
        rag = RAGCore()
        
        # 1. Recuperar contexto
        documentos_recuperados = rag.buscar_ayudas(pregunta_prueba)
        
        print("\n" + "="*50)
        print(f"DOCUMENTOS RECUPERADOS ({len(documentos_recuperados)} por encima del umbral {MIN_SIMILARITY_SCORE}):")
        print("="*50)
        for d in documentos_recuperados:
            print(f"- {d.get('descripcion')} (Score: {d.get('_score'):.4f}) [{d.get('referencia_busqueda')}]")
        
        # 2. Generar respuesta
        respuesta_final = rag.generar_respuesta(pregunta_prueba, documentos_recuperados)
        
        print("\n" + "="*50)
        print("RESPUESTA OLLAMA:")
        print("="*50)
        print(respuesta_final)
        
    except Exception as e:
        logger.error(f"Fallo en la ejecución de prueba: {e}")
