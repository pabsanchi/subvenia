import os
import sys

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_mod3 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../modulo3-rag/src"))
for _p in (_src, _mod3):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import _styles
from rag_core import RAGCore

st.set_page_config(
    page_title="Asistente de ayudas — SubvenIA",
    page_icon="🗣️",
    layout="wide",
    
)

# ---------------------------------------------------------------------------
# @st.cache_resource a nivel de módulo: garantiza que el modelo de IA (1 GB)
# se cargue una sola vez y se reutilice en todos los rerenders.
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Preparando el asistente... (solo la primera vez)")
def _get_rag() -> RAGCore:
    return RAGCore()


_styles.apply()
st.page_link("app.py", label="← Volver al inicio")
st.title("🗣️ Asistente de ayudas")
st.markdown(
    "Cuéntame tu situación con tus propias palabras y te diré "
    "qué ayudas o subvenciones podrían corresponderte."
)
st.divider()

rag_instance = None
try:
    rag_instance = _get_rag()
except Exception:
    st.error(
        "El asistente no está disponible en este momento. "
        "Prueba de nuevo en unos minutos o usa el buscador."
    )
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Cuéntame tu situación o escribe qué tipo de ayuda necesitas..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Buscando ayudas..."):
            try:
                contexto_docs = rag_instance.buscar_ayudas(prompt)
                respuesta = rag_instance.generar_respuesta(prompt, contexto_docs)
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception:
                st.error("No he podido procesar tu consulta. Inténtalo de nuevo.")
