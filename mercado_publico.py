"""
mercado_publico.py — Lógica de negocio de la API de Mercado Público.

Interactúa con los endpoints específicos:
- /licitaciones.json  → obtener metadatos de una licitación.
- /licitaciones/{codigo}/Archivos.json → listar documentos asociados.
"""

import logging
from typing import Any, Optional

import requests

from api_client import APIClient, APIError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de endpoints
# ---------------------------------------------------------------------------
BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico"
LICITACIONES_ENDPOINT = "/licitaciones.json"
ARCHIVOS_ENDPOINT = "/licitaciones/{codigo}/Archivos.json"


# ---------------------------------------------------------------------------
# Excepciones específicas
# ---------------------------------------------------------------------------
class LicitacionNotFoundError(APIError):
    """El código de licitación no existe (HTTP 404)."""
    pass


class InvalidTicketError(APIError):
    """El ticket de autenticación es inválido (HTTP 400)."""
    pass


# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------
def fetch_licitacion(
    api_client: APIClient,
    codigo: str,
    ticket: str,
) -> dict[str, Any]:
    """
    Obtiene los metadatos de una licitación desde el endpoint /licitaciones.json.

    Args:
        api_client: Instancia de APIClient.
        codigo: Código de la licitación (ej. "1234567-8-LP24").
        ticket: Ticket de autenticación.

    Returns:
        dict con los datos de la licitación (respuesta completa del endpoint).

    Raises:
        LicitacionNotFoundError: si el código no existe (HTTP 404).
        InvalidTicketError: si el ticket es inválido (HTTP 400).
        APIError: para otros errores HTTP o de red.
    """
    params: dict[str, str] = {
        "codigo": codigo,
        "ticket": ticket,
    }

    try:
        data = api_client.get_json(LICITACIONES_ENDPOINT, params=params)

        # La API puede devolver HTTP 203 con error en el cuerpo JSON
        # ej: {"Codigo": 203, "Mensaje": "Ticket no válido."}
        # Detectamos estos errores mirando el contenido del JSON.
        if isinstance(data, dict) and "Mensaje" in data and "Codigo" in data:
            error_msg = data["Mensaje"]
            error_code = data["Codigo"]
            if "ticket" in error_msg.lower():
                raise InvalidTicketError(
                    f"Ticket inválido (código {error_code}): {error_msg}\n"
                    "Verifica tu MERCADO_PUBLICO_TICKET en el archivo .env"
                )
            elif "no encontrad" in error_msg.lower() or "not found" in error_msg.lower():
                raise LicitacionNotFoundError(
                    f"Licitación no encontrada (código {error_code}): {codigo}"
                )
            else:
                raise APIError(
                    f"Error de API (código {error_code}): {error_msg}"
                )

        # La API devuelve los datos dentro de Listado[0]
        # Estructura: {"Cantidad": 1, "Listado": [ { ... datos licitación ... } ]}
        if isinstance(data, dict) and "Listado" in data:
            listado = data["Listado"]
            if isinstance(listado, list) and len(listado) > 0:
                return listado[0]  # extraer la licitación del listado
            elif isinstance(listado, list) and len(listado) == 0:
                raise LicitacionNotFoundError(
                    f"Licitación no encontrada (Listado vacío): {codigo}"
                )

        return data
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        if status_code == 404:
            raise LicitacionNotFoundError(
                f"Licitación no encontrada (HTTP 404): {codigo}"
            ) from e
        elif status_code == 400:
            raise InvalidTicketError(
                "Ticket inválido (HTTP 400). Verifica tu MERCADO_PUBLICO_TICKET."
            ) from e
        else:
            raise APIError(
                f"Error HTTP {status_code} al consultar la licitación: {e}"
            ) from e


def fetch_archivos(
    api_client: APIClient,
    codigo: str,
    ticket: str,
) -> list[dict[str, Any]]:
    """
    Obtiene la lista de archivos/documentos asociados a una licitación.

    Args:
        api_client: Instancia de APIClient.
        codigo: Código de la licitación.
        ticket: Ticket de autenticación.

    Returns:
        list[dict]: Lista de documentos con sus metadatos.
        Puede ser lista vacía si no hay documentos.

    Raises:
        APIError: para errores HTTP o de red.
    """
    endpoint = ARCHIVOS_ENDPOINT.format(codigo=codigo)
    params: dict[str, str] = {
        "ticket": ticket,
    }

    try:
        data = api_client.get_json(endpoint, params=params)

        # Verificar si la API devolvió un error en el cuerpo JSON
        if isinstance(data, dict) and "Mensaje" in data and "Codigo" in data:
            error_msg = data["Mensaje"]
            error_code = data["Codigo"]
            if "ticket" in error_msg.lower():
                raise InvalidTicketError(
                    f"Ticket inválido (código {error_code}): {error_msg}\n"
                    "Verifica tu MERCADO_PUBLICO_TICKET en el archivo .env"
                )
            else:
                logger.warning(
                    "Error de API al consultar archivos (código %d): %s",
                    error_code, error_msg,
                )
                return []

        # La respuesta puede tener diferentes formas.
        # Intentamos extraer la lista de archivos de forma flexible.
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # Puede venir en "Archivos", "Documentos", "Listado", o ser el dict mismo
            for key in ("Archivos", "Documentos", "Listado", "data", "Data"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Si no encontramos lista, asumimos que es un único elemento
            # o un dict sin lista: devolvemos [data] si tiene Nombre/URL
            if "Nombre" in data or "URL" in data or "Enlace" in data:
                return [data]

        # Si llegamos aquí, la estructura no es la esperada
        logger.warning(
            "Estructura inesperada en la respuesta de Archivos: %s",
            type(data).__name__,
        )
        return []

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        if status_code == 400:
            raise InvalidTicketError(
                "Ticket inválido (HTTP 400). Verifica tu MERCADO_PUBLICO_TICKET."
            ) from e
        elif status_code == 404:
            # No se encontraron archivos para esta licitación
            logger.info("No se encontraron archivos para la licitación %s", codigo)
            return []
        else:
            raise APIError(
                f"Error HTTP {status_code} al consultar archivos: {e}"
            ) from e


def build_download_url(
    archivo: dict[str, Any],
    ticket: str,
) -> Optional[str]:
    """
    Construye la URL de descarga para un archivo.

    Busca el campo URL/Enlace/Href en el dict del archivo y,
    si es necesario, añade el ticket como parámetro.

    Args:
        archivo: Dict con metadatos del archivo.
        ticket: Ticket de autenticación.

    Returns:
        str: URL de descarga, o None si no se encuentra.
    """
    url = archivo.get("URL") or archivo.get("Enlace") or archivo.get("Href") or archivo.get("url")

    if not url:
        return None

    url = str(url)

    # Si la URL no contiene ticket y parece necesitarlo, lo añadimos
    if "ticket=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}ticket={ticket}"

    return url
