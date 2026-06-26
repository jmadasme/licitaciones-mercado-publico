"""
utils.py — Utilidades varias: sanitización de nombres, logging, tipos comunes.
"""

import re
import logging
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """
    Limpia un nombre de archivo para el sistema de archivos local.
    Reemplaza caracteres inválidos por '_' y recorta espacios.

    Caracteres reemplazados: / \\ : * ? " < > |

    Args:
        filename: Nombre original del archivo.

    Returns:
        str: Nombre sanitizado.
    """
    if not filename:
        return "archivo_sin_nombre"

    # Reemplazar caracteres inválidos por '_'
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', filename)

    # Recortar espacios al inicio/final
    sanitized = sanitized.strip()

    # Eliminar puntos consecutivos y espacios múltiples
    sanitized = re.sub(r'\s+', ' ', sanitized)

    # Si el nombre queda vacío después de la limpieza
    if not sanitized:
        return "archivo_sin_nombre"

    # Si termina en punto, es molesto en Windows
    sanitized = sanitized.rstrip('.')

    if not sanitized:
        return "archivo_sin_nombre"

    return sanitized


def resolve_filename_collision(
    download_dir: Path,
    filename: str,
) -> str:
    """
    Resuelve colisiones de nombres de archivo añadiendo un sufijo numérico.

    Si ya existe un archivo con el mismo nombre en download_dir,
    se renombra añadiendo _1, _2, etc. antes de la extensión.

    Args:
        download_dir: Directorio donde se guardará el archivo.
        filename: Nombre del archivo (ya sanitizado).

    Returns:
        str: Nombre de archivo sin colisión.
    """
    dest = download_dir / filename

    if not dest.exists():
        return filename

    # Separar nombre base y extensión
    stem = dest.stem
    suffix = dest.suffix

    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_dest = download_dir / new_name
        if not new_dest.exists():
            return new_name
        counter += 1


def setup_logging(log_dir: Optional[Path] = None) -> None:
    """
    Configura el sistema de logging.

    - Consola: nivel INFO con timestamp y mensaje.
    - Archivo (opcional): nivel DEBUG en downloader.log.

    Args:
        log_dir: Directorio donde guardar el archivo de log.
                 Si es None, solo se configura logging en consola.
    """
    # Formato
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Evitar agregar handlers duplicados
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(console_handler)

    # Handler de archivo opcional
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "downloader.log"

        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
            root_logger.addHandler(file_handler)

        logging.info("Log guardado en: %s", log_path)
