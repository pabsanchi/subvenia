"""
Sistema de estilos globales de SubvenIA.

Streamlit solo expone 4 variables de tema (primaryColor, backgroundColor,
secondaryBackgroundColor, textColor). Para poder usar colores distintos en
fondo de página, tarjetas e inputs definimos variables propias en config.toml
y las aplicamos via CSS inyectado.

Sistema de marcadores:
  Para apuntar con CSS a contenedores concretos sin afectar a otros
  stVerticalBlock de la página, cada tipo de tarjeta inyecta un div
  invisible con una clase identificadora:
    - .inicio-card-marker  → tarjetas de la landing (app.py)
    - .ayuda-card-marker   → tarjetas de resultados del buscador (buscador_tab.py)
    - .recurso-card-marker → panel de detalle del mapa (recursos_tab.py)
  El CSS usa :has(.marker) para pintar solo el bloque que contiene ese div,
  y :not(:has(stVerticalBlock .marker)) para evitar que el selector suba
  a bloques padre que también lo contienen indirectamente.
"""
import os
import tomllib
import streamlit as st


def load_config_val(key: str, default: str) -> str:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.streamlit/config.toml"))
    if not os.path.exists(path):
        return default
    try:
        with open(path, "rb") as f:
            config = tomllib.load(f)
            return config.get("theme", {}).get(key, default)
    except Exception:
        return default


def apply():
    bg_color = load_config_val("pageBackgroundColor", "#EDD9C0")
    container_bg = load_config_val("containerBackgroundColor", "#FFFFFF")
    input_bg = load_config_val("inputBackgroundColor", "#FFFFFF")
    secondary_bg = load_config_val("secondaryBackgroundColor", "#F5EAD8")
    listContainerBgColor = load_config_val("listContainerBgColor", "#85c9ebff")

    st.markdown(f"""
    <style>
    /* Fondo de página: arena cálida aplicada sobre el área principal */
    .stApp,
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stAppViewContainer"] > .main > .block-container {{
        background-color: {bg_color} !important;
    }}

    /* Cabecera (Toolbar superior) */
    header[data-testid="stHeader"],
    [data-testid="stHeader"],
    .stHeader {{
        background-color: {bg_color} !important;
    }}

    /* Redefinir variables de tema en el ámbito de contenedores de información (tarjetas e historial de chat) */
    div[data-testid="stExpander"],
    div[data-testid="stChatMessage"],
    div[data-testid="stVerticalBlock"]:has(.ayuda-card-marker):not(:has(div[data-testid="stVerticalBlock"] .ayuda-card-marker)),
    div[data-testid="stVerticalBlock"]:has(.recurso-card-marker):not(:has(div[data-testid="stVerticalBlock"] .recurso-card-marker)),
    div[data-testid="stVerticalBlock"]:has(.inicio-card-marker):not(:has(div[data-testid="stVerticalBlock"] .inicio-card-marker)) {{
        --background-color: {container_bg} !important;
        --secondary-background-color: {container_bg} !important;
    }}

    /* Redefinir variables de tema en el ámbito de campos de entrada (excepto chat input wrapper) */
    div[data-testid="stTextInput"],
    div[data-testid="stTextArea"],
    div[data-testid="stSelectbox"],
    div[data-testid="stMultiSelect"] {{
        --background-color: {input_bg} !important;
        --secondary-background-color: {input_bg} !important;
    }}

    /* Estilo de Tarjetas con marcadores (solo el bloque interno más específico) */
    div[data-testid="stVerticalBlock"]:has(.ayuda-card-marker):not(:has(div[data-testid="stVerticalBlock"] .ayuda-card-marker)),
    div[data-testid="stVerticalBlock"]:has(.recurso-card-marker):not(:has(div[data-testid="stVerticalBlock"] .recurso-card-marker)),
    div[data-testid="stVerticalBlock"]:has(.inicio-card-marker):not(:has(div[data-testid="stVerticalBlock"] .inicio-card-marker)) {{
        background-color: {container_bg} !important;
        box-shadow: 0 4px 12px rgba(100, 60, 10, 0.08) !important;
        border-radius: 10px !important;
        border: 1px solid #C8A882 !important;
        padding: 16px !important;
    }}

    /* Ocultar el marker HTML para que no deje espacio en el layout */
    .ayuda-card-marker, .recurso-card-marker, .inicio-card-marker, .rec-lista-marker {{
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }}

    /* Listado de recursos — contenedor scrollable (Elemento 1)
       Selector: stLayoutWrapper con overflow=auto que contiene el marker.
       El atributo overflow="auto" identifica de forma única los st.container(height=N). */
    div[data-testid="stLayoutWrapper"][overflow="auto"]:has(.rec-lista-marker) {{
        background-color: {secondary_bg} !important;
        border: 1px solid #C8A882 !important;
        border-radius: 8px !important;
        padding: 4px !important;
    }}
    div[data-testid="stVerticalBlock"][overflow="auto"]:has(.rec-lista-marker) {{
        background-color: {secondary_bg} !important;
        border-radius: 6px !important;
    }}

    /* Listado de recursos — cada fila/item (Elemento 2)
       Selector: stLayoutWrapper hijo directo del bloque scrollable. */
    div[data-testid="stVerticalBlock"][overflow="auto"]:has(.rec-lista-marker)
    > div[data-testid="stLayoutWrapper"] {{
        background-color: {listContainerBgColor} !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
        margin-bottom: 4px !important;
    }}

    /* Expanders (incluyendo cabecera y contenido interno) */
    div[data-testid="stExpander"],
    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background-color: {container_bg} !important;
        border-radius: 10px !important;
        border-color: #C8A882 !important;
    }}

    /* Contenedor del chat input y franja inferior st.bottom (hacer transparente para ver el fondo de la página) */
    div[data-testid="stBottom"],
    div[data-testid="stBottom"] > div,
    .stBottom,
    .stBottom > div,
    div[data-testid="stChatInput"],
    div:has(> [data-testid="stChatInput"]),
    div:has(> div > [data-testid="stChatInput"]),
    div[data-testid="stAppViewContainer"] .main > div:has([data-testid="stChatInput"]) {{
        background-color: transparent !important;
        background: transparent !important;
        box-shadow: none !important;
    }}

    /* Campos de entrada (inputs de texto, selectboxes, textareas, multiselects) */
    div[data-testid="stTextInput"] div[data-baseweb="base-input"],
    div[data-testid="stTextArea"] div[data-baseweb="base-input"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stMultiSelect"] div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"],
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stChatInput"] textarea,
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox select {{
        background-color: {input_bg} !important;
    }}

    /* Mensajes de chat */
    div[data-testid="stChatMessage"],
    div[data-testid="stChatMessageContent"],
    div[data-testid="stChatMessage"] div {{
        background-color: {container_bg} !important;
        border-radius: 10px !important;
    }}

    div[data-testid="stChatMessage"] {{
        border: 1px solid #E6D2B8 !important;
        padding: 12px !important;
        margin-bottom: 10px !important;
    }}

    /* Dataframes y Tablas (Listado de recursos, etc.) */
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {{
        --background-color: {input_bg} !important;
        --secondary-background-color: {secondary_bg} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

