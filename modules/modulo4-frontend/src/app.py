import os
import sys

# Módulo 3 (RAG)
_mod3 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modulo3-rag/src"))
if _mod3 not in sys.path:
    sys.path.insert(0, _mod3)

import streamlit as st
from rag_core import RAGCore
import buscador_tab
import recursos_tab

st.set_page_config(
    page_title="SubvenIA",
    page_icon="🏛️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# @st.cache_resource DEBE estar a nivel de módulo, nunca dentro de un bloque
# `with tab:`. Si se define dentro del bloque, Streamlit crea un objeto función
# nuevo en cada re-render y la caché nunca se reutiliza, causando que RAGCore
# (modelo de 1GB) se recargue en cada interacción del usuario.
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Cargando modelo de IA... (solo ocurre la primera vez)")
def get_rag_core() -> RAGCore:
    return RAGCore()


st.title("🏛️ SubvenIA — Asistente de Ayudas Públicas")
st.caption("Encuentra subvenciones y recursos sociales de la Comunitat Valenciana")

tab_rag, tab_buscador, tab_recursos = st.tabs([
    "🤖 Asistente conversacional",
    "🔍 Buscador filtrado",
    "🗺️ Recursos sociales en Valencia",
])

# =============================================================================
# Tab 1: RAG conversacional
# =============================================================================
with tab_rag:
    st.markdown(
        "Describe tu situación con tus propias palabras y el asistente buscará "
        "las ayudas más adecuadas para ti."
    )

    rag_instance = None
    rag_error = None
    try:
        rag_instance = get_rag_core()
    except Exception as e:
        rag_error = str(e)

    if rag_error:
        st.error(f"Error al inicializar el motor RAG: {rag_error}")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Escribe tu pregunta sobre ayudas..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Buscando en bases oficiales y analizando..."):
                    try:
                        contexto_docs = rag_instance.buscar_ayudas(prompt)
                        respuesta = rag_instance.generar_respuesta(prompt, contexto_docs)
                        st.markdown(respuesta)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": respuesta}
                        )
                    except Exception as e:
                        st.error(f"Se produjo un error al procesar tu solicitud: {e}")

# =============================================================================
# Tab 2: Buscador filtrado (Módulo 5)
# =============================================================================
with tab_buscador:
    buscador_tab.render()

# =============================================================================
# Tab 3: Mapa de recursos sociales (Módulo 6)
# =============================================================================
with tab_recursos:
    recursos_tab.render()
