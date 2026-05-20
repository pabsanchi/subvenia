# -*- coding: utf-8 -*-
"""
Módulo 1 (Scraper Real): Enriquecimiento y clasificación de convocatorias con Gemini.

Este script lee las convocatorias raw descargadas, descarga sus PDFs oficiales
desde la BDNS, los envía a la API de Gemini para extraer y clasificar los requisitos
bajo un esquema estructurado (JSON), y consolida los resultados en 'convocatorias_full.json'.
"""

import os
import json
import time
import logging
from pathlib import Path
import typing_extensions as typing
from typing import Optional, Literal

from dotenv import load_dotenv
from bdns.fetch.client import BDNSClient
from google.api_core import exceptions
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuración de rutas relativas
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Directorio temporal de PDFs (se creará y limpiará dinámicamente)
PDF_DIR = DATA_DIR / "PDFdescargados"
PDF_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE = DATA_DIR / "lista_convocatorias_raw.json"
TRACKING_FILE = DATA_DIR / "seguimiento_procesos.json"
FULL_FILE = DATA_DIR / "convocatorias_full.json"

# Carga de la API Key desde el archivo .env del proyecto
# Probamos en la raíz del proyecto y alternativamente en modulo2-db/
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    DB_ENV_PATH = ROOT_DIR / "modules" / "modulo2-db" / ".env"
    if DB_ENV_PATH.exists():
        load_dotenv(DB_ENV_PATH)
    else:
        load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY no encontrada en las variables de entorno ni en los archivos .env.")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("🔑 SDK de Gemini configurado correctamente.")

# Inicialización de BDNSClient para descarga de documentos
client = BDNSClient()

# ===========================================================================
# Definición del esquema JSON estructurado para Gemini
# ===========================================================================

class GeographicScope(typing.TypedDict):
    level: Literal[
        "europeo",
        "nacional",
        "autonomico",
        "provincial",
        "municipal"
    ]
    region_name: Optional[str]


class BeneficiariesData(typing.TypedDict):
    # Colectivos principales
    target_groups: list[
        Literal[
            "ciudadania_general",
            # Edad
            "menores",
            "jovenes",
            "adultos",
            "personas_mayores",
            # Familia
            "familias",
            "familias_con_menores",
            # Vulnerabilidad
            "personas_con_discapacidad",
            "personas_dependientes",
            "personas_sin_hogar",
            "victimas_violencia_genero",
            "inmigrantes",
            "refugiados",
            # Educación
            "estudiantes",
            "estudiantes_universitarios",
            "investigadores",
            # Actividad económica
            "autonomos",
            "emprendedores",
            "pymes",
            "cooperativas",
            "entidades_sin_animo_lucro",
            # Sector primario
            "agricultores",
            "ganaderos",
        ]
    ]

    # Situación laboral
    employment_status: list[
        Literal[
            "empleado",
            "desempleado",
            "desempleado_larga_duracion",
            "busqueda_primer_empleo",
            "erte",
            "autonomo_activo",
            "nuevo_autonomo",
            "jubilado",
            "pensionista",
            "trabajador_publico",
            "empleado_hogar",
        ]
    ]

    # Situación familiar
    family_status: list[
        Literal[
            "familia_numerosa",
            "familia_monoparental",
            "padre_o_madre_soltero",
            "familia_acogedora",
            "familia_con_dependientes",
        ]
    ]

    # Vulnerabilidad / exclusión
    vulnerability_status: list[
        Literal[
            "riesgo_exclusion_social",
            "vulnerabilidad_economica",
            "discapacidad",
            "dependencia",
            "desahucio",
            "pobreza_energetica",
            "victima_terrorismo",
        ]
    ]

    # Restricciones de edad
    age_min: Optional[int]
    age_max: Optional[int]

    # Límites económicos
    income_threshold: Optional[str]

    # Requisitos de residencia
    requires_residency: bool
    residency_scope: Optional[str]

    # Compatibilidad con otras ayudas
    compatible_with_other_aids: Optional[bool]

    # Otros requisitos
    other_conditions: Optional[str]


class GrantExtraction(typing.TypedDict):
    beneficiaries: BeneficiariesData

    # Tipo de ayuda
    aid_type: Literal[
        "subvencion",
        "prestacion",
        "bonificacion",
        "deduccion_fiscal",
        "beca",
        "microcredito",
        "ayuda_alquiler",
        "ayuda_energia",
        "ayuda_transporte",
        "ayuda_alimentacion",
    ]

    # Administración que concede
    granting_body_level: Literal[
        "union_europea",
        "estado",
        "comunidad_autonoma",
        "diputacion",
        "municipio",
    ]

    # Estado de la convocatoria
    status: Literal[
        "abierta",
        "cerrada",
        "proximamente",
        "permanente",
    ]

    # Frecuencia de pago
    frequency: Optional[
        Literal[
            "pago_unico",
            "mensual",
            "trimestral",
            "anual",
        ]
    ]

    # Fecha límite o "desconocido"
    deadline: str

    # Ámbito geográfico
    geographic_scope: GeographicScope


# ===========================================================================
# Funciones auxiliares de seguimiento y gestión de ficheros
# ===========================================================================

def inicializar_seguimiento(filename=None):
    """Crea el archivo de seguimiento si no existe."""
    if filename is None:
        filename = TRACKING_FILE
    datos = {}
    if filename.exists():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    if "raws_rellenadas" not in datos:
        datos["raws_rellenadas"] = 0

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4)


def incrementar_raws_rellenadas(filename=None):
    """Incrementa en 1 el contador de convocatorias analizadas."""
    if filename is None:
        filename = TRACKING_FILE
    inicializar_seguimiento(filename)
    with open(filename, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    datos["raws_rellenadas"] = datos.get("raws_rellenadas", 0) + 1

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
    logger.info(f"'raws_rellenadas' incrementado a {datos['raws_rellenadas']}.")


def obtener_raws_rellenadas(filename=None):
    """Obtiene el número de convocatorias completadas."""
    if filename is None:
        filename = TRACKING_FILE
    if not filename.exists():
        return 0
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            return datos.get("raws_rellenadas", 0)
    except (json.JSONDecodeError, IOError):
        return 0


def obtener_cantidad_convocatorias_raw_almacenadas(filename=None):
    """Retorna la cantidad total de registros raw indexados."""
    if filename is None:
        filename = RAW_FILE
    if not filename.exists():
        return 0
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            return len(datos)
    except (json.JSONDecodeError, IOError):
        return 0


def obtener_convocatoria_raw_por_posicion(indice, filename=None):
    """Retorna una convocatoria raw basada en su posición del archivo JSON."""
    if filename is None:
        filename = RAW_FILE
    if not filename.exists():
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            convocatorias_raw = json.load(f)
            if 0 <= indice < len(convocatorias_raw):
                return convocatorias_raw[indice]
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error al leer convocatorias raw: {e}")
    return None


def obtener_convocatoria_raw_por_numero_convocatoria(numero_convocatoria_str, filename=None):
    """Busca una convocatoria raw por su numeroConvocatoria único."""
    if filename is None:
        filename = RAW_FILE
    if not filename.exists():
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            convocatorias_raw = json.load(f)
            for conv in convocatorias_raw:
                if str(conv.get('numeroConvocatoria')) == str(numero_convocatoria_str):
                    return conv
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error al leer convocatorias: {e}")
    return None


def inicializar_convocatorias_full(filename=None):
    """Crea el archivo final enriquecido si no existe."""
    if filename is None:
        filename = FULL_FILE
    if not filename.exists():
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)


def actualizar_convocatorias_full(nueva_entrada, filename=None):
    """Añade una convocatoria enriquecida al listado final."""
    if filename is None:
        filename = FULL_FILE
    inicializar_convocatorias_full(filename)
    datos_existentes = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            datos_existentes = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

    # Evitamos duplicados en convocatorias_full por numeroConvocatoria o id
    n_conv = nueva_entrada.get('numeroConvocatoria')
    datos_existentes = [d for d in datos_existentes if d.get('numeroConvocatoria') != n_conv]
    datos_existentes.append(nueva_entrada)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(datos_existentes, f, indent=4, ensure_ascii=False)
    logger.info(f"Convocatoria enriquecida guardada en {filename.name}.")


def guardar_convocatoria_full(numero_convocatoria_str, gemini_result):
    """Une los metadatos raw con la extracción estructurada de Gemini."""
    if gemini_result[0] != 0:
        return

    raw_convocatoria = obtener_convocatoria_raw_por_numero_convocatoria(numero_convocatoria_str)
    if raw_convocatoria:
        convocatoria_completa = raw_convocatoria.copy()
        convocatoria_completa['beneficiaries'] = gemini_result[1]['beneficiaries']
        convocatoria_completa['deadline'] = gemini_result[1].get('deadline', 'desconocido')
        convocatoria_completa['geographic_scope'] = gemini_result[1].get('geographic_scope', 'desconocido')

        actualizar_convocatorias_full(convocatoria_completa)
    else:
        logger.warning(f"No se localizó la convocatoria raw para el número {numero_convocatoria_str}.")


# ===========================================================================
# Conexión y llamada a la API de Gemini
# ===========================================================================

def comprobar_estado_api(nombre_modelo='gemini-2.5-flash'):
    """Verifica si la clave API y la cuota de Gemini están operativas."""
    logger.info(f"Comprobando estado de la API de Gemini (modelo: {nombre_modelo})...")
    if not GEMINI_API_KEY:
        logger.error("❌ API Key no configurada.")
        return False
    try:
        test_model = genai.GenerativeModel(nombre_modelo)
        response = test_model.generate_content("ping", generation_config={"max_output_tokens": 5})
        if response.text:
            logger.info("✅ Conexión exitosa: La API responde correctamente.")
            return True
    except exceptions.PermissionDenied:
        logger.error("❌ ERROR: API Key no válida o sin permisos (Permission Denied).")
    except exceptions.ResourceExhausted:
        logger.error("❌ ERROR: Cuota de la API agotada (429 - Resource Exhausted).")
    except exceptions.InvalidArgument:
        logger.error(f"❌ ERROR: El nombre del modelo '{nombre_modelo}' no es válido.")
    except exceptions.ServiceUnavailable:
        logger.error("❌ ERROR: El servicio de Google Gemini no está disponible (503).")
    except Exception as e:
        logger.error(f"❌ ERROR INESPERADO al verificar la API: {e}")
    return False


def extraer_datos_convocatoria(ruta_pdf):
    """
    Sube el PDF a Gemini, ejecuta el prompt estructurado y devuelve la extracción.
    
    Retorna una lista:
      - [0, dict_con_datos] -> Éxito.
      - [1, msg_error] -> Error inesperado.
      - [2, msg_error] -> Error 429 (Cuota Agotada).
      - [3, msg_error] -> Error 503 (Servicio no disponible).
    """
    # Usamos el modelo optimizado por defecto
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    pdf_file = None
    try:
        logger.info(f"Subiendo documento {ruta_pdf.name} a Gemini...")
        pdf_file = genai.upload_file(path=ruta_pdf, display_name=f"Convocatoria {ruta_pdf.stem}")

        while pdf_file.state.name == "PROCESSING":
            logger.info("Procesando PDF en el servidor de Gemini...")
            time.sleep(2)
            pdf_file = genai.get_file(pdf_file.name)

        if pdf_file.state.name == "FAILED":
            raise ValueError(f"El procesamiento del PDF falló en el servidor: {pdf_file.state.name}")

        logger.info("Documento subido y listo. Ejecutando análisis semántico...")

        prompt = """
        Eres un experto legal analizando convocatorias de ayudas estatales.
        Lee este documento y extrae la información requerida siguiendo estrictamente el esquema JSON proporcionado.

        INSTRUCCIONES CRÍTICAS DE CLASIFICACIÓN:
        1. MULTI-ETIQUETA: En los campos que son listas (target_groups, employment_status, family_status, vulnerability_status), puedes y DEBES añadir múltiples etiquetas si la ayuda aplica a varios perfiles. No te limites a una si el documento menciona varias.
        2. BENEFICIARIOS: Identifica con precisión los colectivos, situación laboral y vulnerabilidad basándote en los Enums permitidos.
        3. GEOGRAFÍA: Determina el nivel (autonómico, provincial, municipal) y especifica el nombre de la región o pueblo si es posible.
        4. FECHA LÍMITE: Extrae la fecha final de solicitud. Si no es clara, usa "desconocido".
        5. TIPO Y ESTADO: Clasifica el tipo de ayuda (beca, subvención, etc.) y su estado actual.

        IMPORTANTE: Responde exclusivamente en formato JSON. Todo el texto descriptivo debe estar en español.
        """

        response = model.generate_content(
            [pdf_file, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=GrantExtraction,
                temperature=0.1,
            )
        )

        return [0, json.loads(response.text)]

    except exceptions.ResourceExhausted:
        logger.error("⚠️ [ERROR 429] Cuota de API Gemini agotada.")
        return [2, "Quota exhausted"]
    except exceptions.ServiceUnavailable:
        logger.error("⚠️ [ERROR 503] Servicio de Gemini no disponible temporalmente.")
        return [3, "Service unavailable"]
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            logger.error(f"⚠️ [ERROR 429] Detectado por mensaje: {error_msg}")
            return [2, error_msg]
        logger.error(f"❌ [ERROR INESPERADO] en extracción de Gemini: {error_msg}")
        return [1, error_msg]
    finally:
        # Garantizamos la limpieza del archivo en el servidor de Google
        if pdf_file:
            try:
                genai.delete_file(pdf_file.name)
                logger.info("Limpieza de archivo en el servidor de Gemini completada.")
            except Exception as e:
                logger.warning(f"No se pudo eliminar el archivo del servidor: {e}")


# ===========================================================================
# Flujos de orquestación de completado
# ===========================================================================

def completar_convocatoria(nConvocatoria):
    """
    Descarga el primer PDF asociado a la convocatoria, llama a Gemini,
    guarda el resultado consolidado y limpia los recursos locales.
    """
    nConvocatoria_str = str(nConvocatoria)

    # 1. Obtener metadatos de los documentos
    logger.info(f"Consultando documentos asociados para la convocatoria: {nConvocatoria_str}")
    try:
        convocatoria_datos_documentos = list(client.fetch_convocatorias(numConv=nConvocatoria_str, vpd="GE"))
        if not convocatoria_datos_documentos:
            logger.warning(f"No se encontró respuesta para la convocatoria {nConvocatoria_str}")
            return [1, "Convocatoria no encontrada en BDNS"]
            
        documentos_convocatoria_list = convocatoria_datos_documentos[0].get("documentos", [])
        if not documentos_convocatoria_list:
            logger.warning(f"No hay documentos anexados en la convocatoria {nConvocatoria_str}")
            return [1, "No hay documentos"]
    except Exception as e:
        logger.error(f"Error al descargar metadatos de documentos para {nConvocatoria_str}: {e}")
        return [1, f"Error en BDNS metadata: {e}"]

    # 2. Descargar el primer PDF localmente
    id_documento = documentos_convocatoria_list[0].get("id")
    ruta_pdf = PDF_DIR / f"convocatoria{id_documento}.pdf"

    try:
        logger.info(f"Descargando PDF oficial de la BDNS (ID Documento: {id_documento})...")
        documento_bytes = client.fetch_convocatorias_documentos(idDocumento=id_documento)
        with open(ruta_pdf, "wb") as f:
            f.write(documento_bytes)
        logger.info(f"PDF guardado localmente de forma temporal en: {ruta_pdf.name}")
    except Exception as e:
        logger.error(f"Fallo al descargar los bytes del PDF {id_documento}: {e}")
        return [1, f"Error al descargar PDF: {e}"]

    # 3. Analizar con Gemini y guardar
    resultado = [1, "Unknown error"]
    try:
        resultado = extraer_datos_convocatoria(ruta_pdf)
        if resultado[0] == 0:
            logger.info(f"✅ Extracción semántica exitosa para la convocatoria {nConvocatoria_str}")
            guardar_convocatoria_full(nConvocatoria_str, resultado)
    finally:
        # Garantizamos la eliminación del archivo PDF temporal local para liberar espacio
        if ruta_pdf.exists():
            try:
                os.remove(ruta_pdf)
                logger.info(f"Archivo temporal local {ruta_pdf.name} eliminado.")
            except Exception as e:
                logger.warning(f"No se pudo limpiar el PDF temporal local: {e}")

    return resultado


def flujo_completado_masivo_convocatorias():
    """Ejecuta el procesamiento masivo reanudando desde el checkpoint guardado."""
    inicializar_seguimiento()

    total_raws = obtener_cantidad_convocatorias_raw_almacenadas()
    ya_rellenadas = obtener_raws_rellenadas()

    logger.info(f"📊 Progreso: {ya_rellenadas} procesadas de {total_raws} totales.")

    if ya_rellenadas >= total_raws:
        logger.info("No hay nuevas convocatorias raw para analizar.")
        return

    # Comprobamos la conexión API mínima antes de arrancar el bucle
    if not comprobar_estado_api():
        logger.error("🛑 La API de Gemini no está operativa. Se detiene el proceso masivo.")
        print("\n[AVISO CRÍTICO] La API de Gemini no está accesible (clave incorrecta, sin red o cuota agotada). Revisa tu archivo .env e inténtalo más tarde.\n")
        return

    for i in range(ya_rellenadas, total_raws):
        logger.info(f"\n--- Procesando registro en posición {i+1}/{total_raws} ---")

        conv_raw = obtener_convocatoria_raw_por_posicion(i)
        if not conv_raw:
            logger.warning(f"No se pudo recuperar la convocatoria en la posición {i}. Saltando...")
            incrementar_raws_rellenadas()
            continue

        n_conv_str = str(conv_raw.get('numeroConvocatoria'))

        # Llamar al flujo de completado individual
        resultado = completar_convocatoria(n_conv_str)
        codigo_error = resultado[0]

        if codigo_error == 0:
            incrementar_raws_rellenadas()
            logger.info(f"Convocatoria {n_conv_str} procesada con éxito.")
        elif codigo_error in (2, 3):
            # Errores críticos de API (429 o 503) -> Detenemos el flujo inmediatamente y alertamos por consola
            logger.error(f"🛑 PROCESO DETENIDO por error crítico de API (Código: {codigo_error}).")
            print(f"\n[AVISO CRÍTICO] Deteniendo ejecución: Cuota agotada (429) o servicio no disponible (503).")
            print(f"El progreso se ha guardado en la posición {i}. Ejecuta el script de nuevo cuando se restablezca el servicio.\n")
            return
        else:
            # Error inesperado (ej. PDF corrupto o fallo de BDNS) -> Detenemos para revisión manual
            logger.error(f"🛑 PROCESO DETENIDO por error inesperado en la convocatoria {n_conv_str}.")
            print(f"\n[AVISO DE ERROR] Deteniendo para revisión manual debido a fallo en convocatoria {n_conv_str}.")
            print(f"Mensaje de error: {resultado[1]}")
            print(f"Corrige la incidencia e inténtalo de nuevo. El progreso actual se mantiene intacto.\n")
            return

    logger.info("🎉 Proceso masivo de enriquecimiento finalizado con éxito.")


if __name__ == "__main__":
    logger.info("Iniciando flujo de enriquecimiento semántico con Gemini...")
    flujo_completado_masivo_convocatorias()
