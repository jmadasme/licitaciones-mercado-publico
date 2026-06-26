"""
downloader.py — Descarga de archivos con barra de progreso (tqdm).

Gestiona la descarga por lotes de archivos con progreso visual,
sanitización de nombres, colisiones y reintentos individuales.
"""

import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Callable

import requests
import tqdm

from api_client import (
    APIClient,
    BACKOFF_BASE,
    BACKOFF_FACTOR,
    DownloadError,
    HTTP_TIMEOUT_CONNECT,
    HTTP_TIMEOUT_READ,
)
from mercado_publico import build_download_url
from utils import sanitize_filename, resolve_filename_collision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipos / DataClasses
# ---------------------------------------------------------------------------
@dataclass
class DownloadResult:
    """Resultado de la descarga de un archivo individual."""

    filename: str
    success: bool
    path: Optional[str] = None
    error_message: Optional[str] = None
    size_bytes: Optional[int] = None
    skipped: bool = False


# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------
def download_all_files(
    api_client: APIClient,
    archivos: list[dict[str, Any]],
    download_dir: str,
    ticket: str,
    overwrite: bool = False,
    progress_callback: Optional[Callable] = None,
    min_pause: float = 1.0,
    max_pause: float = 2.0,
) -> list[DownloadResult]:
    """
    Descarga todos los archivos de la lista a download_dir.

    Args:
        api_client: Cliente HTTP.
        archivos: Lista de metadatos de archivos del endpoint.
        download_dir: Directorio destino.
        ticket: Ticket para autenticación en URLs de descarga.
        overwrite: Si True, sobrescribe archivos existentes.
        progress_callback: Callback opcional para reportar progreso general.
        min_pause: Pausa mínima entre descargas (jitter).
        max_pause: Pausa máxima entre descargas (jitter).

    Returns:
        Lista de DownloadResult con el resultado de cada archivo.
    """
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    results: list[DownloadResult] = []

    for i, archivo in enumerate(archivos):
        nombre = archivo.get("Nombre") or archivo.get("nombre") or archivo.get("name") or f"archivo_{i + 1}"
        url = (
            archivo.get("URL")
            or archivo.get("Enlace")
            or archivo.get("Href")
            or archivo.get("url")
            or archivo.get("enlace")
        )

        if not url:
            logger.warning("Archivo #%d ('%s') no tiene URL, saltando.", i + 1, nombre)
            results.append(DownloadResult(
                filename=str(nombre),
                success=False,
                error_message="No tiene URL de descarga",
            ))
            continue

        # Sanitizar nombre
        safe_name = sanitize_filename(str(nombre))

        # Resolver colisiones (solo si no se sobrescribe)
        if not overwrite:
            safe_name = resolve_filename_collision(download_path, safe_name)

        dest_path = download_path / safe_name

        # Si ya existe y no se sobrescribe
        if dest_path.exists() and not overwrite:
            logger.info("Archivo existente, saltando: %s", safe_name)
            results.append(DownloadResult(
                filename=safe_name,
                success=True,
                path=str(dest_path),
                size_bytes=dest_path.stat().st_size,
                skipped=True,
            ))
            continue

        # Construir URL de descarga
        download_url = build_download_url(archivo, ticket)
        if not download_url:
            results.append(DownloadResult(
                filename=safe_name,
                success=False,
                error_message="No se pudo construir URL de descarga",
            ))
            continue

        # Intentar descargar
        logger.info("Descargando (%d/%d): %s", i + 1, len(archivos), safe_name)

        try:
            # Descargamos con la sesión del api_client directamente con streaming
            # para poder mostrar barra de progreso
            size = _download_with_progress(
                api_client=api_client,
                url=download_url,
                dest_path=str(dest_path),
                display_name=safe_name,
            )

            results.append(DownloadResult(
                filename=safe_name,
                success=True,
                path=str(dest_path),
                size_bytes=size,
            ))
            logger.info("Descargado correctamente: %s (%d bytes)", safe_name, size)

        except DownloadError as e:
            logger.error("Error al descargar '%s': %s", safe_name, e)
            results.append(DownloadResult(
                filename=safe_name,
                success=False,
                error_message=str(e),
            ))
        except OSError as e:
            logger.error("Error de E/S al descargar '%s': %s", safe_name, e)
            results.append(DownloadResult(
                filename=safe_name,
                success=False,
                error_message=f"Error de E/S: {e}",
            ))
            # Disco lleno, detener descargas restantes
            logger.critical("Error de E/S crítico. Deteniendo descargas.")
            break

        # Pausa entre descargas (jitter)
        if i < len(archivos) - 1:
            pause = random.uniform(min_pause, max_pause)
            logger.debug("Pausa de %.2f segundos antes del siguiente archivo...", pause)
            time.sleep(pause)

        # Callback de progreso
        if progress_callback:
            progress_callback(i + 1, len(archivos))

    return results


def _cleanup_part_file(dest_path: str) -> None:
    """
    Elimina el archivo parcial .part asociado a dest_path si existe.

    Args:
        dest_path: Ruta del archivo de destino (sin .part).
    """
    part_path = str(dest_path) + ".part"
    try:
        if os.path.exists(part_path):
            os.remove(part_path)
            logger.debug("Archivo parcial eliminado: %s", part_path)
    except OSError as e:
        logger.warning("No se pudo eliminar el archivo parcial %s: %s", part_path, e)


def _download_with_progress(
    api_client: APIClient,
    url: str,
    dest_path: str,
    display_name: str,
) -> int:
    """
    Descarga un archivo con barra de progreso tqdm.

    Args:
        api_client: Cliente HTTP.
        url: URL de descarga.
        dest_path: Ruta local de destino.
        display_name: Nombre para mostrar en la barra.

    Returns:
        int: Tamaño en bytes descargado.

    Raises:
        DownloadError: si la descarga falla.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(1, api_client.max_retries + 1):
        try:
            response = api_client.session.get(
                url,
                timeout=(HTTP_TIMEOUT_CONNECT, HTTP_TIMEOUT_READ),
                stream=True,
            )
            response.raise_for_status()

            total_length = response.headers.get("Content-Length")
            total = int(total_length) if total_length else None

            downloaded = 0
            desc = display_name[:40]  # truncar para la barra
            tmp_path = str(dest_path) + ".part"

            with open(tmp_path, "wb") as f:
                with tqdm.tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=desc,
                    leave=False,
                    miniters=1,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))

            # Renombrar atómicamente .part → archivo final
            os.rename(tmp_path, str(dest_path))
            return downloaded

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            # Limpiar archivo parcial
            _cleanup_part_file(str(dest_path))
            last_exception = e
            logger.warning(
                "Error de red al descargar (intento %d/%d): %s",
                attempt, api_client.max_retries, e,
            )
            if attempt < api_client.max_retries:
                backoff = BACKOFF_BASE * (BACKOFF_FACTOR ** (attempt - 1))
                time.sleep(backoff)
                continue
            raise DownloadError(
                f"Error de descarga tras {api_client.max_retries} intentos: {e}"
            ) from e

        except requests.exceptions.HTTPError as e:
            # Limpiar archivo parcial
            _cleanup_part_file(str(dest_path))
            last_exception = e
            logger.warning(
                "HTTP error al descargar (intento %d/%d): %s",
                attempt, api_client.max_retries, e,
            )
            if attempt < api_client.max_retries:
                if e.response is not None and e.response.status_code == 429:
                    time.sleep(5.0)
                else:
                    backoff = BACKOFF_BASE * (BACKOFF_FACTOR ** (attempt - 1))
                    time.sleep(backoff)
                continue
            raise DownloadError(
                f"Error HTTP tras {api_client.max_retries} intentos: {e}"
            ) from e

    # Si se agotaron los reintentos
    _cleanup_part_file(str(dest_path))
    raise DownloadError(
        f"No se pudo descargar después de {api_client.max_retries} intentos."
    )


def ensure_download_dir(dir_path: str) -> None:
    """
    Crea el directorio de descarga si no existe (incluyendo padres).

    Args:
        dir_path: Ruta del directorio a crear.
    """
    Path(dir_path).mkdir(parents=True, exist_ok=True)
