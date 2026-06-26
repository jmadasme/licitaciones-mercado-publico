"""
metadata.py — Serialización y guardado de metadatos JSON.

Guarda toda la información de la licitación, archivos y estado de
descargas en un archivo metadata.json dentro del directorio de descarga.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ticket_hash
from downloader import DownloadResult

logger = logging.getLogger(__name__)


def save_metadata(
    licitacion_data: dict[str, Any],
    archivos_data: list[dict[str, Any]],
    download_results: list[DownloadResult],
    download_dir: str,
    codigo: str,
    ticket: str,
) -> str:
    """
    Guarda un archivo metadata.json en download_dir con toda la información.

    Estructura del JSON:
    {
        "licitacion": { ... },              // respuesta completa del endpoint
        "archivos_count": N,
        "archivos": [ ... ],                // lista completa con metadatos originales
        "descargas": [                      // estado de cada descarga
            {
                "nombre": "...",
                "url_origen": "...",
                "archivo_local": "...",
                "descargado": true/false,
                "tamano_bytes": 12345,
                "error": null | "mensaje",
                "saltado": true/false
            },
            ...
        ],
        "fecha_descarga": "2026-06-26T12:00:00",
        "codigo_licitacion": "XXXX",
        "ticket_hash": "sha256:abc...",     // hash del ticket (NO el ticket en texto plano)
    }

    Args:
        licitacion_data: Datos completos de la licitación.
        archivos_data: Lista de archivos con metadatos originales.
        download_results: Resultados de las descargas.
        download_dir: Directorio donde guardar el archivo.
        codigo: Código de la licitación.
        ticket: Ticket de autenticación (solo se guarda el hash).

    Returns:
        str: Ruta del archivo metadata.json creado.
    """
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    # Construir la lista de descargas con estado
    descargas_list = []
    for archivo, result in zip(archivos_data, download_results):
        entry = {
            "nombre": result.filename,
            "url_origen": (
                archivo.get("URL")
                or archivo.get("Enlace")
                or archivo.get("Href")
                or archivo.get("url")
                or ""
            ),
            "archivo_local": result.path if result.success else None,
            "descargado": result.success,
            "tamano_bytes": result.size_bytes,
            "error": result.error_message,
            "saltado": result.skipped,
        }
        descargas_list.append(entry)

    # Si hay más archivos en archivos_data que resultados (por alguna razón),
    # añadimos los que faltan como no descargados
    while len(descargas_list) < len(archivos_data):
        idx = len(descargas_list)
        archivo = archivos_data[idx]
        entry = {
            "nombre": archivo.get("Nombre", f"archivo_{idx}"),
            "url_origen": archivo.get("URL", ""),
            "archivo_local": None,
            "descargado": False,
            "tamano_bytes": None,
            "error": "No se procesó (error antes de descargar)",
            "saltado": False,
        }
        descargas_list.append(entry)

    metadata = {
        "licitacion": licitacion_data,
        "archivos_count": len(archivos_data),
        "archivos": archivos_data,
        "descargas": descargas_list,
        "fecha_descarga": datetime.now(timezone.utc).isoformat(),
        "codigo_licitacion": codigo,
        "ticket_hash": ticket_hash(ticket),
    }

    metadata_path = download_path / "metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Metadatos guardados en: %s", metadata_path)
    return str(metadata_path)
