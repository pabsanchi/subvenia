"""
Módulo 5 — UI: Buscador filtrado de convocatorias de ayudas.
"""
import os
import sys

_mod5 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modulo5-buscador/src"))
if _mod5 not in sys.path:
    sys.path.insert(0, _mod5)

import streamlit as st
from _texts import T
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

_AID_ICONS = {
    "beca": "🎓", "subvencion": "💰", "prestacion": "🏛️",
    "ayuda_alquiler": "🏠", "ayuda_energia": "⚡", "ayuda_transporte": "🚌",
    "ayuda_alimentacion": "🍽️", "bonificacion": "📉",
    "deduccion_fiscal": "📋", "microcredito": "💳",
}

_STATUS_BADGE_COLORS = {
    "abierta":      ("#d4edda", "#155724"),
    "proximamente": ("#fff3cd", "#856404"),
    "permanente":   ("#cce5ff", "#004085"),
    "cerrada":      ("#f8d7da", "#721c24"),
    "desconocida":  ("#e2e3e5", "#383d41"),
}


def _badge(text: str, bg: str, fg: str, extra_style: str = "") -> str:
    style = (
        f"display:inline-block;padding:2px 9px;border-radius:12px;"
        f"background:{bg};color:{fg};font-size:0.78em;font-weight:600;"
        f"margin:2px 3px 2px 0;{extra_style}"
    )
    return f"<span style='{style}'>{text}</span>"


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
        st.markdown('<div class="ayuda-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(f"**{doc.get('descripcion', T['buscador']['card_sin_descripcion']).strip()}**")

        if organismo:
            st.markdown(f"<span style='font-size:0.9em;color:#555'>🏛️ {organismo}</span>", unsafe_allow_html=True)

        bg, fg = _STATUS_BADGE_COLORS.get(status_key, ("#e2e3e5", "#383d41"))
        row = _badge(status_label, bg, fg)
        if aid_type:
            row += _badge(f"{aid_icon} {aid_label}", "#e8f4f8", "#0c5460")
        if geo_label:
            row += _badge(geo_text, "#f0f0f0", "#444")
        st.markdown(row, unsafe_allow_html=True)

        if deadline and deadline not in ("desconocido", ""):
            st.caption(T["buscador"]["card_plazo"].format(deadline=deadline))

        if matching_tags:
            chips = "".join(_badge(f"✓ {t}", "#e8f5e9", "#2e7d32") for t in matching_tags)
            st.markdown(chips, unsafe_allow_html=True)

        if other_conditions:
            with st.expander(T["buscador"]["card_condiciones"]):
                st.write(other_conditions)

        if n_conv:
            st.caption(
                T["buscador"]["card_numero_conv"].format(n_conv=n_conv)
                + f"[{T['buscador']['card_enlace_portal']}]({BDNS_PORTAL_URL})"
            )


def render() -> None:
    st.markdown(T["buscador"]["titulo"])
    st.markdown(T["buscador"]["subtitulo"])
    st.divider()

    with st.expander(T["buscador"]["filtros_expander"], expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lab_sel = _checkbox_group(T["buscador"]["filtro_laboral"], SITUACION_LABORAL, "lab")
        with c2:
            fam_sel = _checkbox_group(T["buscador"]["filtro_familiar"], SITUACION_FAMILIAR, "fam")
        with c3:
            vul_sel = _checkbox_group(T["buscador"]["filtro_vulnerabilidad"], VULNERABILIDAD, "vul")
        with c4:
            col_sel = _checkbox_group(T["buscador"]["filtro_colectivo"], COLECTIVOS, "col")

        st.divider()
        cf1, cf2, cf3 = st.columns([2, 1, 1])
        with cf1:
            texto_sel = st.text_input(
                T["buscador"]["filtro_palabras_label"],
                placeholder=T["buscador"]["filtro_palabras_placeholder"],
                key="buscador_texto",
            )
        with cf2:
            todos = T["buscador"]["filtro_todos"]
            aid_opts = [todos] + list(AID_TYPES.keys())
            aid_disp = [todos] + list(AID_TYPES.values())
            aid_idx = st.selectbox(
                T["buscador"]["filtro_tipo_ayuda"], range(len(aid_opts)),
                format_func=lambda i: aid_disp[i], key="buscador_aid",
            )
            aid_sel = aid_opts[aid_idx] if aid_idx > 0 else None
        with cf3:
            geo_opts = [todos] + list(GEO_LEVELS.keys())
            geo_disp = [todos] + list(GEO_LEVELS.values())
            geo_idx = st.selectbox(
                T["buscador"]["filtro_ambito"], range(len(geo_opts)),
                format_func=lambda i: geo_disp[i], key="buscador_geo",
            )
            geo_sel = geo_opts[geo_idx] if geo_idx > 0 else None

    col_btn, col_clear = st.columns([2, 1])
    with col_btn:
        buscar = st.button(T["buscador"]["btn_buscar"], type="primary", use_container_width=True)
    with col_clear:
        limpiar = st.button(T["buscador"]["btn_limpiar"], use_container_width=True)

    if "buscador_results" not in st.session_state:
        st.session_state.buscador_results = None
        st.session_state.buscador_error = None
        st.session_state.buscador_hidden = 0
        st.session_state.buscador_filters_used = {}
        st.session_state.buscador_page = 0

    if limpiar:
        for key in SITUACION_LABORAL:
            st.session_state[f"lab_{key}"] = False
        for key in SITUACION_FAMILIAR:
            st.session_state[f"fam_{key}"] = False
        for key in VULNERABILIDAD:
            st.session_state[f"vul_{key}"] = False
        for key in COLECTIVOS:
            st.session_state[f"col_{key}"] = False
        st.session_state["buscador_texto"] = ""
        st.session_state["buscador_aid"] = 0
        st.session_state["buscador_geo"] = 0
        st.session_state.buscador_results = None
        st.session_state.buscador_error = None
        st.session_state.buscador_hidden = 0
        st.session_state.buscador_page = 0
        st.rerun()

    if buscar:
        with st.spinner(T["buscador"]["spinner_buscar"]):
            try:
                raw = buscar_convocatorias(
                    situacion_laboral=lab_sel or None,
                    situacion_familiar=fam_sel or None,
                    vulnerabilidad=vul_sel or None,
                    colectivos=col_sel or None,
                    aid_types=[aid_sel] if aid_sel else None,
                    geo_level=geo_sel,
                    texto=texto_sel.strip() or None,
                    max_results=80,
                    exclude_closed=True,
                )
                open_results = []
                hidden_extra = 0
                for doc in raw:
                    if get_status(doc)[0] == "cerrada":
                        hidden_extra += 1
                    else:
                        open_results.append(doc)

                st.session_state.buscador_results = open_results[:60]
                st.session_state.buscador_hidden = hidden_extra
                st.session_state.buscador_error = None
                st.session_state.buscador_page = 0
                st.session_state.buscador_filters_used = {
                    "situacion_laboral": lab_sel,
                    "situacion_familiar": fam_sel,
                    "vulnerabilidad": vul_sel,
                    "colectivos_generales": col_sel,
                }
            except Exception as e:
                st.session_state.buscador_error = str(e)
                st.session_state.buscador_results = None
                st.session_state.buscador_hidden = 0

    results = st.session_state.buscador_results
    error = st.session_state.buscador_error

    if error:
        st.error(T["buscador"]["error_busqueda"])
        return

    if results is None:
        st.info(T["buscador"]["info_inicial"])
        return

    if not results:
        st.warning(T["buscador"]["warning_sin_resultados"])
        return

    PAGE_SIZE = 20
    n = len(results)
    total_pages = max(1, (n + PAGE_SIZE - 1) // PAGE_SIZE)
    page = st.session_state.get("buscador_page", 0)
    page = min(page, total_pages - 1)

    noun = T["buscador"]["resultados_1"] if n == 1 else T["buscador"]["resultados_n"]
    st.success(f"**{n}** {noun}")
    if n == 60:
        st.caption(T["buscador"]["caption_limite"])

    hidden = st.session_state.get("buscador_hidden", 0)
    if hidden:
        noun_h = T["buscador"]["ocultas_noun_1"] if hidden == 1 else T["buscador"]["ocultas_noun_n"]
        coinc  = T["buscador"]["ocultas_coinc_1"] if hidden == 1 else T["buscador"]["ocultas_coinc_n"]
        plazo  = T["buscador"]["ocultas_plazo_1"] if hidden == 1 else T["buscador"]["ocultas_plazo_n"]
        st.info(f"ℹ️ También hay **{hidden}** {noun_h} que {coinc} con tu búsqueda, pero {plazo}.")

    selected_keys = st.session_state.buscador_filters_used
    any_profile = any(selected_keys.values())

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, n)
    for doc in results[start:end]:
        tags = get_matching_tags(doc, selected_keys) if any_profile else []
        _render_card(doc, tags)

    if total_pages > 1:
        st.divider()
        nav1, nav2, nav3 = st.columns([1, 2, 1])
        if page > 0 and nav1.button(T["buscador"]["pag_anterior"], use_container_width=True):
            st.session_state.buscador_page = page - 1
            st.rerun()
        nav2.markdown(
            f"<p style='text-align:center;margin:0'>"
            f"{T['buscador']['pag_info'].format(page=page + 1, total=total_pages)}"
            f"</p>",
            unsafe_allow_html=True,
        )
        if end < n and nav3.button(T["buscador"]["pag_siguiente"], use_container_width=True):
            st.session_state.buscador_page = page + 1
            st.rerun()

    st.divider()
    st.caption(T["buscador"]["footer"].format(url=BDNS_PORTAL_URL))
