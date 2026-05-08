import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuraciones Base
BASE_DIR = Path(__file__).resolve().parent.parent
# El usuario solicitó usar el .env ya existente (el de modulo2-db)
ENV_PATH = BASE_DIR.parent / "modulo2-db" / ".env"
INDEX_NAME = "ayudas_sociales"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "intfloat/multilingual-e5-base"


class RAGCore:
    def __init__(self):
        """Inicializa los clientes de Elasticsearch y el modelo de embeddings."""
        # 1. Cargar Variables de Entorno
        if not ENV_PATH.exists():
            logger.warning(f"No se encontró el archivo .env en {ENV_PATH}. Intentando variables del sistema.")
        load_dotenv(ENV_PATH)
        
        elastic_password = os.getenv("ELASTIC_PASSWORD")
        if not elastic_password:
            raise ValueError("ELASTIC_PASSWORD no encontrada en el entorno.")

        # 2. Conectar a Elasticsearch
        self.es = Elasticsearch(
            "http://localhost:9200",
            basic_auth=("elastic", elastic_password)
        )
        # Validar conexión
        if self.es.ping():
            logger.info("Conexión a Elasticsearch exitosa.")
        else:
            logger.error("No se pudo conectar a Elasticsearch.")

        # 3. Cargar Modelo de Embeddings
        logger.info(f"Cargando modelo de embeddings: {MODEL_NAME}...")
        self.encoder = SentenceTransformer(MODEL_NAME)
        logger.info("Modelo de embeddings cargado correctamente.")

    def buscar_ayudas(self, pregunta: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Convierte la pregunta a vector y busca en Elasticsearch mediante kNN.
        """
        logger.info(f"Buscando contexto para la pregunta: '{pregunta}'")
        
        # El modelo multilingual-e5 recomienda prefijar las queries con "query: "
        texto_query = f"query: {pregunta}"
        vector_query = self.encoder.encode(texto_query).tolist()

        knn_query = {
            "field": "embedding",
            "query_vector": vector_query,
            "k": top_k,
            "num_candidates": 50
        }

        # Especificamos qué campos queremos que nos devuelva (Source Filtering)
        _source = ["title", "description", "beneficiaries", "url"]

        response = self.es.search(
            index=INDEX_NAME,
            knn=knn_query,
            _source=_source
        )

        resultados = []
        hits = response.get("hits", {}).get("hits", [])
        for hit in hits:
            doc = hit["_source"]
            doc["_score"] = hit["_score"]
            resultados.append(doc)

        logger.info(f"Se han recuperado {len(resultados)} documentos relevantes.")
        return resultados

    def generar_respuesta(self, pregunta: str, contexto_docs: List[Dict[str, Any]]) -> str:
        """
        Genera una respuesta usando Ollama basada estrictamente en el contexto.
        """
        logger.info("Generando respuesta con Ollama...")

        # Construimos el texto del contexto
        contexto_texto = ""
        for i, doc in enumerate(contexto_docs, 1):
            contexto_texto += f"\n--- Documento {i} ---\n"
            contexto_texto += f"Título: {doc.get('title', 'N/A')}\n"
            contexto_texto += f"Descripción: {doc.get('description', 'N/A')}\n"
            contexto_texto += f"Beneficiarios: {doc.get('beneficiaries', 'N/A')}\n"
            contexto_texto += f"URL: {doc.get('url', 'N/A')}\n"

        system_prompt = (
            "Eres un experto en ayudas públicas de la Comunidad Valenciana. "
            "Responde a la pregunta del usuario utilizando ÚNICAMENTE la información del contexto proporcionado. "
            "Si la respuesta no está en el contexto, di 'No tengo información sobre eso'. "
            "Incluye siempre las URLs que aparecen en los documentos recuperados."
        )

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
        documentos_recuperados = rag.buscar_ayudas(pregunta_prueba, top_k=2)
        
        print("\n" + "="*50)
        print("DOCUMENTOS RECUPERADOS:")
        print("="*50)
        for d in documentos_recuperados:
            print(f"- {d.get('title')} (Score: {d.get('_score')})")
        
        # 2. Generar respuesta
        respuesta_final = rag.generar_respuesta(pregunta_prueba, documentos_recuperados)
        
        print("\n" + "="*50)
        print("RESPUESTA OLLAMA:")
        print("="*50)
        print(respuesta_final)
        
    except Exception as e:
        logger.error(f"Fallo en la ejecución de prueba: {e}")
