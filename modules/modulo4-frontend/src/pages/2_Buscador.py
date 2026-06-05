import os
import sys

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st
import _styles
import buscador_tab

st.set_page_config(
    page_title="Buscador de ayudas — SubvenIA",
    page_icon="🔍",
    layout="wide",
)

_styles.apply()
st.page_link("app.py", label="← Volver al inicio")
buscador_tab.render()
