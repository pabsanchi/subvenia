import os
import sys

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_mod3 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../modulo3-rag/src"))
for _p in (_src, _mod3):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
from _texts import T
from rag_core import RAGCore

# set_page_config y _styles.apply() se llaman en app.py (una sola vez por carga)


@st.cache_resource(show_spinner=T["asistente"]["spinner_carga"])
def _get_rag() -> RAGCore:
    return RAGCore()


st.page_link("pages/0_Inicio.py", label=T["comun"]["volver_inicio"])
st.title(T["asistente"]["titulo"])
st.markdown(T["asistente"]["subtitulo"])
st.divider()

rag_instance = None
try:
    rag_instance = _get_rag()
except Exception:
    st.error(T["asistente"]["error_no_disponible"])
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(T["asistente"]["chat_placeholder"]):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner(T["asistente"]["spinner_respuesta"]):
            try:
                contexto_docs = rag_instance.buscar_ayudas(prompt)
                respuesta = rag_instance.generar_respuesta(prompt, contexto_docs)
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception:
                st.error(T["asistente"]["error_consulta"])
