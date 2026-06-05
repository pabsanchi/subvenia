import streamlit as st
import _styles

st.set_page_config(
    page_title="SubvenIA — Ayudas para la Comunitat Valenciana",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

_styles.apply()

st.title("¿Buscas una ayuda o subvención?")
st.markdown(
    "SubvenIA te ayuda a encontrar ayudas públicas y recursos sociales "
    "de la Comunitat Valenciana de forma sencilla y gratuita."
)

st.divider()

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    with st.container(border=True):
        st.markdown('<div class="inicio-card-marker"></div>', unsafe_allow_html=True)
        st.markdown("### 🗣️ Cuéntame tu situación")
        st.markdown(
            "Si no sabes por dónde empezar, descríbenos lo que necesitas "
            "con tus propias palabras y te diremos qué ayudas podrían corresponderte."
        )
        st.markdown("*«Soy autónomo y no puedo pagar el alquiler»*")
        st.caption("Sin formularios. Sin filtros. Solo escribe.")
        st.page_link("pages/1_Asistente.py", label="Ir al asistente →", use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown('<div class="inicio-card-marker"></div>', unsafe_allow_html=True)
        st.markdown("### 🔍 Buscar por mi perfil")
        st.markdown(
            "Si prefieres explorar tú mismo, selecciona tu situación "
            "—laboral, familiar, colectivo— y te mostramos las "
            "convocatorias abiertas que encajan contigo."
        )
        st.markdown("*Solo convocatorias abiertas y vigentes.*")
        st.caption("Para quienes prefieren buscar con filtros.")
        st.page_link("pages/2_Buscador.py", label="Ir al buscador →", use_container_width=True)

with col3:
    with st.container(border=True):
        st.markdown('<div class="inicio-card-marker"></div>', unsafe_allow_html=True)
        st.markdown("### 🗺️ Encontrar ayuda cerca de mí")
        st.markdown(
            "Localiza centros, asociaciones y servicios sociales "
            "del Ayuntamiento de Valencia que atienden en persona "
            "a personas en tu situación."
        )
        st.markdown("*Más de 1.000 recursos en el mapa.*")
        st.caption("Servicios presenciales en la ciudad de Valencia.")
        st.page_link("pages/3_Recursos.py", label="Ver recursos →", use_container_width=True)

st.divider()
st.caption(
    "Datos de la Base de Datos Nacional de Subvenciones (BDNS) y del "
    "[Portal de Datos Abiertos del Ayuntament de València](https://opendata.vlci.valencia.es). "
    "Licencia CC BY 4.0."
)
