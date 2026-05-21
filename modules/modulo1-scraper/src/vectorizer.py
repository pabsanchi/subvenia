# -*- coding: utf-8 -*-
"""
Módulo 1 (Scraper Real): Vectorizador de convocatorias para búsqueda semántica.

Este script se encarga de compilar toda la estructura de metadatos y campos enriquecidos
de una convocatoria en un formato textual descriptivo en español, y generar su
vector de embedding correspondiente mediante el modelo local 'intfloat/multilingual-e5-base'.
"""

import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def compile_text_for_embedding(convocatoria: dict) -> str:
    """
    Compila todos los campos descriptivos y estructurados de una convocatoria
    en un único bloque de texto coherente en español, idóneo para vectorizar
    con el modelo multilingual-e5.
    
    Añade el prefijo obligatorio 'passage: ' al principio.
    """
    parts = []
    
    # 1. Título y descripción principal
    titulo = convocatoria.get("descripcion", "")
    if titulo:
        parts.append(f"Título: {titulo}")
        
    desc_leng = convocatoria.get("descripcionLeng", "")
    if desc_leng:
        parts.append(f"Descripción alternativa: {desc_leng}")
        
    # 2. Organismos emisores y niveles
    nivel1 = convocatoria.get("nivel1", "")
    nivel2 = convocatoria.get("nivel2", "")
    nivel3 = convocatoria.get("nivel3", "")
    orgs = [n for n in [nivel1, nivel2, nivel3] if n]
    if orgs:
        parts.append(f"Organismo emisor: {', '.join(orgs)}")
        
    # 3. Ámbito geográfico
    geo = convocatoria.get("geographic_scope", {})
    if isinstance(geo, dict):
        level = geo.get("level", "")
        region = geo.get("region_name", "")
        if level or region:
            parts.append(f"Ámbito geográfico: {level} ({region})")
            
    # 4. Fecha límite de solicitud
    deadline = convocatoria.get("deadline", "")
    if deadline and deadline != "desconocido":
        parts.append(f"Fecha límite de solicitud: {deadline}")
        
    # 5. Beneficiarios y requisitos detallados (Gemini)
    benef = convocatoria.get("beneficiaries", {})
    if isinstance(benef, dict):
        benef_parts = []
        
        # Procesar booleanos para vectorización semántica
        fam = benef.get("situacion_familiar", {})
        if fam.get("familia_numerosa"): benef_parts.append("Esta ayuda va dirigida a familias numerosas.")
        if fam.get("familia_monoparental_o_soltero"): benef_parts.append("Esta ayuda va dirigida a familias monoparentales o padres/madres solteros.")
        if fam.get("familia_acogedora"): benef_parts.append("Esta ayuda va dirigida a familias acogedoras.")
        if fam.get("familia_con_dependientes"): benef_parts.append("Esta ayuda va dirigida a familias con personas dependientes a cargo.")
        
        lab = benef.get("situacion_laboral", {})
        if lab.get("empleado"): benef_parts.append("Esta ayuda va dirigida a empleados por cuenta ajena.")
        if lab.get("desempleado"): benef_parts.append("Esta ayuda va dirigida a personas desempleadas.")
        if lab.get("autonomo_o_emprendedor"): benef_parts.append("Esta ayuda va dirigida a autónomos o emprendedores.")
        if lab.get("jubilado_o_pensionista"): benef_parts.append("Esta ayuda va dirigida a jubilados o pensionistas.")
        if lab.get("empleado_hogar"): benef_parts.append("Esta ayuda va dirigida a empleados del hogar.")
        
        vul = benef.get("vulnerabilidad", {})
        if vul.get("riesgo_exclusion_pobreza"): benef_parts.append("Esta ayuda va dirigida a personas en riesgo de exclusión social o pobreza.")
        if vul.get("discapacidad_o_dependencia"): benef_parts.append("Esta ayuda va dirigida a personas con discapacidad o dependencia.")
        if vul.get("victima_violencia_genero"): benef_parts.append("Esta ayuda va dirigida a víctimas de violencia de género.")
        if vul.get("victima_terrorismo"): benef_parts.append("Esta ayuda va dirigida a víctimas de terrorismo.")
        
        col = benef.get("colectivos_generales", {})
        if col.get("menores"): benef_parts.append("Esta ayuda va dirigida a menores de edad.")
        if col.get("jovenes"): benef_parts.append("Esta ayuda va dirigida a jóvenes.")
        if col.get("personas_mayores"): benef_parts.append("Esta ayuda va dirigida a personas mayores.")
        if col.get("estudiantes_o_investigadores"): benef_parts.append("Esta ayuda va dirigida a estudiantes o investigadores.")
        if col.get("pymes_o_cooperativas"): benef_parts.append("Esta ayuda va dirigida a pymes o cooperativas.")
        if col.get("sector_primario_agri_ganadero"): benef_parts.append("Esta ayuda va dirigida al sector primario, agricultores o ganaderos.")
            
        age_min = benef.get("age_min")
        age_max = benef.get("age_max")
        if age_min is not None or age_max is not None:
            age_str = "Edad requerida: "
            if age_min is not None and age_max is not None:
                age_str += f"entre {age_min} y {age_max} años"
            elif age_min is not None:
                age_str += f"mínimo {age_min} años"
            else:
                age_str += f"máximo {age_max} años"
            benef_parts.append(age_str)
            
        income = benef.get("income_threshold")
        if income:
            benef_parts.append(f"Límite de ingresos: {income}")
            
        req_res = benef.get("requires_residency")
        res_scope = benef.get("residency_scope")
        if req_res:
            res_str = "Requiere residencia obligatoria"
            if res_scope:
                res_str += f" en {res_scope}"
            benef_parts.append(res_str)
            
        compat = benef.get("compatible_with_other_aids")
        if compat is not None:
            compat_str = "Compatible con otras ayudas" if compat else "Incompatible con otras ayudas"
            benef_parts.append(compat_str)
            
        other = benef.get("other_conditions")
        if other:
            benef_parts.append(f"Otras condiciones y requisitos: {other}")
            
        if benef_parts:
            parts.append(f"Requisitos y Beneficiarios: {'; '.join(benef_parts)}")
            
    compiled_text = ". ".join(parts)
    # Formato e5 obligatorio
    return f"passage: {compiled_text}"


class ConvocatoriaVectorizer:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        """Inicializa y descarga el modelo de embeddings SentenceTransformers."""
        logger.info(f"Instanciando SentenceTransformer con el modelo '{model_name}'...")
        self.model = SentenceTransformer(model_name)
        logger.info("Modelo de embeddings cargado correctamente.")

    def vectorize(self, text: str) -> list:
        """
        Genera el vector numérico (embedding) para el texto proporcionado.
        Retorna una lista de flotantes de longitud 768.
        """
        vector = self.model.encode(text)
        return vector.tolist()
