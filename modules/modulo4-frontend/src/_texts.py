"""
Centralización de todos los textos visibles de la interfaz de SubvenIA.

Edita este archivo para cambiar cualquier texto de la aplicación sin tocar
la lógica de las páginas. Cada clave está comentada con el archivo y el
elemento concreto donde aparece.

Convención para strings con variables:
  Los valores con {placeholder} se rellenan en el código con .format().
  El comentario indica qué variables espera cada string.

Para añadir un idioma: duplica este módulo (p.ej. _texts_en.py) y
ajusta el import en app.py.
"""

T: dict = {

    # =========================================================================
    # NAVEGACIÓN LATERAL
    # app.py → st.navigation() → etiquetas visibles en la barra lateral
    # =========================================================================
    "nav": {
        "inicio":    "Inicio",      # página de bienvenida
        "asistente": "Asistente",   # pages/1_Asistente.py
        "buscador":  "Buscador",    # pages/2_Buscador.py
        "recursos":  "Recursos",    # pages/3_Recursos.py
    },

    # =========================================================================
    # CONFIGURACIÓN GLOBAL
    # app.py → st.set_page_config()
    # =========================================================================
    "app": {
        # Título que aparece en la pestaña del navegador (fallback global)
        "page_title": "SubvenIA — Ayudas para la Comunitat Valenciana",
        # Icono de la pestaña del navegador
        "page_icon":  "🏛️",
    },

    # =========================================================================
    # ELEMENTOS COMUNES
    # Aparecen en varias páginas
    # =========================================================================
    "comun": {
        # pages/1_Asistente.py, pages/2_Buscador.py, pages/3_Recursos.py
        # → st.page_link(), enlace en la cabecera de cada página interior
        "volver_inicio": "← Volver al inicio",
    },

    # =========================================================================
    # LANDING — pages/0_Inicio.py
    # =========================================================================
    "inicio": {
        # Título principal de la landing
        # → st.title()
        "titulo": "¿Buscas una ayuda o subvención?",

        # Subtítulo bajo el título principal
        # → st.markdown()
        "subtitulo": (
            "SubvenIA te ayuda a encontrar ayudas públicas y recursos sociales "
            "de la Comunitat Valenciana de forma sencilla y gratuita."
        ),

        # ── Tarjeta 1: Asistente conversacional ──────────────────────────────
        # → st.markdown() dentro de st.container(border=True)
        "card_asistente_titulo":  "### Cuéntame tu situación",
        "card_asistente_desc": (
            "Si no sabes por dónde empezar, descríbenos lo que necesitas "
            "con tus propias palabras y te diremos qué ayudas podrían corresponderte."
        ),
        # → st.markdown(), texto de ejemplo en cursiva
        "card_asistente_ejemplo": "*«Soy autónomo y no puedo pagar el alquiler»*",
        # → st.caption()
        "card_asistente_caption": "Sin formularios. Sin filtros. Solo escribe con garantía de privacidad.",
        # → st.page_link(label=...)
        "card_asistente_boton":   "Ir al asistente →",

        # ── Tarjeta 2: Buscador filtrado ──────────────────────────────────────
        "card_buscador_titulo":  "### Buscar por mi cuenta",
        "card_buscador_desc": (
            "Opción dirigida a gente con experiencia, "
            "busca entre todas las ayudas con filtros y te mostramos las "
            "convocatorias que encajan con tus criterios."
        ),
        "card_buscador_ejemplo":  "*Solo convocatorias abiertas y vigentes.*",
        "card_buscador_caption":  "Para quienes prefieren buscar con filtros.",
        "card_buscador_boton":    "Ir al buscador →",

        # ── Tarjeta 3: Mapa de recursos ───────────────────────────────────────
        "card_recursos_titulo":  "### Encontrar ayuda cerca de mí",
        "card_recursos_desc": (
            "Localiza centros, asociaciones y servicios sociales "
            "del Ayuntamiento de Valencia que atienden en persona "
            "a personas en tu situación."
        ),
        "card_recursos_ejemplo":  "*Más de 1.000 recursos en el mapa.*",
        "card_recursos_caption":  "Servicios presenciales en la ciudad de Valencia.",
        "card_recursos_boton":    "Ver recursos →",

        # ── Pie de la landing ─────────────────────────────────────────────────
        # → st.caption() — el enlace usa markdown
        "footer": (
            "Datos de la Base de Datos Nacional de Subvenciones (BDNS) y del "
            "[Portal de Datos Abiertos del Ayuntament de València](https://opendata.vlci.valencia.es). "
            "Licencia CC BY 4.0."
        ),
    },

    # =========================================================================
    # ASISTENTE CONVERSACIONAL — pages/1_Asistente.py
    # =========================================================================
    "asistente": {
        # → st.set_page_config() / st.Page(icon=...)
        "page_title": "Asistente de ayudas — SubvenIA",
        "page_icon":  "🗣️",

        # → st.title()
        "titulo":    " Asistente de ayudas",
        # → st.markdown() bajo el título
        "subtitulo": (
            "Cuéntame tu situación con tus propias palabras y te diré "
            "qué ayudas o subvenciones podrían corresponderte."
        ),

        # → @st.cache_resource(show_spinner=...)
        # Aparece mientras se carga el modelo de IA (solo la primera vez)
        "spinner_carga": "Preparando el asistente... (solo la primera vez)",

        # → st.chat_input(placeholder=...)
        "chat_placeholder": "Cuéntame tu situación o escribe qué tipo de ayuda necesitas...",

        # → st.spinner() mientras el asistente genera la respuesta
        "spinner_respuesta": "Buscando ayudas...",

        # → st.error() si el modelo RAG no arranca
        "error_no_disponible": (
            "El asistente no está disponible en este momento. "
            "Prueba de nuevo en unos minutos o usa el buscador."
        ),
        # → st.error() si falla una consulta concreta
        "error_consulta": "No he podido procesar tu consulta. Inténtalo de nuevo.",
    },

    # =========================================================================
    # BUSCADOR FILTRADO — pages/2_Buscador.py + buscador_tab.py
    # =========================================================================
    "buscador": {
        # → st.set_page_config() / st.Page(icon=...)
        "page_title": "Buscador de ayudas — SubvenIA",
        "page_icon":  "🔍",

        # ── Cabecera de la sección ────────────────────────────────────────────
        # → st.markdown() — incluye el nivel de heading (###)
        "titulo":    "### Buscador de ayudas",
        # → st.markdown()
        "subtitulo": (
            "Marca las opciones que describen tu situación y te mostraremos "
            "las ayudas abiertas que podrían corresponderte."
        ),

        # ── Panel de filtros ──────────────────────────────────────────────────
        # → st.expander(label=...)
        "filtros_expander": "Filtros de perfil",
        # → _checkbox_group(label=...) — encabezados de cada grupo de checkboxes
        "filtro_laboral":        "Situación laboral",
        "filtro_familiar":       "Situación familiar",
        "filtro_vulnerabilidad": "Vulnerabilidad",
        "filtro_colectivo":      "Colectivo",
        # → st.text_input(label=..., placeholder=...)
        "filtro_palabras_label":       "🔎 Palabras clave en el título",
        "filtro_palabras_placeholder": "ej: alquiler, beca, energía...",
        # → st.selectbox(label=...) para tipo de ayuda
        "filtro_tipo_ayuda": "Tipo de ayuda",
        # → primer elemento de las listas de tipo y ámbito
        "filtro_todos":      "Todos",
        # → st.selectbox(label=...) para ámbito geográfico
        "filtro_ambito":     "Ámbito",

        # ── Botones de acción ─────────────────────────────────────────────────
        # → st.button(label=..., type="primary")
        "btn_buscar":  " Buscar ayudas",
        # → st.button(label=...)
        "btn_limpiar": "✕ Limpiar filtros",

        # ── Mensajes durante la búsqueda ──────────────────────────────────────
        # → st.spinner()
        "spinner_buscar": "Consultando base de datos...",

        # ── Mensajes de resultado ─────────────────────────────────────────────
        # → st.info() antes de hacer la primera búsqueda
        "info_inicial": "Marca las opciones que describen tu situación y pulsa **Buscar ayudas**.",
        # → st.error() si falla la llamada a la base de datos
        "error_busqueda": "No hemos podido realizar la búsqueda. Inténtalo de nuevo en unos instantes.",
        # → st.warning() cuando la búsqueda no devuelve resultados
        "warning_sin_resultados": (
            "No hemos encontrado ayudas con esos criterios. "
            "Prueba a marcar menos opciones para ampliar la búsqueda."
        ),
        # → st.success() — forma singular y plural según n
        # Uso: f"**{n}** {T['buscador']['resultados_1' if n==1 else 'resultados_n']}"
        "resultados_1": "convocatoria encontrada",
        "resultados_n": "convocatorias encontradas",
        # → st.caption() cuando se alcanza el límite de 60 resultados
        "caption_limite": "Mostrando los primeros 60 resultados. Añade más filtros para afinar.",

        # ── Aviso de convocatorias cerradas ocultas ───────────────────────────
        # → st.info() — fragmentos para construir la frase con concordancia
        # Uso: f"ℹ️ También hay **{hidden}** {noun} que {coinc} con tu búsqueda, pero {plazo}."
        "ocultas_noun_1":  "ayuda cerrada",
        "ocultas_noun_n":  "ayudas cerradas",
        "ocultas_coinc_1": "coincide",
        "ocultas_coinc_n": "coinciden",
        "ocultas_plazo_1": "está fuera de plazo y no se muestra",
        "ocultas_plazo_n": "están fuera de plazo y no se muestran",

        # ── Paginación ────────────────────────────────────────────────────────
        # → st.button(label=...)
        "pag_anterior":  "← Anterior",
        "pag_siguiente": "Siguiente →",
        # → st.markdown() — {page} = página actual (base 1), {total} = total páginas
        "pag_info": "Página {page} de {total}",

        # ── Tarjeta de resultado (_render_card) ───────────────────────────────
        # → doc.get('descripcion', ...) — fallback si el doc no tiene descripción
        "card_sin_descripcion": "Sin descripción",
        # → st.caption() — {deadline} = fecha límite
        "card_plazo": "📅 Plazo: {deadline}",
        # → st.expander(label=...)
        "card_condiciones": "ℹ️ Condiciones adicionales",
        # → st.caption() — {n_conv} = número de convocatoria
        # El enlace al portal se construye con BDNS_PORTAL_URL en el código
        "card_numero_conv": "Nº de convocatoria: **{n_conv}** · ",
        # → texto del enlace al portal BDNS
        "card_enlace_portal": "Ver en el portal oficial ↗",

        # ── Pie de página ─────────────────────────────────────────────────────
        # → st.caption() — {url} = BDNS_PORTAL_URL (se inyecta en el código)
        "footer": (
            "Información extraída de la [Base de Datos Nacional de Subvenciones]({url}), "
            "el registro oficial de ayudas públicas del Estado."
        ),
    },

    # =========================================================================
    # MAPA DE RECURSOS — pages/3_Recursos.py + recursos_tab.py
    # =========================================================================
    "recursos": {
        # → st.set_page_config() / st.Page(icon=...)
        "page_title": "Recursos sociales — SubvenIA",
        "page_icon":  "🗺️",

        # ── Cabecera de la sección ────────────────────────────────────────────
        # → st.markdown() — incluye el nivel de heading (###)
        "titulo":    "### 🗺️ Recursos Sociales en Valencia",
        # → st.markdown()
        "subtitulo": (
            "Directorio de centros, asociaciones y servicios sociales del "
            "Ayuntamiento de Valencia. \n\n Selecciona un colectivo para ver los recursos disponibles.\n\n"
            "Haz en un recurso en el mapa para obtener información detallada.\n\n"
            "Tambien puede pulsar el botón de un recurso de la lista más abajo para ubicar dicho recurso en el mapa."
        ),

        # ── Filtros ───────────────────────────────────────────────────────────
        # → st.multiselect(label=..., placeholder=...)
        "filtro_colectivo_label":       "Colectivo",
        "filtro_colectivo_placeholder": "Selecciona uno o más colectivos...",
        # → st.text_input(label=..., placeholder=...)
        "filtro_buscar_label":       "🔎 Buscar por nombre o entidad",
        "filtro_buscar_placeholder": "ej: residencia, asociación, ONCE...",

        # ── Mensajes de estado ────────────────────────────────────────────────
        # → st.info() cuando no hay colectivo ni texto de búsqueda
        "info_sin_seleccion": (
            "Selecciona al menos un colectivo (o escribe en el buscador) "
            "para ver los recursos disponibles."
        ),
        # → st.error() si falla la carga de datos del portal opendata
        "error_carga": "No se pudieron cargar los datos del portal opendata.vlci.valencia.es.",
        # → st.info() cuando los filtros no devuelven resultados
        "info_sin_resultados": "No hay recursos que coincidan con los filtros seleccionados.",
        # → st.markdown() — {n} = número de recursos encontrados
        "total_resultados": "**{n}** recursos encontrados",

        # ── Secciones del layout ──────────────────────────────────────────────
        # → st.markdown() encabezados de cada bloque
        "seccion_mapa":    "#### Mapa",
        "seccion_detalle": "#### Detalle",
        "seccion_listado": "#### Listado",

        # ── Mapa (pydeck) ─────────────────────────────────────────────────────
        # → st.info() si ningún recurso filtrado tiene coordenadas
        "mapa_sin_coordenadas": "Sin coordenadas para los recursos seleccionados.",
        # → st.caption() bajo el mapa — {n} = puntos con coordenadas
        "mapa_caption": "{n} recursos con coordenadas.",

        # ── Panel de detalle ──────────────────────────────────────────────────
        # → st.markdown() cuando no hay ningún punto seleccionado
        "detalle_vacio": (
            "Haz clic en un punto del mapa o en un elemento del listado "
            "para ver sus detalles."
        ),

        # ── Listado de botones ────────────────────────────────────────────────
        # → st.caption() cuando se supera _MAX_LIST — {max} = límite
        "listado_limite": "Mostrando los primeros {max} resultados. Usa el buscador para filtrar.",
        # → st.button(help=...) tooltip del botón de navegación de cada fila
        "listado_btn_tooltip": "Ver en el mapa",

        # ── Leyenda de colores (visible cuando hay más de un colectivo seleccionado)
        # → st.markdown()
        "leyenda": "**Leyenda**",

        # ── Pie de página ─────────────────────────────────────────────────────
        # → st.caption()
        "footer": (
            "Fuente: [Portal de Datos Abiertos del Ayuntament de València]"
            "(https://opendata.vlci.valencia.es) · "
            "Categoría: Sociedad y Bienestar · Licencia CC BY 4.0"
        ),
    },
}
