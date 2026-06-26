"""
api_client.py — Cliente HTTP genérico con retry, rate-limiting y streaming.

Proporciona:
- RateLimiter: control de tasa con jitter aleatorio.
- APIClient: sesión persistente con reintentos automáticos y backoff exponencial.
"""

import random
import time
import logging
from typing import Any, Optional

import requests
from requests import Response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
HTTP_TIMEOUT_CONNECT = 10       # segundos
HTTP_TIMEOUT_READ = 30          # segundos
MAX_RETRIES = 4
BACKOFF_BASE = 1.0              # segundos
BACKOFF_FACTOR = 2.0

RATE_LIMIT_MIN_WAIT = 1.0       # segundos
RATE_LIMIT_MAX_WAIT = 2.0       # segundos


# ---------------------------------------------------------------------------
# Excepciones personalizadas
# ---------------------------------------------------------------------------
class DownloadError(Exception):
    """Error durante la descarga de un archivo."""
    pass


class APIError(Exception):
    """Error general de la API."""
    pass


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """
    Controla la tasa de peticiones con una pausa mínima entre llamadas.
    Usa jitter aleatorio para evitar comportamiento de bot.
    """

    def __init__(self, min_wait: float = 1.0, max_wait: float = 2.0) -> None:
        """
        Args:
            min_wait: Tiempo mínimo de espera entre peticiones (segundos).
            max_wait: Tiempo máximo de espera entre peticiones (segundos).
        """
        self.min_wait = min_wait
        self.max_wait = max_wait
        self._last_call: float = 0.0

    def wait(self) -> None:
        """Espera el tiempo necesario desde la última llamada más un jitter aleatorio."""
        now = time.monotonic()
        elapsed = now - self._last_call

        if self._last_call > 0 and elapsed < self.min_wait:
            sleep_time = self.min_wait - elapsed + random.uniform(0, self.max_wait - self.min_wait)
            logger.debug("RateLimiter: esperando %.2f segundos (mínimo)", sleep_time)
            time.sleep(sleep_time)
            self._last_call = time.monotonic()
            return

        jitter = random.uniform(self.min_wait, self.max_wait)
        total_wait = jitter

        if self._last_call > 0:
            sleep_time = max(0.0, total_wait - elapsed)
        else:
            sleep_time = 0.0  # primera llamada no espera

        if sleep_time > 0:
            logger.debug("RateLimiter: esperando %.2f segundos", sleep_time)
            time.sleep(sleep_time)

        self._last_call = time.monotonic()

    def reset(self) -> None:
        """Resetea el temporizador."""
        self._last_call = 0.0


# ---------------------------------------------------------------------------
# APIClient
# ---------------------------------------------------------------------------
class APIClient:
    """
    Cliente HTTP con sesión persistente, retry automático y rate limiting.
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = HTTP_TIMEOUT_READ,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """
        Args:
            base_url: URL base para peticiones (opcional).
            timeout: Timeout de lectura en segundos.
            max_retries: Número máximo de reintentos.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MercadoPublicoDownloader/1.0",
            "Accept": "application/json",
        })

        self.rate_limiter = RateLimiter(
            min_wait=RATE_LIMIT_MIN_WAIT,
            max_wait=RATE_LIMIT_MAX_WAIT,
        )

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, str]] = None,
        stream: bool = False,
    ) -> Response:
        """
        Realiza una petición HTTP con reintentos y backoff exponencial.

        Args:
            method: Método HTTP (GET, POST, etc.).
            url: URL completa o relativa (si base_url está configurada).
            params: Parámetros de query string.
            stream: Si es True, usa streaming para la respuesta.

        Returns:
            Response: Objeto respuesta de requests.

        Raises:
            ConnectionError: Si falla la conexión después de reintentos.
            requests.exceptions.Timeout: Si se agota el timeout.
            requests.exceptions.HTTPError: Para errores HTTP 4xx/5xx no recuperables.
        """
        if self.base_url and not url.startswith(("http://", "https://")):
            url = f"{self.base_url}{url}"

        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Rate limiting ANTES de la petición (excepto en reintentos)
                if attempt == 1:
                    self.rate_limiter.wait()
                else:
                    # En reintentos, espera backoff en lugar de rate limiting normal
                    backoff = BACKOFF_BASE * (BACKOFF_FACTOR ** (attempt - 2))
                    logger.info(
                        "Reintento %d/%d, esperando %.1f segundos...",
                        attempt, self.max_retries, backoff,
                    )
                    time.sleep(backoff)
                    self.rate_limiter.reset()

                safe_params = {k: ("***" if k == "ticket" else v) for k, v in (params or {}).items()}
                logger.debug("HTTP %s %s params=%s", method, url, safe_params)
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=(HTTP_TIMEOUT_CONNECT, self.timeout),
                    stream=stream,
                )

                # Si es 5xx, reintentamos
                if response.status_code >= 500:
                    logger.warning(
                        "Error HTTP %d en el intento %d/%d",
                        response.status_code, attempt, self.max_retries,
                    )
                    if attempt < self.max_retries:
                        continue
                    response.raise_for_status()

                # 4xx: no reintentamos (excepto 429)
                if response.status_code == 429:
                    logger.warning("Rate limit (429), reintentando...")
                    if attempt < self.max_retries:
                        time.sleep(5.0)  # espera extra para rate limit
                        continue
                    response.raise_for_status()

                if response.status_code >= 400:
                    response.raise_for_status()

                return response

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                last_exception = e
                logger.warning(
                    "Error de conexión (intento %d/%d): %s",
                    attempt, self.max_retries, e,
                )
                if attempt < self.max_retries:
                    continue
                raise

            except requests.exceptions.HTTPError as e:
                last_exception = e
                # Para 400 y 404, no reintentamos
                if e.response is not None and e.response.status_code in (400, 404):
                    raise
                # Para otros 4xx, reintentamos solo si no es el último intento
                if attempt < self.max_retries:
                    continue
                raise

        # Si agotamos reintentos, lanzamos la última excepción
        if last_exception:
            raise last_exception

        # No debería llegar aquí, pero por si acaso
        raise APIError("Número máximo de reintentos alcanzado sin éxito.")

    def get_json(
        self,
        endpoint: str,
        params: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Realiza GET y devuelve JSON parseado.

        Args:
            endpoint: Endpoint relativo (ej. "/licitaciones.json").
            params: Parámetros de query string.

        Returns:
            dict con la respuesta JSON.

        Raises:
            APIError: Si la respuesta no es JSON válido.
            requests.exceptions.HTTPError: Para errores HTTP.
            ConnectionError: Para errores de red.
        """
        response = self._request("GET", endpoint, params=params, stream=False)

        try:
            data: dict[str, Any] = response.json()
        except ValueError as e:
            raise APIError(
                f"La API devolvió datos no válidos (no es JSON): {e}"
            ) from e

        return data


    def close(self) -> None:
        """Cierra la sesión HTTP."""
        self.session.close()
