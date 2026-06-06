import os
import sys

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st
from _texts import T

# set_page_config y _styles.apply() se llaman en app.py (una sola vez por carga)

st.title(T["inicio"]["titulo"])
st.markdown(T["inicio"]["subtitulo"])
st.divider()

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    with st.container(border=True):
        st.markdown('<div class="inicio-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(T["inicio"]["card_asistente_titulo"])
        st.markdown(T["inicio"]["card_asistente_desc"])
        st.markdown(T["inicio"]["card_asistente_ejemplo"])
        st.caption(T["inicio"]["card_asistente_caption"])
        st.page_link("pages/1_Asistente.py", label=T["inicio"]["card_asistente_boton"], use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown('<div class="inicio-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(T["inicio"]["card_buscador_titulo"])
        st.markdown(T["inicio"]["card_buscador_desc"])
        st.markdown(T["inicio"]["card_buscador_ejemplo"])
        st.caption(T["inicio"]["card_buscador_caption"])
        st.page_link("pages/2_Buscador.py", label=T["inicio"]["card_buscador_boton"], use_container_width=True)

with col3:
    with st.container(border=True):
        st.markdown('<div class="inicio-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(T["inicio"]["card_recursos_titulo"])
        st.markdown(T["inicio"]["card_recursos_desc"])
        st.markdown(T["inicio"]["card_recursos_ejemplo"])
        st.caption(T["inicio"]["card_recursos_caption"])
        st.page_link("pages/3_Recursos.py", label=T["inicio"]["card_recursos_boton"], use_container_width=True)

st.divider()
st.caption(T["inicio"]["footer"])
