import os
import sys

# Añadir ruta para importar RAGCore desde el Módulo 3
modulo3_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../modulo3-rag/src'))
if modulo3_path not in sys.path:
    sys.path.append(modulo3_path)

import streamlit as st
from rag_core import RAGCore

# Configuración visual
st.set_page_config(
    page_title="SubvenIA",
    page_icon="🏛️",
    layout="centered"
)

st.title("Bienvenido a SubvenIA - Asistente de Ayudas Públicas.")
st.markdown("Describe tu situación actual para que pueda ayudarte a encontrar ayudas dirigidas a ti.")

# Caché del motor RAG para no recargar el modelo de embeddings (~1GB) en cada interacción
@st.cache_resource
def get_rag_core():
    return RAGCore()

try:
    rag = get_rag_core()
except Exception as e:
    st.error(f"Error al inicializar el motor RAG: {e}")
    st.stop()

# Inicializar el estado de sesión para guardar el historial de la conversación
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar el historial del chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input del usuario
if prompt := st.chat_input("Escribe tu pregunta sobre ayudas..."):
    # 1. Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Guardar mensaje del usuario en estado de sesión
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 3. Procesamiento y respuesta del asistente
    with st.chat_message("assistant"):
        with st.spinner("Buscando en bases oficiales y analizando..."):
            try:
                # Recuperar contexto
                contexto_docs = rag.buscar_ayudas(prompt)
                
                # Generar respuesta
                respuesta = rag.generar_respuesta(prompt, contexto_docs)
                
                # Mostrar la respuesta
                st.markdown(respuesta)
                
                # Guardar respuesta del asistente en el historial
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
                
            except Exception as e:
                st.error(f"Se produjo un error al procesar tu solicitud: {e}")
