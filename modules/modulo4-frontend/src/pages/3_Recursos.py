import os
import sys

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st
from _texts import T
import recursos_tab

# set_page_config y _styles.apply() se llaman en app.py (una sola vez por carga)

st.page_link("pages/0_Inicio.py", label=T["comun"]["volver_inicio"])
recursos_tab.render()
