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
    buscar_licitaciones,
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
    # Helper para extraer campos anidados (ej: "Comprador.NombreOrganismo")
    def _get_nested(d: dict, dotted_key: str, default: Any = None) -> Any:
        parts = dotted_key.split(".")
        current = d
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return default
        return current if current is not None else default

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
    # Organismo está anidado en Comprador.NombreOrganismo
    organismo = (
        _get_nested(data, "Comprador.NombreOrganismo")
        or _get_nested(data, "comprador.nombreOrganismo")
        or data.get("Organismo")
        or data.get("NombreOrganismo")
        or "N/A"
    )
    # Estado: primero el texto, luego el código numérico
    estado = (
        data.get("Estado")
        or data.get("estado")
        or str(data.get("CodigoEstado", ""))
        or "N/A"
    )
    tipo = (
        data.get("Tipo")
        or data.get("tipo")
        or "N/A"
    )
    # Fechas están dentro del sub-dict "Fechas"
    fechas = data.get("Fechas") or {}
    fecha_pub = (
        fechas.get("FechaPublicacion")
        or fechas.get("fechaPublicacion")
        or data.get("FechaPublicacion")
        or "N/A"
    )
    fecha_cierre = (
        fechas.get("FechaCierre")
        or fechas.get("fechaCierre")
        or data.get("FechaCierre")
        or "N/A"
    )
    monto = (
        data.get("MontoEstimado")
        or data.get("montoEstimado")
        or data.get("Monto")
        or data.get("monto")
        or "No especificado"
    )
    # Formatear monto como CLP si es numérico
    if isinstance(monto, (int, float)) and monto > 0:
        monto = f"$ {monto:,.0f}"
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
            print("═" * 60)
            print("  MENÚ PRINCIPAL")
            print("═" * 60)
            print("  1. Buscar licitación por código")
            print("  2. Buscar licitaciones por palabras clave")
            print("  0. Salir")
            print("─" * 60)

            opcion = input("  Opción: ").strip()

            if opcion == "0" or opcion.lower() in ("salir", "exit", "q"):
                break

            if opcion == "1":
                # ── BUSCAR POR CÓDIGO ────────────────────────────────
                print()
                print("─" * 60)
                codigo = get_licitacion_code()
                if codigo is None:
                    continue

                print(f"Buscando licitación: {codigo} ...")

                try:
                    licitacion_data = fetch_licitacion(api_client, codigo, ticket)
                except LicitacionNotFoundError:
                    print(f"\n⚠ Licitación no encontrada: {codigo}")
                    continue
                except InvalidTicketError as e:
                    print(f"\nERROR: {e}")
                    sys.exit(1)
                except APIError as e:
                    print(f"\nERROR: {e}")
                    continue
                except Exception as e:
                    logger.exception("Error inesperado al consultar licitación")
                    print(f"\nERROR inesperado: {e}")
                    continue

                display_licitacion_summary(licitacion_data)
                procesar_licitacion(api_client, licitacion_data, codigo, ticket)

            elif opcion == "2":
                # ── BUSCAR POR PALABRAS CLAVE ─────────────────────────
                print()
                print("─" * 60)
                print("  Búsqueda por palabras clave")
                print("  Ingresa términos separados por comas (ej: telemetria, iot, monitoreo)")
                print("  Deja vacío para listar TODAS las licitaciones vigentes")
                print("─" * 60)
                entrada = input("  Términos: ").strip()

                terminos = None
                if entrada:
                    terminos = [t.strip() for t in entrada.split(",") if t.strip()]

                print(f"\n  Buscando licitaciones vigentes...")
                if terminos:
                    print(f"  Términos: {', '.join(terminos)}")

                try:
                    resultados = buscar_licitaciones(
                        api_client, ticket, terminos=terminos, solo_vigentes=True
                    )
                except APIError as e:
                    print(f"\nERROR: {e}")
                    continue
                except Exception as e:
                    logger.exception("Error en la búsqueda")
                    print(f"\nERROR inesperado: {e}")
                    continue

                if not resultados:
                    print("\n  No se encontraron licitaciones vigentes con esos términos.")
                    continue

                print(f"\n  Se encontraron {len(resultados)} licitación(es):")
                print("─" * 60)

                # Mostrar resultados numerados
                for i, item in enumerate(resultados, 1):
                    cod = item.get("CodigoExterno", "?")
                    nom = item.get("Nombre", "Sin nombre")[:70]
                    print(f"  {i:3d}. [{cod}] {nom}")

                print("─" * 60)
                print("  0. Volver al menú principal")

                seleccion = input(f"\n  Selecciona una licitación (1-{len(resultados)}): ").strip()

                if seleccion == "0" or not seleccion:
                    continue

                try:
                    idx = int(seleccion) - 1
                    if idx < 0 or idx >= len(resultados):
                        print("  Número inválido.")
                        continue
                    item_seleccionado = resultados[idx]
                    codigo = item_seleccionado.get("CodigoExterno", "")
                    if not codigo:
                        print("  Error: licitación sin código.")
                        continue

                    # Obtener datos completos (el listado solo trae campos básicos)
                    print(f"\n  Obteniendo detalles de {codigo} ...")
                    licitacion_data = fetch_licitacion(api_client, codigo, ticket)
                    display_licitacion_summary(licitacion_data)
                    procesar_licitacion(api_client, licitacion_data, codigo, ticket)

                except (ValueError, IndexError):
                    print("  Número inválido.")
                    continue
                except LicitacionNotFoundError:
                    print(f"\n⚠ Licitación no encontrada: {codigo}")
                    continue
                except APIError as e:
                    print(f"\nERROR: {e}")
                    continue

            else:
                print("  Opción inválida. Intenta 1, 2 o 0.")

    except KeyboardInterrupt:
        print("\n\nOperación interrumpida por el usuario.")
    except Exception as e:
        logger.exception("Error inesperado")
        print(f"\nERROR inesperado: {e}")
    finally:
        api_client.close()
        logger.info("Programa finalizado.")


def procesar_licitacion(
    api_client: APIClient,
    licitacion_data: dict[str, Any],
    codigo: str,
    ticket: str,
) -> None:
    """
    Procesa una licitación: consulta archivos y ofrece descarga.

    Args:
        api_client: Cliente API.
        licitacion_data: Datos de la licitación.
        codigo: Código de la licitación.
        ticket: Ticket de autenticación.
    """
    from downloader import download_all_files, display_download_summary
    from metadata import save_metadata
    from utils import sanitize_filename

    # ── 1. Confirmar descarga ────────────────────────────────────
    if not ask_yes_no("¿Descargar documentos?", default=True):
        return

    # ── 2. Pausa de cortesía antes de consultar archivos ─────────
    logger.info("Consultando documentos asociados...")
    time.sleep(random.uniform(1.0, 2.0))

    # ── 3. Consultar archivos ────────────────────────────────────
    try:
        archivos_data = fetch_archivos(api_client, codigo, ticket, licitacion_data)
    except InvalidTicketError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except APIError as e:
        print(f"\nERROR: {e}")
        return
    except Exception as e:
        logger.exception("Error inesperado al consultar archivos")
        print(f"\nERROR inesperado: {e}")
        return

    if not archivos_data:
        print("\n⚠ No se encontraron documentos descargables vía API.")
        print("  Los documentos (bases, anexos, etc.) pueden estar disponibles")
        print(f"  en la página web de Mercado Público:")
        print(f"  https://www.mercadopublico.cl/Procurement/Modules/RFB/Details.aspx?q={codigo}")
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
        return

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

    # ── 4. Preparar directorio de descarga ───────────────────────
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
            return

    # Crear directorio
    download_dir.mkdir(parents=True, exist_ok=True)

    # ── 5. Descargar archivos ────────────────────────────────────
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

    # ── 6. Guardar metadatos ─────────────────────────────────────
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

    # ── 7. Mostrar resumen final ─────────────────────────────────
    display_download_summary(results)

    if results:
        print(f"  Ruta: {download_dir.resolve()}/")
    print()


if __name__ == "__main__":
    main()
