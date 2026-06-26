#!/usr/bin/env python3
"""
main.py — Punto de entrada e interfaz interactiva.

Orquesta el flujo completo:
1. Carga ticket → 2. Bucle interactivo → 3. Consulta licitación
→ 4. Consulta archivos → 5. Descarga → 6. Guarda metadatos → 7. Repite.
"""

import logging
import random
import sys
import time
from pathlib import Path
from typing import Any, Optional

from config import load_ticket, TicketNotFoundError
from api_client import APIClient, APIError, HTTP_TIMEOUT_READ, MAX_RETRIES
from mercado_publico import (
    fetch_licitacion,
    fetch_archivos,
    LicitacionNotFoundError,
    InvalidTicketError,
    BASE_URL,
)
from downloader import download_all_files, DownloadResult
from metadata import save_metadata
from utils import setup_logging, sanitize_filename

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
DEFAULT_DOWNLOAD_DIR = "descargas"
MAX_CODE_INPUT_RETRIES = 3


# ---------------------------------------------------------------------------
# Funciones de interfaz
# ---------------------------------------------------------------------------
def print_banner() -> None:
    """Muestra banner ASCII de bienvenida."""
    banner = r"""
╔══════════════════════════════════════════════════════════╗
║       Mercado Público — Buscador y Descargador          ║
║         de Licitaciones y Documentos                    ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def ask_yes_no(question: str, default: bool = True) -> bool:
    """
    Pregunta sí/no con valor por defecto.

    Args:
        question: Texto de la pregunta.
        default: Valor por defecto (True = Sí, False = No).

    Returns:
        bool: True si la respuesta es afirmativa, False en caso contrario.
    """
    if default:
        prompt = f"{question} [S/n]: "
    else:
        prompt = f"{question} [s/N]: "

    while True:
        try:
            answer = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default

        if not answer:
            return default

        if answer in ("s", "si", "sí", "y", "yes"):
            return True
        if answer in ("n", "no", "not", "nop"):
            return False

        print("Por favor responde 's' o 'n'.")


def display_licitacion_summary(data: dict[str, Any]) -> None:
    """
    Muestra resumen formateado de la licitación en consola.

    Args:
        data: Dict con datos de la licitación.
    """
    # Extraer campos de forma flexible
    codigo = (
        data.get("CodigoExterno")
        or data.get("codigoExterno")
        or data.get("Codigo")
        or data.get("codigo")
        or "N/A"
    )
    nombre = (
        data.get("Nombre")
        or data.get("nombre")
        or "Sin nombre"
    )
    organismo = (
        data.get("Organismo")
        or data.get("NombreOrganismo")
        or data.get("organismo")
        or data.get("nombreOrganismo")
        or "N/A"
    )
    estado = (
        data.get("CodigoEstado")
        or data.get("codigoEstado")
        or data.get("Estado")
        or data.get("estado")
        or "N/A"
    )
    tipo = (
        data.get("Tipo")
        or data.get("tipo")
        or "N/A"
    )
    fecha_pub = (
        data.get("FechaPublicacion")
        or data.get("fechaPublicacion")
        or "N/A"
    )
    fecha_cierre = (
        data.get("FechaCierre")
        or data.get("fechaCierre")
        or "N/A"
    )
    monto = (
        data.get("MontoEstimado")
        or data.get("montoEstimado")
        or data.get("Monto")
        or data.get("monto")
        or "No especificado"
    )
    descripcion = (
        data.get("Descripcion")
        or data.get("descripcion")
        or ""
    )

    print()
    print("─" * 60)
    print(f"  Código          : {codigo}")
    print(f"  Nombre          : {nombre}")
    print(f"  Organismo       : {organismo}")
    print(f"  Estado          : {estado}")
    print(f"  Tipo            : {tipo}")
    print(f"  Publicación     : {fecha_pub}")
    print(f"  Cierre          : {fecha_cierre}")
    print(f"  Monto estimado  : {monto}")

    if descripcion:
        # Truncar descripción larga
        desc_short = descripcion[:200]
        if len(descripcion) > 200:
            desc_short += "..."
        print(f"  Descripción     : {desc_short}")

    print("─" * 60)
    print()


def display_download_summary(results: list[DownloadResult]) -> None:
    """
    Muestra resumen de descargas: exitosas, fallidas, saltadas.

    Args:
        results: Lista de resultados de descarga.
    """
    total = len(results)
    successful = sum(1 for r in results if r.success and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    failed = sum(1 for r in results if not r.success)

    print()
    print("─" * 60)
    print(f"  Archivos procesados : {total}")
    print(f"  Descargados         : {successful}")
    print(f"  Saltados (existentes): {skipped}")
    print(f"  Fallidos            : {failed}")

    if failed > 0:
        print()
        print("  Archivos con error:")
        for r in results:
            if not r.success:
                print(f"    • {r.filename}: {r.error_message}")
    print("─" * 60)
    print()


def get_licitacion_code() -> Optional[str]:
    """
    Solicita al usuario un código de licitación.

    Returns:
        str: Código sanitizado, o None si el usuario cancela.

    Raises:
        SystemExit: si se agotan los intentos.
    """
    for attempt in range(1, MAX_CODE_INPUT_RETRIES + 1):
        try:
            raw = input("Código de licitación: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("Operación cancelada.")
            return None

        if not raw:
            remaining = MAX_CODE_INPUT_RETRIES - attempt
            if remaining > 0:
                print(
                    f"El código no puede estar vacío. "
                    f"Intentos restantes: {remaining}"
                )
            else:
                print("Demasiados intentos fallidos. Saliendo.")
                return None
            continue

        # Sanitizar: normalizar guiones, quitar espacios
        codigo = raw.strip().replace("—", "-").replace("–", "-").replace("−", "-")
        # Múltiples guiones consecutivos → uno solo
        while "--" in codigo:
            codigo = codigo.replace("--", "-")

        # Validar contra path traversal
        if "/" in codigo or "\\" in codigo or ".." in codigo:
            print(
                "El código contiene caracteres no válidos "
                "(/, \\, ..). Intenta de nuevo."
            )
            remaining = MAX_CODE_INPUT_RETRIES - attempt
            if remaining > 0:
                print(f"Intentos restantes: {remaining}")
            else:
                print("Demasiados intentos fallidos. Saliendo.")
                return None
            continue

        return codigo

    return None


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Punto de entrada principal.

    Orquesta el flujo completo de búsqueda, descarga y guardado de metadatos.
    """
    # Configurar logging
    log_dir = Path(DEFAULT_DOWNLOAD_DIR)
    setup_logging(log_dir)
    logger.info("Iniciando Mercado Público Downloader")

    print_banner()

    # ── 1. Cargar ticket ──────────────────────────────────────────────
    try:
        ticket = load_ticket()
        logger.info("Ticket cargado correctamente")
    except TicketNotFoundError as e:
        print(f"\nERROR: {e}")
        print(
            "\nCrea un archivo .env basado en .env.example con tu ticket, "
            "o exporta la variable de entorno MERCADO_PUBLICO_TICKET."
        )
        sys.exit(1)

    # ── 2. Inicializar cliente API ────────────────────────────────────
    api_client = APIClient(
        base_url=BASE_URL,
        timeout=HTTP_TIMEOUT_READ,
        max_retries=MAX_RETRIES,
    )

    # ── 3. Bucle interactivo ──────────────────────────────────────────
    try:
        while True:
            print()
            print("─" * 60)

            # Pedir código de licitación
            codigo = get_licitacion_code()
            if codigo is None:
                break

            print(f"Buscando licitación: {codigo} ...")

            # ── 4. Consultar licitación ────────────────────────────────
            try:
                licitacion_data = fetch_licitacion(api_client, codigo, ticket)
            except LicitacionNotFoundError:
                print(f"\n⚠ Licitación no encontrada: {codigo}")
                if not ask_yes_no("¿Buscar otra licitación?", default=True):
                    break
                continue
            except InvalidTicketError as e:
                print(f"\nERROR: {e}")
                sys.exit(1)
            except APIError as e:
                print(f"\nERROR: {e}")
                if not ask_yes_no("¿Intentar con otro código?", default=True):
                    break
                continue
            except Exception as e:
                logger.exception("Error inesperado al consultar licitación")
                print(f"\nERROR inesperado: {e}")
                if not ask_yes_no("¿Intentar con otro código?", default=True):
                    break
                continue

            # ── 5. Mostrar resumen ────────────────────────────────────
            display_licitacion_summary(licitacion_data)

            # ── 6. Confirmar descarga ─────────────────────────────────
            if not ask_yes_no("¿Descargar documentos?", default=True):
                if not ask_yes_no("¿Buscar otra licitación?", default=True):
                    break
                continue

            # ── 7. Pausa de cortesía antes de consultar archivos ──────
            logger.info("Consultando documentos asociados...")
            time.sleep(random.uniform(1.0, 2.0))

            # ── 8. Consultar archivos ─────────────────────────────────
            try:
                archivos_data = fetch_archivos(api_client, codigo, ticket)
            except InvalidTicketError as e:
                print(f"\nERROR: {e}")
                sys.exit(1)
            except APIError as e:
                print(f"\nERROR: {e}")
                if not ask_yes_no("¿Intentar con otro código?", default=True):
                    break
                continue
            except Exception as e:
                logger.exception("Error inesperado al consultar archivos")
                print(f"\nERROR inesperado: {e}")
                if not ask_yes_no("¿Intentar con otro código?", default=True):
                    break
                continue

            if not archivos_data:
                print("\nEsta licitación no tiene documentos asociados.")
                # Guardar metadata igual
                download_dir = Path(DEFAULT_DOWNLOAD_DIR) / sanitize_filename(codigo)
                download_dir.mkdir(parents=True, exist_ok=True)
                save_metadata(
                    licitacion_data=licitacion_data,
                    archivos_data=[],
                    download_results=[],
                    download_dir=str(download_dir),
                    codigo=codigo,
                    ticket=ticket,
                )
                print(f"Metadatos guardados en: {download_dir / 'metadata.json'}")
                if not ask_yes_no("¿Buscar otra licitación?", default=True):
                    break
                continue

            # Mostrar archivos encontrados
            print(f"\nSe encontraron {len(archivos_data)} documento(s):")
            for i, archivo in enumerate(archivos_data, 1):
                nombre = (
                    archivo.get("Nombre")
                    or archivo.get("nombre")
                    or archivo.get("name")
                    or f"Documento {i}"
                )
                tipo = archivo.get("Tipo") or archivo.get("Extension") or archivo.get("tipo") or "?"
                size = archivo.get("Tamaño") or archivo.get("Size") or archivo.get("tamaño") or ""
                size_str = f" ({size} bytes)" if size else ""
                print(f"  {i:3d}. {nombre}  [{tipo}]{size_str}")

            # ── 9. Preparar directorio de descarga ────────────────────
            safe_codigo = sanitize_filename(codigo)
            download_dir = Path(DEFAULT_DOWNLOAD_DIR) / safe_codigo

            # Verificar si ya existe
            overwrite = False
            if download_dir.exists():
                print(f"\nLa carpeta ya existe: {download_dir}")
                if ask_yes_no("¿Sobrescribir archivos existentes?", default=False):
                    overwrite = True
                else:
                    print("Descarga cancelada.")
                    if not ask_yes_no("¿Buscar otra licitación?", default=True):
                        break
                    continue

            # Crear directorio
            download_dir.mkdir(parents=True, exist_ok=True)

            # ── 10. Descargar archivos ────────────────────────────────
            print(f"\nDescargando archivos a: {download_dir}/")
            print()

            try:
                results = download_all_files(
                    api_client=api_client,
                    archivos=archivos_data,
                    download_dir=str(download_dir),
                    ticket=ticket,
                    overwrite=overwrite,
                )
            except Exception as e:
                logger.exception("Error durante la descarga de archivos")
                print(f"\nERROR durante la descarga: {e}")
                results = []

            # ── 11. Guardar metadatos ─────────────────────────────────
            try:
                save_metadata(
                    licitacion_data=licitacion_data,
                    archivos_data=archivos_data,
                    download_results=results,
                    download_dir=str(download_dir),
                    codigo=codigo,
                    ticket=ticket,
                )
            except Exception as e:
                logger.exception("Error al guardar metadatos")
                print(f"\nERROR al guardar metadatos: {e}")

            # ── 12. Mostrar resumen final ─────────────────────────────
            display_download_summary(results)

            if results:
                print(f"  Ruta: {download_dir.resolve()}/")
            print()

            # ── 13. Preguntar si continuar ────────────────────────────
            if not ask_yes_no("¿Buscar otra licitación?", default=True):
                break

    except KeyboardInterrupt:
        print("\n\nOperación interrumpida por el usuario.")
    except Exception as e:
        logger.exception("Error inesperado")
        print(f"\nERROR inesperado: {e}")
    finally:
        api_client.close()
        logger.info("Programa finalizado.")


if __name__ == "__main__":
    main()
