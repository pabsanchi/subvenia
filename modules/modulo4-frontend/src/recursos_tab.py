"""
Módulo 6 — UI: Mapa de recursos sociales del Ayuntament de València.

Fuente de datos: Portal de Datos Abiertos del Ayuntament de València
Licencia: CC BY 4.0
"""
import os
import sys

_mod6 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modulo6-recursos/src"))
if _mod6 not in sys.path:
    sys.path.insert(0, _mod6)

import streamlit as st
import pandas as pd
from recursos_client import load_all_resources, CATEGORY_COLORS


# Nivel de módulo: @st.cache_data cachea por identidad de función,
# definir aquí garantiza que el caché se reutilice entre re-renders.
@st.cache_data(ttl=3600, show_spinner=False)
def _get_resources() -> pd.DataFrame:
    return load_all_resources()


def render() -> None:
    st.markdown("### 🗺️ Recursos Sociales en Valencia")
    st.markdown(
        "Directorio de centros, asociaciones y servicios sociales del "
        "Ayuntamiento de Valencia. Selecciona un colectivo para ver los recursos disponibles."
    )

    # Cargar datos (siempre desde caché tras la primera llamada)
    df = _get_resources()

    if df.empty:
        st.error("No se pudieron cargar los datos del portal opendata.vlci.valencia.es.")
        return

    available_cats = sorted(df["categoria"].unique().tolist())

    # -------------------------------------------------------------------------
    # Filtros — multiselect sin default: empieza vacío
    # -------------------------------------------------------------------------
    col_search, col_cats = st.columns([2, 2])
    with col_cats:
        selected_cats = st.multiselect(
            "Colectivo",
            options=available_cats,
            default=[],
            placeholder="Selecciona uno o más colectivos...",
            key="recursos_cats",
        )
    with col_search:
        search = st.text_input(
            "🔎 Buscar por nombre o entidad",
            placeholder="ej: residencia, asociación, ONCE...",
            key="recursos_search",
        )

    # -------------------------------------------------------------------------
    # Estado vacío: no renderizar nada hasta que el usuario elija algo.
    # Esto es crítico para el rendimiento: evita renderizar cientos de
    # st.container() en cada re-render de la app.
    # -------------------------------------------------------------------------
    if not selected_cats and not search.strip():
        st.info(
            "Selecciona al menos un colectivo (o escribe en el buscador) "
            "para ver los recursos disponibles."
        )
        st.divider()
        st.caption(
            "Fuente: [Portal de Datos Abiertos del Ayuntament de València]"
            "(https://opendata.vlci.valencia.es) · "
            "Categoría: Sociedad y Bienestar · Licencia CC BY 4.0"
        )
        return

    # -------------------------------------------------------------------------
    # Aplicar filtros
    # -------------------------------------------------------------------------
    if selected_cats:
        filtered = df[df["categoria"].isin(selected_cats)].copy()
    else:
        filtered = df.copy()

    if search.strip():
        mask = (
            filtered["descripcion"].str.contains(search.strip(), case=False, na=False)
            | filtered["titularidad"].str.contains(search.strip(), case=False, na=False)
        )
        filtered = filtered[mask]

    filtered = filtered.reset_index(drop=True)
    total_filtered = len(filtered)

    st.markdown(f"**{total_filtered}** recursos encontrados")

    if filtered.empty:
        st.info("No hay recursos que coincidan con los filtros seleccionados.")
        return

    # -------------------------------------------------------------------------
    # Layout: tabla a la izquierda, mapa a la derecha
    # -------------------------------------------------------------------------
    col_list, col_map = st.columns([1, 1], gap="medium")

    with col_list:
        st.markdown("#### Listado")
        # Usar dataframe en lugar de N st.container() individuales.
        # Renderizar cientos de containers bloquea la UI en cada re-render.
        display_df = filtered[["categoria", "descripcion", "titularidad"]].copy()
        display_df.columns = ["Colectivo", "Recurso", "Titular"]
        display_df["Titular"] = display_df["Titular"].fillna("—")
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, 35 + 35 * len(display_df)),
        )

    with col_map:
        st.markdown("#### Mapa")
        map_data = (
            filtered.dropna(subset=["lat", "lon"])[["lat", "lon", "color"]]
            .copy()
            .reset_index(drop=True)
        )
        if not map_data.empty:
            st.map(map_data, color="color", size=60, zoom=12)
            st.caption(f"{len(map_data)} recursos con coordenadas.")
        else:
            st.info("Sin coordenadas para los recursos seleccionados.")

    # -------------------------------------------------------------------------
    # Leyenda
    # -------------------------------------------------------------------------
    if len(selected_cats) > 1:
        st.divider()
        st.markdown("**Leyenda**")
        legend_cols = st.columns(min(len(selected_cats), 4))
        for i, cat in enumerate(sorted(selected_cats)):
            color = CATEGORY_COLORS.get(cat, "#7F8C8D")
            with legend_cols[i % len(legend_cols)]:
                st.markdown(
                    f"<span style='color:{color}'>●</span> {cat}",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.caption(
        "Fuente: [Portal de Datos Abiertos del Ayuntament de València]"
        "(https://opendata.vlci.valencia.es) · "
        "Categoría: Sociedad y Bienestar · Licencia CC BY 4.0"
    )
