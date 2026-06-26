"""
config.py — Gestión de configuración.

Carga el ticket de autenticación de Mercado Público desde variable
de entorno o archivo .env usando python-dotenv.
"""

import os
import hashlib
from pathlib import Path

import dotenv


class TicketNotFoundError(Exception):
    """Se lanza cuando no se encuentra el ticket en ninguna fuente."""
    pass


def load_ticket() -> str:
    """
    Carga MERCADO_PUBLICO_TICKET desde:
    1. os.environ (variables de entorno del sistema)
    2. Archivo .env en el directorio de trabajo (usando python-dotenv)

    La variable de entorno tiene prioridad sobre .env.

    Returns:
        str: el ticket cargado y limpio.

    Raises:
        TicketNotFoundError: si no se encuentra en ninguna fuente.
    """
    # Cargar .env si existe (dotenv no sobrescribe variables ya definidas)
    env_path = Path(".env")
    if env_path.exists():
        dotenv.load_dotenv(env_path)

    ticket = os.environ.get("MERCADO_PUBLICO_TICKET")

    if ticket is None:
        raise TicketNotFoundError(
            "No se encontró MERCADO_PUBLICO_TICKET.\n"
            "Define la variable de entorno o crea un archivo .env "
            "basado en .env.example con tu ticket."
        )

    # Limpiar comillas y espacios
    ticket = ticket.strip().strip("\"'")

    if not ticket:
        raise TicketNotFoundError(
            "MERCADO_PUBLICO_TICKET está vacío.\n"
            "Define un ticket válido en la variable de entorno o en el archivo .env."
        )

    return ticket


def ticket_hash(ticket: str) -> str:
    """
    Genera un hash SHA-256 del ticket para guardar en metadatos
    sin exponer el ticket en texto plano.

    Args:
        ticket: El ticket de autenticación.

    Returns:
        str: Hash SHA-256 con prefijo "sha256:".
    """
    return f"sha256:{hashlib.sha256(ticket.encode('utf-8')).hexdigest()}"
