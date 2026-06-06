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

import pydeck as pdk
import streamlit as st
import pandas as pd
from recursos_client import load_all_resources, CATEGORY_COLORS
from _texts import T


def _hex_to_rgb(hex_color: str) -> list[int]:
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


@st.cache_data(ttl=3600, show_spinner=False)
def _get_resources() -> pd.DataFrame:
    return load_all_resources()


_MAX_LIST = 200


def render() -> None:
    st.markdown(T["recursos"]["titulo"])
    st.markdown(T["recursos"]["subtitulo"])

    df = _get_resources()

    if df.empty:
        st.error(T["recursos"]["error_carga"])
        return

    available_cats = sorted(df["categoria"].unique().tolist())

    col_search, col_cats = st.columns([2, 2])
    with col_cats:
        selected_cats = st.multiselect(
            T["recursos"]["filtro_colectivo_label"],
            options=available_cats,
            default=[],
            placeholder=T["recursos"]["filtro_colectivo_placeholder"],
            key="recursos_cats",
        )
    with col_search:
        search = st.text_input(
            T["recursos"]["filtro_buscar_label"],
            placeholder=T["recursos"]["filtro_buscar_placeholder"],
            key="recursos_search",
        )

    if not selected_cats and not search.strip():
        st.info(T["recursos"]["info_sin_seleccion"])
        st.divider()
        st.caption(T["recursos"]["footer"])
        return

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

    st.markdown(T["recursos"]["total_resultados"].format(n=len(filtered)))

    if filtered.empty:
        st.info(T["recursos"]["info_sin_resultados"])
        return

    # -------------------------------------------------------------------------
    # Estado de selección unificado
    #
    # rec_sel:     recurso actualmente mostrado en el panel de detalle.
    #              Lo establece cualquier interacción: botón de lista o clic en mapa.
    #              Formato: {lat, lon, descripcion, titularidad, categoria, source}
    #
    # rec_zoom_id: sufijo del key del mapa. Solo cambia al pulsar un botón de lista,
    #              lo que fuerza a pydeck a re-inicializar con el nuevo initial_view_state.
    #              Los clics en el mapa no modifican este valor: el mapa no salta.
    # -------------------------------------------------------------------------
    rec_sel = st.session_state.get("rec_sel")
    rec_zoom_id = st.session_state.get("rec_zoom_id", "0")

    if rec_sel and rec_sel.get("source") == "list" and rec_sel.get("lat") and rec_sel.get("lon"):
        view = pdk.ViewState(latitude=rec_sel["lat"], longitude=rec_sel["lon"], zoom=14)
    else:
        view = pdk.ViewState(latitude=39.47, longitude=-0.376, zoom=12)

    map_key = f"recursos_mapa_{rec_zoom_id}"

    # -------------------------------------------------------------------------
    # Layout: mapa (izq, 2/3) + detalle (der, 1/3)
    # -------------------------------------------------------------------------
    map_data = (
        filtered.dropna(subset=["lat", "lon"])[
            ["lat", "lon", "color", "descripcion", "titularidad", "categoria"]
        ]
        .copy()
        .reset_index(drop=True)
    )

    event = None
    col_map, col_detail = st.columns([2, 1], gap="medium")

    with col_map:
        st.markdown(T["recursos"]["seccion_mapa"])
        if not map_data.empty:
            map_data["color_rgb"] = map_data["color"].apply(_hex_to_rgb)
            layer = pdk.Layer(
                "ScatterplotLayer",
                id="recursos-layer",
                data=map_data,
                get_position=["lon", "lat"],
                get_fill_color="color_rgb",
                get_radius=50,
                pickable=True,
                auto_highlight=True,
            )
            tooltip = {
                "html": "<b>{descripcion}</b><br/>{titularidad}<br/><i>{categoria}</i>",
                "style": {
                    "backgroundColor": "white",
                    "color": "#333",
                    "padding": "8px",
                    "borderRadius": "4px",
                    "fontSize": "12px",
                },
            }
            event = st.pydeck_chart(
                pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip),
                use_container_width=True,
                height=420,
                on_select="rerun",
                selection_mode="single-object",
                key=map_key,
            )
            st.caption(T["recursos"]["mapa_caption"].format(n=len(map_data)))
        else:
            st.info(T["recursos"]["mapa_sin_coordenadas"])

    # Clic en el mapa → actualizar rec_sel (sin tocar rec_zoom_id: el mapa no salta)
    selected_objects = []
    if event and event.selection:
        selected_objects = (event.selection.get("objects") or {}).get("recursos-layer", [])

    if selected_objects:
        obj = selected_objects[0]
        new_sel = {
            "lat": obj.get("lat"),
            "lon": obj.get("lon"),
            "descripcion": obj.get("descripcion", "—"),
            "titularidad": obj.get("titularidad"),
            "categoria": obj.get("categoria", ""),
            "source": "map",
        }
        st.session_state["rec_sel"] = new_sel
        rec_sel = new_sel

    # -------------------------------------------------------------------------
    # Panel de detalle
    # -------------------------------------------------------------------------
    with col_detail:
        st.markdown(T["recursos"]["seccion_detalle"])
        if rec_sel:
            cat_color = CATEGORY_COLORS.get(rec_sel.get("categoria", ""), "#7F8C8D")
            with st.container(border=True):
                st.markdown('<div class="recurso-card-marker"></div>', unsafe_allow_html=True)
                st.markdown(
                    f"<span style='color:{cat_color};font-size:1.1em'>●</span> "
                    f"**{rec_sel.get('descripcion', '—')}**",
                    unsafe_allow_html=True,
                )
                tit = rec_sel.get("titularidad")
                if tit and pd.notna(tit):
                    st.markdown(f"🏛️ {tit}")
                st.caption(f"📂 {rec_sel.get('categoria', '')}")
        else:
            st.markdown(
                f"<div style='color:#999;padding:24px 0;text-align:center'>"
                f"{T['recursos']['detalle_vacio']}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # Listado — botones en contenedor desplazable
    #
    # Los botones no tienen estado visual persistido: al hacer clic actualizan
    # rec_sel y rec_zoom_id, luego hacen rerun. No hay "fila marcada" residual.
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown(T["recursos"]["seccion_listado"])

    list_df = filtered[["descripcion", "titularidad", "categoria", "lat", "lon"]].copy()
    if len(list_df) > _MAX_LIST:
        st.caption(T["recursos"]["listado_limite"].format(max=_MAX_LIST))
        list_df = list_df.head(_MAX_LIST)

    with st.container(height=min(420, 20 + 68 * len(list_df))):
        st.markdown('<div class="rec-lista-marker"></div>', unsafe_allow_html=True)
        for idx, row in list_df.iterrows():
            desc = row["descripcion"]
            tit = row["titularidad"] if pd.notna(row["titularidad"]) else ""
            cat = row["categoria"] if pd.notna(row["categoria"]) else ""

            col_text, col_btn = st.columns([10, 1])
            with col_text:
                second_line = tit if tit else cat
                st.markdown(f"**{desc}**  \n{second_line}" if second_line else f"**{desc}**")
            with col_btn:
                clicked = st.button("→", key=f"rec_btn_{idx}", help=T["recursos"]["listado_btn_tooltip"])

            if clicked:
                new_sel = {
                    "lat": row["lat"] if pd.notna(row["lat"]) else None,
                    "lon": row["lon"] if pd.notna(row["lon"]) else None,
                    "descripcion": desc,
                    "titularidad": tit or None,
                    "categoria": cat,
                    "source": "list",
                }
                st.session_state["rec_sel"] = new_sel
                if new_sel["lat"] is not None:
                    st.session_state["rec_zoom_id"] = str(idx)
                st.rerun()

    # -------------------------------------------------------------------------
    # Leyenda
    # -------------------------------------------------------------------------
    if len(selected_cats) > 1:
        st.divider()
        st.markdown(T["recursos"]["leyenda"])
        legend_cols = st.columns(min(len(selected_cats), 4))
        for i, cat in enumerate(sorted(selected_cats)):
            color = CATEGORY_COLORS.get(cat, "#7F8C8D")
            with legend_cols[i % len(legend_cols)]:
                st.markdown(
                    f"<span style='color:{color}'>●</span> {cat}",
                    unsafe_allow_html=True,
                )

    st.divider()
    st.caption(T["recursos"]["footer"])
