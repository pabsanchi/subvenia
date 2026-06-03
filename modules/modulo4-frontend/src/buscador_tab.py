"""
Módulo 5 — UI: Buscador filtrado de convocatorias de ayudas.
"""
import os
import sys

_mod5 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modulo5-buscador/src"))
if _mod5 not in sys.path:
    sys.path.insert(0, _mod5)

import streamlit as st
from buscador_client import (
    BDNS_PORTAL_URL,
    AID_TYPES,
    COLECTIVOS,
    GEO_LEVELS,
    SITUACION_FAMILIAR,
    SITUACION_LABORAL,
    VULNERABILIDAD,
    buscar_convocatorias,
    get_matching_tags,
    get_status,
)

_STATUS_ICONS = {
    "abierta": "🟢",
    "cerrada": "🔴",
    "proximamente": "🟡",
    "permanente": "🔵",
    "desconocida": "⚪",
}
_AID_ICONS = {
    "beca": "🎓", "subvencion": "💰", "prestacion": "🏛️",
    "ayuda_alquiler": "🏠", "ayuda_energia": "⚡", "ayuda_transporte": "🚌",
    "ayuda_alimentacion": "🍽️", "bonificacion": "📉",
    "deduccion_fiscal": "📋", "microcredito": "💳",
}


def _checkbox_group(label: str, options: dict, key_prefix: str) -> list[str]:
    st.markdown(f"**{label}**")
    return [k for k, v in options.items() if st.checkbox(v, key=f"{key_prefix}_{k}")]


def _render_card(doc: dict, matching_tags: list[str]) -> None:
    status_key, status_label = get_status(doc)
    aid_type = doc.get("aid_type") or ""
    aid_icon = _AID_ICONS.get(aid_type, "📄")
    aid_label = AID_TYPES.get(aid_type, "Ayuda") if aid_type else "Ayuda"

    geo = doc.get("geographic_scope") or {}
    geo_level = geo.get("level", "")
    geo_region = geo.get("region_name", "")
    geo_label = GEO_LEVELS.get(geo_level, geo_level.capitalize()) if geo_level else ""
    geo_text = f"📍 {geo_label}" + (f" · {geo_region}" if geo_region else "")

    organismo = doc.get("nivel3", "")
    deadline = doc.get("deadline", "")
    n_conv = doc.get("numeroConvocatoria", "")
    other_conditions = (doc.get("beneficiaries") or {}).get("other_conditions") or ""

    with st.container(border=True):
        st.markdown(f"**{doc.get('descripcion', 'Sin descripción').strip()}**")

        cols = st.columns([1, 1, 1])
        cols[0].markdown(f"{_STATUS_ICONS.get(status_key, '⚪')} {status_label}")
        if aid_type:
            cols[1].markdown(f"{aid_icon} {aid_label}")
        if geo_label:
            cols[2].markdown(geo_text)

        if organismo:
            st.caption(f"🏛️ {organismo}")
        if deadline and deadline not in ("desconocido", ""):
            st.caption(f"📅 Plazo: {deadline}")
        if other_conditions:
            with st.expander("ℹ️ Condiciones adicionales"):
                st.write(other_conditions)
        if matching_tags:
            st.markdown(" · ".join(f"`{t}`" for t in matching_tags))
        if n_conv:
            st.caption(
                f"Ref. BDNS nº **{n_conv}** · "
                f"[Buscar en el portal oficial ↗]({BDNS_PORTAL_URL})"
            )


def render() -> None:
    st.markdown("### 🔍 Buscador de Ayudas y Subvenciones")
    st.markdown(
        "Selecciona tu situación para ver las convocatorias de la BDNS "
        "para las que podrías ser elegible."
    )
    st.divider()

    # -------------------------------------------------------------------------
    # Filtros
    # -------------------------------------------------------------------------
    with st.expander("🎛️ Filtros de perfil", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lab_sel = _checkbox_group("Situación laboral", SITUACION_LABORAL, "lab")
        with c2:
            fam_sel = _checkbox_group("Situación familiar", SITUACION_FAMILIAR, "fam")
        with c3:
            vul_sel = _checkbox_group("Vulnerabilidad", VULNERABILIDAD, "vul")
        with c4:
            col_sel = _checkbox_group("Colectivo", COLECTIVOS, "col")

        st.divider()
        cf1, cf2, cf3 = st.columns([2, 1, 1])
        with cf1:
            texto_sel = st.text_input(
                "🔎 Palabras clave en el título",
                placeholder="ej: alquiler, beca, energía...",
                key="buscador_texto",
            )
        with cf2:
            aid_opts = ["Todos"] + list(AID_TYPES.keys())
            aid_disp = ["Todos"] + list(AID_TYPES.values())
            aid_idx = st.selectbox(
                "Tipo de ayuda", range(len(aid_opts)),
                format_func=lambda i: aid_disp[i], key="buscador_aid",
            )
            aid_sel = aid_opts[aid_idx] if aid_idx > 0 else None
        with cf3:
            geo_opts = ["Todos"] + list(GEO_LEVELS.keys())
            geo_disp = ["Todos"] + list(GEO_LEVELS.values())
            geo_idx = st.selectbox(
                "Ámbito", range(len(geo_opts)),
                format_func=lambda i: geo_disp[i], key="buscador_geo",
            )
            geo_sel = geo_opts[geo_idx] if geo_idx > 0 else None

    col_btn, col_clear = st.columns([2, 1])
    with col_btn:
        buscar = st.button("🔍 Buscar ayudas", type="primary", use_container_width=True)
    with col_clear:
        limpiar = st.button("✕ Limpiar resultados", use_container_width=True)

    # -------------------------------------------------------------------------
    # Session state para persistir resultados entre re-renders
    # -------------------------------------------------------------------------
    if "buscador_results" not in st.session_state:
        st.session_state.buscador_results = None
        st.session_state.buscador_error = None
        st.session_state.buscador_filters_used = {}

    if limpiar:
        st.session_state.buscador_results = None
        st.session_state.buscador_error = None

    if buscar:
        with st.spinner("Consultando base de datos..."):
            try:
                results = buscar_convocatorias(
                    situacion_laboral=lab_sel or None,
                    situacion_familiar=fam_sel or None,
                    vulnerabilidad=vul_sel or None,
                    colectivos=col_sel or None,
                    aid_types=[aid_sel] if aid_sel else None,
                    geo_level=geo_sel,
                    texto=texto_sel.strip() or None,
                )
                st.session_state.buscador_results = results
                st.session_state.buscador_error = None
                st.session_state.buscador_filters_used = {
                    "situacion_laboral": lab_sel,
                    "situacion_familiar": fam_sel,
                    "vulnerabilidad": vul_sel,
                    "colectivos_generales": col_sel,
                }
            except Exception as e:
                st.session_state.buscador_error = str(e)
                st.session_state.buscador_results = None

    # -------------------------------------------------------------------------
    # Mostrar resultados desde session_state
    # -------------------------------------------------------------------------
    results = st.session_state.buscador_results
    error = st.session_state.buscador_error

    if error:
        st.error(f"Error al consultar la base de datos: {error}")
        return

    if results is None:
        st.info(
            "Selecciona tu perfil y pulsa **Buscar ayudas** para ver las convocatorias."
        )
        return

    if not results:
        st.warning(
            "No se encontraron convocatorias con esos filtros. "
            "Prueba a seleccionar menos criterios."
        )
        return

    n = len(results)
    st.success(f"**{n}** {'convocatoria encontrada' if n == 1 else 'convocatorias encontradas'}")
    if n == 60:
        st.caption("Mostrando los primeros 60 resultados. Añade filtros para acotar.")

    selected_keys = st.session_state.buscador_filters_used
    any_profile = any(selected_keys.values())

    for doc in results:
        tags = get_matching_tags(doc, selected_keys) if any_profile else []
        _render_card(doc, tags)

    st.divider()
    st.caption(
        "Datos de la [BDNS – Base de Datos Nacional de Subvenciones]"
        f"({BDNS_PORTAL_URL}), procesados por SubvenIA."
    )
