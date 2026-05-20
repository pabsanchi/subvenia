# -*- coding: utf-8 -*-
"""
Módulo 1 (Scraper Real): Recogida de convocatorias raw desde la BDNS.

Este script descarga de forma incremental las convocatorias de subvenciones
para la Comunidad Valenciana destinadas a personas físicas (tipos 1 y 3) y
las guarda de manera persistente evitando duplicidades.
"""

import os
import json
import logging
from datetime import date
from pathlib import Path
from bdns.fetch.client import BDNSClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuración de rutas relativas
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE = DATA_DIR / "lista_convocatorias_raw.json"
TRACKING_FILE = DATA_DIR / "seguimiento_procesos.json"

# Inicialización de BDNSClient
client = BDNSClient()


def inicializar_seguimiento(filename=None):
    """Crea el archivo si no existe y lo inicializa con campos por defecto."""
    if filename is None:
        filename = TRACKING_FILE
    datos = {}
    if filename.exists():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning(f"El archivo {filename} está corrupto o vacío. Se reinicializará.")

    if "raws_rellenadas" not in datos:
        datos["raws_rellenadas"] = 0
        logger.info("Campo 'raws_rellenadas' inicializado a 0.")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4)


def obtener_fecha_hoy():
    """Retorna la fecha de hoy como una tupla (YYYY, M, DD)."""
    hoy = date.today()
    return (hoy.year, hoy.month, hoy.day)


def obtener_fecha_guardada(filename=None):
    """Obtiene la fecha de la última actualización almacenada como tupla (YYYY, MM, DD)."""
    if filename is None:
        filename = TRACKING_FILE
    if not filename.exists():
        return None

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            val = datos.get("ultima_actualizacion_convocatorias_raw")
            return tuple(val) if val else None
    except (json.JSONDecodeError, IOError, TypeError):
        return None


def actualizar_fecha_actualizacion(filename=None):
    """Actualiza el campo de última actualización a la fecha de hoy."""
    if filename is None:
        filename = TRACKING_FILE
    if not filename.exists():
        inicializar_seguimiento(filename)

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except (json.JSONDecodeError, IOError):
        datos = {}

    fecha_hoy = obtener_fecha_hoy()
    datos["ultima_actualizacion_convocatorias_raw"] = fecha_hoy

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
    logger.info(f"Campo 'ultima_actualizacion_convocatorias_raw' actualizado a {fecha_hoy}.")


def obtener_convocatorias_raw(start_date, end_date, regiones="54", tipos_beneficiario="1, 3"):
    """Llama a BDNSClient para descargar convocatorias dentro del rango especificado."""
    logger.info(f"Descargando convocatorias desde {start_date} hasta {end_date}...")
    try:
        convocatorias = list(client.fetch_convocatorias_busqueda(
            fechaDesde=date(*start_date),
            fechaHasta=date(*end_date),
            regiones=regiones,
            tiposBeneficiario=tipos_beneficiario,
            pageSize=1000,
            num_pages=100
        ))
        logger.info(f"Recibidas {len(convocatorias)} convocatorias desde la BDNS.")
        return convocatorias
    except Exception as e:
        logger.error(f"Error al llamar a la API de BDNS: {e}")
        return []


def actualizar_json_convocatorias(nuevas_convocatorias, filename=None):
    """Guarda las convocatorias en el JSON raw evitando duplicados por ID."""
    if filename is None:
        filename = RAW_FILE
    datos_existentes = []
    ids_existentes = set()

    if filename.exists():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                datos_existentes = json.load(f)
                ids_existentes = {c['id'] for c in datos_existentes}
        except (json.JSONDecodeError, IOError):
            datos_existentes = []

    contador_nuevas = 0
    for conv in nuevas_convocatorias:
        if conv.get('id') not in ids_existentes:
            datos_existentes.append(conv)
            ids_existentes.add(conv['id'])
            contador_nuevas += 1

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(datos_existentes, f, indent=4, ensure_ascii=False)
    logger.info(f"Se han añadido {contador_nuevas} nuevas convocatorias a {filename}.")


def flujo_obtencion_convocatorias_raw():
    """Ejecuta el flujo completo de recogida de datos raw."""
    inicializar_seguimiento()

    hoy = obtener_fecha_hoy()
    fecha_last_update = obtener_fecha_guardada()

    # Si no hay fecha previa guardada, iniciamos por defecto el 1 de Enero de 2026
    if fecha_last_update is None:
        fecha_last_update = (2026, 1, 1)
        logger.info(f"No se detectó fecha de última actualización. Usando fecha por defecto: {fecha_last_update}")

    if fecha_last_update == hoy:
        logger.info("Las convocatorias raw ya están actualizadas al día de hoy.")
    else:
        convocatorias_raw = obtener_convocatorias_raw(
            start_date=fecha_last_update,
            end_date=hoy,
            regiones="54",
            tipos_beneficiario="1, 3"
        )

        actualizar_json_convocatorias(convocatorias_raw)
        actualizar_fecha_actualizacion()


if __name__ == "__main__":
    logger.info("Iniciando flujo de recogida de convocatorias raw...")
    flujo_obtencion_convocatorias_raw()
    logger.info("Flujo finalizado.")
