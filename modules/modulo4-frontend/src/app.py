import streamlit as st
from _texts import T
import _styles

st.set_page_config(
    page_title=T["app"]["page_title"],
    page_icon=T["app"]["page_icon"],
    layout="wide",
)

_styles.apply()

pg = st.navigation([
    st.Page("pages/0_Inicio.py",     title=T["nav"]["inicio"],    icon=T["app"]["page_icon"],        default=True),
    st.Page("pages/1_Asistente.py",  title=T["nav"]["asistente"], icon=T["asistente"]["page_icon"]),
    st.Page("pages/2_Buscador.py",   title=T["nav"]["buscador"],  icon=T["buscador"]["page_icon"]),
    st.Page("pages/3_Recursos.py",   title=T["nav"]["recursos"],  icon=T["recursos"]["page_icon"]),
])
pg.run()
