# Documentacion Tecnica -- Mercado Publico Downloader

Guia para desarrolladores que deseen comprender, modificar o extender el
programa.

## Indice

1. [Arquitectura del sistema](#arquitectura-del-sistema)
2. [Descripcion de modulos](#descripcion-de-modulos)
3. [Flujo de datos](#flujo-de-datos)
4. [Decisiones tecnicas](#decisiones-tecnicas)
5. [Guia de modificacion y extension](#guia-de-modificacion-y-extension)
6. [API de funciones principales](#api-de-funciones-principales)
7. [Pruebas](#pruebas)
8. [Taxonomia de errores](#taxonomia-de-errores)
9. [Modelo de datos](#modelo-de-datos)
10. [Convenciones de codigo](#convenciones-de-codigo)
11. [Recetas de extension](#recetas-de-extension)
12. [Empaquetado y despliegue](#empaquetado-y-despliegue)
13. [Deuda tecnica y roadmap](#deuda-tecnica-y-roadmap)
14. [Checklist de revision](#checklist-de-revision)

---

## Arquitectura del sistema

El programa sigue una arquitectura modular con responsabilidad unica por modulo.
Cada archivo `.py` encapsula una capa especifica de la aplicacion:

```
main.py  -->  config.py (ticket)
         -->  api_client.py (HTTP con retry/rate-limit)
         -->  mercado_publico.py (logica de negocio: endpoints)
         -->  downloader.py (descarga archivos con progreso)
         -->  metadata.py (serializacion JSON)
         -->  utils.py (sanitizacion, logging, helpers)
```

### Capas de la arquitectura

| Capa | Modulo | Responsabilidad |
|------|--------|-----------------|
| Entrada / Interfaz | `main.py` | CLI interactiva, orquestacion del flujo |
| Configuracion | `config.py` | Carga y validacion del ticket de autenticacion |
| Transporte HTTP | `api_client.py` | Peticiones HTTP con reintentos, backoff, rate limiting |
| Logica de negocio | `mercado_publico.py` | Endpoints especificos de la API de Mercado Publico |
| Descarga | `downloader.py` | Descarga streaming con barra de progreso y reintentos |
| Persistencia | `metadata.py` | Serializacion JSON de metadatos |
| Soporte | `utils.py` | Sanitizacion de nombres, logging, colisiones |

---

## Descripcion de modulos

### main.py -- Punto de entrada e interfaz interactiva

**Responsabilidad**: Inicializar el sistema y ejecutar el bucle interactivo
principal.

**Flujo**:
1. Configura el logging (consola nivel INFO, archivo `descargas/downloader.log`
   nivel DEBUG).
2. Muestra el banner ASCII de bienvenida.
3. Carga el ticket via `config.load_ticket()`.
4. Inicializa el `APIClient`.
5. Entra en un bucle que se repite hasta que el usuario decida salir:
   - Solicita codigo de licitacion (`get_licitacion_code()`).
   - Busca la licitacion (`mercado_publico.fetch_licitacion()`).
   - Muestra resumen (`display_licitacion_summary()`).
   - Pregunta confirmacion de descarga (`ask_yes_no()`).
   - Consulta archivos (`mercado_publico.fetch_archivos()`).
   - Lista archivos encontrados.
   - Prepara directorio de descarga, manejando colision de carpeta.
   - Descarga archivos (`downloader.download_all_files()`).
   - Guarda metadatos (`metadata.save_metadata()`).
   - Muestra resumen de descargas (`display_download_summary()`).
   - Pregunta si desea buscar otra licitacion.
6. Captura `KeyboardInterrupt` para salida limpia.
7. Cierra la sesion HTTP en `finally`.

**Funciones publicas**:

- `print_banner()` -- Muestra el banner ASCII.
- `ask_yes_no(question, default)` -- Pregunta si/no con valor por defecto.
  Soporta "s", "si", "y", "yes" para afirmacion y "n", "no", "not" para
  negacion.
- `display_licitacion_summary(data)` -- Formatea y muestra datos de licitacion.
  Busca campos con nombres flexibles (soporta variantes de mayusculas/minusculas
  de los nombres de campo de la API).
- `display_download_summary(results)` -- Resumen de descargas: exitosas, saltadas
  y fallidas.
- `get_licitacion_code()` -- Solicita codigo al usuario con validacion de path
  traversal, normalizacion de guiones y maximo 3 intentos.
- `main()` -- Punto de entrada. Orquesta todo el flujo.

### config.py -- Gestion de configuracion

**Responsabilidad**: Cargar el ticket de autenticacion y generar su hash.

**Funciones**:

- `load_ticket() -> str` -- Carga `MERCADO_PUBLICO_TICKET` con la siguiente
  prioridad:
  1. Variable de entorno del sistema (`os.environ`).
  2. Archivo `.env` en el directorio de trabajo (via `python-dotenv`).
  
  Limpia comillas y espacios del ticket. Lanza `TicketNotFoundError` si no se
  encuentra o si esta vacio.

- `ticket_hash(ticket) -> str` -- Genera un hash SHA-256 del ticket con prefijo
  `"sha256:"`. Se usa en `metadata.py` para guardar una referencia del ticket
  sin exponerlo en texto plano.

**Excepciones**:

- `TicketNotFoundError` -- El ticket no esta configurado en ninguna fuente.

### api_client.py -- Cliente HTTP generico

**Responsabilidad**: Abstraer las peticiones HTTP con control de tasa,
reintentos automaticos y backoff exponencial.

**Clases**:

- `RateLimiter` -- Controla la tasa de peticiones con jitter aleatorio.
  - `__init__(min_wait=1.0, max_wait=2.0)` -- Configura rango de espera.
  - `wait()` -- Duerme el hilo el tiempo necesario para respetar el minimo
    entre peticiones, mas un jitter aleatorio.
  - `reset()` -- Resetea el temporizador interno.

- `APIClient` -- Cliente HTTP con sesion persistente.
  - `__init__(base_url, timeout, max_retries)` -- Configura sesion de requests
    con User-Agent personalizado, timeouts y reintentos.
  - `_request(method, url, params, stream)` -- Nucleo de peticiones HTTP con
    logica de reintentos:
    - Intento 1: aplica rate limiting normal (jitter 1-2s).
    - Reintentos: aplica backoff exponencial (formula: `1 * 2^(attempt-2)`) y
      resetea el rate limiter.
    - HTTP 5xx: reintenta hasta agotar intentos.
    - HTTP 429 (rate limit): reintenta con espera extra de 5s.
    - HTTP 400/404: no reintenta, lanza inmediatamente.
    - Enmascara el ticket en los logs DEBUG reemplazandolo por `"***"`.
  - `get_json(endpoint, params)` -- Realiza GET y parsea JSON. Lanza `APIError`
    si la respuesta no es JSON valido.
  - `close()` -- Cierra la sesion HTTP.

**Constantes**:

| Constante               | Valor | Descripcion                          |
|-------------------------|-------|--------------------------------------|
| `HTTP_TIMEOUT_CONNECT`  | 10    | Timeout de conexion (segundos)       |
| `HTTP_TIMEOUT_READ`     | 30    | Timeout de lectura (segundos)        |
| `MAX_RETRIES`           | 4     | Intentos totales (1 inicial + 3 reintentos) |
| `BACKOFF_BASE`          | 1.0   | Base de backoff exponencial          |
| `BACKOFF_FACTOR`        | 2.0   | Factor de backoff exponencial        |
| `RATE_LIMIT_MIN_WAIT`   | 1.0   | Espera minima entre peticiones       |
| `RATE_LIMIT_MAX_WAIT`   | 2.0   | Espera maxima entre peticiones       |

**Excepciones**:

- `APIError` -- Error general de la API (JSON malformado, HTTP error, etc.).
- `DownloadError` -- Error durante la descarga de un archivo.

### mercado_publico.py -- Logica de negocio de la API

**Responsabilidad**: Interactuar con los endpoints especificos de la API de
Mercado Publico y mapear respuestas HTTP a excepciones semanticas.

**Constantes de endpoints**:

- `BASE_URL = "http://api.mercadopublico.cl/servicios/v1/publico"`
- `LICITACIONES_ENDPOINT = "/licitaciones.json"`
- `ARCHIVOS_ENDPOINT = "/licitaciones/{codigo}/Archivos.json"`

**Funciones**:

- `fetch_licitacion(api_client, codigo, ticket) -> dict` -- Consulta el endpoint
  `/licitaciones.json`. Traduce HTTP 404 a `LicitacionNotFoundError` y HTTP 400
  a `InvalidTicketError`. Retorna la respuesta JSON completa.

- `fetch_archivos(api_client, codigo, ticket) -> list[dict]` -- Consulta el
  endpoint `Archivos.json`. Soporta multiples formatos de respuesta:
  - Si la respuesta es una lista, la retorna directamente.
  - Si es un dict, busca claves como `"Archivos"`, `"Documentos"`, `"Listado"`,
    `"data"` o `"Data"` y extrae la lista interna.
  - Si es un dict con un solo archivo (tiene `"Nombre"` o `"URL"`), lo
    envuelve en una lista.
  - Si no encuentra lista, retorna lista vacia y registra un warning.

- `build_download_url(archivo, ticket) -> Optional[str]` -- Construye la URL de
  descarga a partir de los metadatos del archivo. Busca campos `"URL"`,
  `"Enlace"`, `"Href"`, `"url"`. Si la URL no contiene el parametro `ticket`,
  lo anade automaticamente.

**Excepciones**:

- `LicitacionNotFoundError(APIError)` -- HTTP 404 en el endpoint de licitaciones.
- `InvalidTicketError(APIError)` -- HTTP 400 en cualquier endpoint.

### downloader.py -- Descarga de archivos con progreso

**Responsabilidad**: Gestionar la descarga por lotes de archivos, con barra de
progreso visual (tqdm), manejo de archivos parciales y reintentos individuales.

**Clases**:

- `DownloadResult` (dataclass) -- Representa el resultado de una descarga.
  - `filename: str` -- Nombre del archivo.
  - `success: bool` -- True si la descarga fue exitosa.
  - `path: Optional[str]` -- Ruta local del archivo descargado.
  - `error_message: Optional[str]` -- Mensaje de error si fallo.
  - `size_bytes: Optional[int]` -- Tamano en bytes.
  - `skipped: bool` -- True si se salto por existir previamente.

**Funciones**:

- `download_all_files(api_client, archivos, download_dir, ticket, overwrite,
  progress_callback, min_pause, max_pause) -> list[DownloadResult]` --
  Itera sobre la lista de archivos y para cada uno:
  1. Extrae nombre y URL de los metadatos (con flexibilidad de nombres de
     campo).
  2. Si no tiene URL, registra como fallido y continua.
  3. Sanitiza el nombre con `utils.sanitize_filename()`.
  4. Resuelve colisiones de nombre si `overwrite=False`.
  5. Si el archivo ya existe y `overwrite=False`, lo salta.
  6. Construye la URL de descarga con `mercado_publico.build_download_url()`.
  7. Descarga con `_download_with_progress()`.
  8. Pausa de jitter (1-2s) entre archivos.
  9. Si ocurre `OSError` (ej. disco lleno), detiene todas las descargas
     restantes.

- `_download_with_progress(api_client, url, dest_path, display_name) -> int` --
  Descarga un archivo individual con:
  - Barra de progreso `tqdm` (porcentaje y velocidad si `Content-Length` esta
    presente; bytes acumulados en caso contrario).
  - Archivo temporal `.part` durante la descarga; renombra atomicamente al
    finalizar exitosamente.
  - Reintentos con backoff exponencial para errores de red y HTTP (excepto 4xx
    no recuperables).
  - Limpieza automatica del archivo `.part` en caso de fallo.

- `_cleanup_part_file(dest_path)` -- Elimina el archivo `.part` asociado si
  existe.

- `ensure_download_dir(dir_path)` -- Crea el directorio de descarga con padres
  si no existe.

### metadata.py -- Serializacion y guardado de metadatos JSON

**Responsabilidad**: Construir y persistir el archivo `metadata.json` con toda
la informacion recopilada durante el proceso.

**Funcion**:

- `save_metadata(licitacion_data, archivos_data, download_results, download_dir,
  codigo, ticket) -> str` -- Construye y guarda `metadata.json` con la
  siguiente estructura:

```json
{
  "licitacion": { ... },
  "archivos_count": 3,
  "archivos": [ ... ],
  "descargas": [
    {
      "nombre": "archivo.pdf",
      "url_origen": "http://...",
      "archivo_local": "descargas/.../archivo.pdf",
      "descargado": true,
      "tamano_bytes": 1310720,
      "error": null,
      "saltado": false
    }
  ],
  "fecha_descarga": "2026-06-26T12:00:00+00:00",
  "codigo_licitacion": "1234567-8-LP24",
  "ticket_hash": "sha256:a1b2c3d4..."
}
```

Puntos clave:
- Usa `json.dumps` con `indent=2` y `ensure_ascii=False` para soportar tildes y
  caracteres especiales.
- La fecha se guarda en formato ISO 8601 con timezone UTC.
- El ticket NUNCA se guarda en texto plano; se guarda un hash SHA-256 generado
  por `config.ticket_hash()`.
- Si hay mas archivos en `archivos_data` que en `download_results` (por una
  interrupcion temprana), los archivos no procesados se registran como no
  descargados.

### utils.py -- Utilidades

**Responsabilidad**: Funciones auxiliares de sanitizacion, resolucion de
colisiones y configuracion de logging.

**Funciones**:

- `sanitize_filename(filename) -> str` -- Limpia un nombre de archivo
  reemplazando caracteres invalidos (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`,
  `|`) por `_`. Recorta espacios, elimina multiples espacios consecutivos y
  puntos al final. Si el resultado queda vacio, retorna `"archivo_sin_nombre"`.

- `resolve_filename_collision(download_dir, filename) -> str` -- Resuelve
  colisiones de nombre anadiendo un sufijo numerico antes de la extension:
  `archivo.pdf` -> `archivo_1.pdf` -> `archivo_2.pdf`. Solo modifica el nombre
  si ya existe un archivo con ese nombre en el directorio.

- `setup_logging(log_dir)` -- Configura el sistema de logging con:
  - Handler de consola: nivel INFO con timestamp corto (`HH:MM:SS`).
  - Handler de archivo (opcional): nivel DEBUG con timestamp completo y nombre
    del logger. Guarda en `<log_dir>/downloader.log`.
  - Proteccion contra acumulacion de handlers duplicados.

---

## Flujo de datos

```
[Usuario]
   |-- codigo de licitacion
   v
main.py
   |-- load_ticket()
   |     |
   |     v
   |   config.py  --> MERCADO_PUBLICO_TICKET (env / .env)
   |
   |-- fetch_licitacion(api_client, codigo, ticket)
   |     |
   |     v
   |   mercado_publico.py  --> api_client.get_json()
   |     |                       |
   |     |                       v
   |     |                   [GET /licitaciones.json?codigo=X&ticket=T]
   |     |                       |
   |     |                       v
   |     |                   [JSON licitacion]
   |     |
   |     v
   |   [Resumen en consola] --> display_licitacion_summary()
   |
   |-- fetch_archivos(api_client, codigo, ticket)
   |     |
   |     v
   |   mercado_publico.py  --> api_client.get_json()
   |     |                       |
   |     |                       v
   |     |                   [GET /licitaciones/{X}/Archivos.json?ticket=T]
   |     |                       |
   |     |                       v
   |     |                   [JSON archivos[]]
   |     |
   |     v
   |   [Listado en consola]
   |
   |-- download_all_files(api_client, archivos, dir, ticket)
   |     |
   |     v
   |   downloader.py
   |     |-- build_download_url()        --> URL con ticket
   |     |-- _download_with_progress()   --> archivo .part -> archivo final
   |     |-- (jitter 1-2s entre archivos)
   |     |-- (reintentos individuales)
   |     |
   |     v
   |   [Archivos en descargas/{codigo}/]
   |
   |-- save_metadata()
         |
         v
       metadata.py
         |-- ticket_hash(ticket)         --> hash SHA-256
         |-- json.dump()
         |
         v
       descargas/{codigo}/metadata.json
```

---

## Decisiones tecnicas

### Control de tasa (rate limiting)

La API de Mercado Publico no documenta publicamente sus limites de tasa. Para
actuar de forma conservadora y respetuosa con el servicio, el programa implementa
dos mecanismos:

1. **RateLimiter**: Pausa de 1 a 2 segundos con jitter aleatorio entre cada
   peticion HTTP que no sea un reintento. El jitter evita patrones de bot y
   reduce la probabilidad de activar protecciones anti-abuso.

2. **Pausa entre descargas**: Entre cada descarga de archivo, se aplica una
   pausa adicional de 1 a 2 segundos (jitter), ya que las descargas tambien son
   peticiones HTTP que pueden impactar al servidor.

### Backoff exponencial

Los reintentos usan backoff exponencial con la formula `BASE * FACTOR^(n-1)` o
`BASE * FACTOR^(n-2)` segun el contexto:

- **api_client.py._request()**: Los reintentos ocurren al inicio de cada intento
  (con `attempt` ya incrementado). Formula: `1.0 * 2^(attempt-2)`, produciendo
  1s, 2s, 4s.
- **downloader.py._download_with_progress()**: Los reintentos ocurren dentro del
  bloque `except`, con `attempt` conservando el valor del intento fallido.
  Formula: `1.0 * 2^(attempt-1)`, produciendo tambien 1s, 2s, 4s.

El maximo de reintentos es 3 (4 intentos totales contando el inicial):
`MAX_RETRIES = 4`.

### Seguridad del ticket

1. **Nunca en texto plano en disco**: El archivo `metadata.json` solo guarda un
   hash SHA-256 del ticket, no el ticket en si.

2. **Enmascarado en logs**: El metodo `APIClient._request()` construye un
   diccionario `safe_params` donde el valor del parametro `ticket` se reemplaza
   por `"***"` antes de registrarlo en logs.

3. **Excluido de Git**: El archivo `.env` esta en `.gitignore` para prevenir
   que se suba accidentalmente a repositorios.

4. **Sin hardcoding**: El ticket nunca aparece hardcodeado en el codigo fuente.

### Sanitizacion de nombres de archivo

Dado que los nombres de documentos en Mercado Publico pueden contener caracteres
no validos para sistemas de archivos (ej. `Bases: Anexo/N°1 <final>.pdf`), el
programa sanitiza automaticamente reemplazando `\`, `/`, `:`, `*`, `?`, `"`, `<`,
`>`, `|` por `_`.

### Archivos parciales (.part)

Para evitar archivos corruptos por descargas interrumpidas:
- Durante la descarga, los datos se escriben en `<nombre>.part`.
- Al finalizar exitosamente, el archivo se renombra atomicamente a `<nombre>`.
- Si la descarga falla, el archivo `.part` se elimina.

### Colision de nombres

Si se descargan multiples documentos con el mismo nombre (o si la carpeta ya
contiene archivos de una descarga anterior y `overwrite=False`), se resuelve la
colision anadiendo un sufijo numerico: `archivo.pdf` -> `archivo_1.pdf`.

### Timeouts

Se usa un timeout de conexion de 10 segundos y un timeout de lectura de 30
segundos. Esto permite detectar rapidamente problemas de red sin esperar
indefinidamente, pero tambien da margen suficiente para descargar archivos
grandes en modo streaming.

### Codificacion UTF-8 y caracteres especiales

`metadata.json` se escribe con `ensure_ascii=False` para preservar tildes, enyes
y otros caracteres del espanol presentes en los datos de la API.

---

## Guia de modificacion y extension

### Agregar un nuevo endpoint

1. Agrega la constante del endpoint en `mercado_publico.py`:
   ```python
   NUEVO_ENDPOINT = "/nuevo/recurso.json"
   ```

2. Crea una funcion en `mercado_publico.py` que use `api_client.get_json()`:
   ```python
   def fetch_nuevo_recurso(api_client, ticket, **params):
       params["ticket"] = ticket
       return api_client.get_json(NUEVO_ENDPOINT, params=params)
   ```

3. Integra la llamada en `main.py` dentro del bucle principal.

### Ajustar el rate limiting

Modifica las constantes en `api_client.py`:

```python
RATE_LIMIT_MIN_WAIT = 0.5   # mas rapido
RATE_LIMIT_MAX_WAIT = 1.0   # mas rapido
```

O ajusta las pausas entre descargas en `downloader.py` al llamar a
`download_all_files()` con los parametros `min_pause` y `max_pause`.

### Cambiar el directorio de descarga

Modifica la constante en `main.py`:

```python
DEFAULT_DOWNLOAD_DIR = "mis_descargas"
```

### Agregar soporte para un nuevo campo de la API

Los mapeos de campos estan dispersos en el codigo con logica de fallback
(ej. `data.get("Nombre") or data.get("nombre")`). Para agregar un nuevo campo:

1. En `main.py.display_licitacion_summary()`, agrega la extraccion del campo.
2. En `downloader.py.download_all_files()`, agrega el campo al extraer nombre/URL
   de los archivos.
3. Considera agregar el campo a `metadata.json` si corresponde.

### Agregar soporte para HTTPS

Si la API de Mercado Publico llegara a exponer un endpoint HTTPS, modifica la
constante en `mercado_publico.py`:

```python
BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico"
```

### Cambiar el nivel de logging

El nivel de logging se configura en `utils.py`:
- Consola: `console_handler.setLevel(logging.INFO)`
- Archivo: `file_handler.setLevel(logging.DEBUG)`

Para ver mas detalles en consola, cambia INFO por DEBUG.

---

## API de funciones principales

Esta seccion describe las funciones publicas que pueden ser invocadas desde
otros modulos o desde scripts externos que importen el proyecto como libreria.

### config.py

```python
def load_ticket() -> str
```
Carga el ticket de autenticacion. Lanza `TicketNotFoundError` si no se encuentra.

```python
def ticket_hash(ticket: str) -> str
```
Retorna el hash SHA-256 del ticket con prefijo `"sha256:"`.

### api_client.py

```python
class APIClient:
    def __init__(self, base_url: str = "", timeout: int = 30, max_retries: int = 4)
    def get_json(self, endpoint: str, params: dict | None = None) -> dict[str, Any]
    def close(self) -> None

class RateLimiter:
    def __init__(self, min_wait: float = 1.0, max_wait: float = 2.0)
    def wait(self) -> None
    def reset(self) -> None
```

### mercado_publico.py

```python
def fetch_licitacion(api_client: APIClient, codigo: str, ticket: str) -> dict[str, Any]
def fetch_archivos(api_client: APIClient, codigo: str, ticket: str) -> list[dict[str, Any]]
def build_download_url(archivo: dict[str, Any], ticket: str) -> Optional[str]
```

### downloader.py

```python
@dataclass
class DownloadResult:
    filename: str
    success: bool
    path: Optional[str] = None
    error_message: Optional[str] = None
    size_bytes: Optional[int] = None
    skipped: bool = False

def download_all_files(
    api_client: APIClient,
    archivos: list[dict[str, Any]],
    download_dir: str,
    ticket: str,
    overwrite: bool = False,
    progress_callback: Optional[Callable] = None,
    min_pause: float = 1.0,
    max_pause: float = 2.0,
) -> list[DownloadResult]

def ensure_download_dir(dir_path: str) -> None
```

### metadata.py

```python
def save_metadata(
    licitacion_data: dict[str, Any],
    archivos_data: list[dict[str, Any]],
    download_results: list[DownloadResult],
    download_dir: str,
    codigo: str,
    ticket: str,
) -> str
```

### utils.py

```python
def sanitize_filename(filename: str) -> str
def resolve_filename_collision(download_dir: Path, filename: str) -> str
def setup_logging(log_dir: Optional[Path] = None) -> None
```

---

## Pruebas

El proyecto esta disenado para ser probado con `pytest` mediante mocking de las
respuestas HTTP. El plan de pruebas definido en `PLAN.md` contempla pruebas
funcionales y unitarias.

### Pruebas funcionales manuales

| # | Caso | Resultado esperado |
|---|------|--------------------|
| 1 | Ticket no configurado | Error explicativo. Codigo de salida 1. |
| 2 | Ticket valido, codigo existente | Descarga documentos a `descargas/{codigo}/`, guarda `metadata.json`. |
| 3 | Codigo inexistente | Error 404. Ofrece buscar otra licitacion. |
| 4 | Ticket invalido | Error 400. Codigo de salida 1. |
| 5 | Licitacion sin archivos | Mensaje informativo. Guarda `metadata.json`. |
| 6 | Carpeta ya existe | Pregunta si sobrescribir. |
| 7 | Ctrl+C durante descarga | Salida limpia. |
| 8 | Codigo con caracteres especiales | Sanitizacion correcta. |

### Pruebas unitarias sugeridas

| Modulo | Prueba |
|--------|--------|
| `config.py` | `load_ticket` desde variable de entorno |
| `config.py` | `load_ticket` desde `.env` (mock `load_dotenv`) |
| `config.py` | `TicketNotFoundError` cuando no hay ticket |
| `api_client.py` | `get_json` con respuesta 200 (mock) |
| `api_client.py` | `get_json` con fallo y reintento exitoso |
| `api_client.py` | `get_json` con reintentos agotados |
| `api_client.py` | `RateLimiter.wait` respeta minimo de espera |
| `mercado_publico.py` | `fetch_licitacion` exitosa |
| `mercado_publico.py` | `fetch_licitacion` con 404 |
| `mercado_publico.py` | `fetch_archivos` con lista vacia |
| `downloader.py` | `sanitize_filename` con nombre normal |
| `downloader.py` | `sanitize_filename` con caracteres invalidos |
| `downloader.py` | `sanitize_filename` con nombre que queda vacio |
| `metadata.py` | `save_metadata` crea archivo correctamente |
| `metadata.py` | El ticket no aparece en texto plano en el JSON |
| `metadata.py` | La estructura JSON es la esperada |

---

## Taxonomia de errores

El programa usa excepciones propias para separar los fallos recuperables de los
que obligan a detener la ejecucion. Entender esa cadena es clave para extender
el codigo sin romper el manejo de errores de `main.py`.

| Excepcion | Modulo | Causa | Manejo actual |
|-----------|--------|-------|----------------|
| `TicketNotFoundError` | `config` | No hay variable ni `.env` | Mensaje y `sys.exit(1)` |
| `InvalidTicketError` | `mercado_publico` | HTTP 400 o mensaje con "ticket" | Mensaje y `sys.exit(1)` |
| `LicitacionNotFoundError` | `mercado_publico` | HTTP 404 o `Listado` vacio | Aviso y vuelta al menu |
| `APIError` | `api_client` | Error HTTP/red/JSON no clasificado | Mensaje y continuar |
| `DownloadError` | `api_client` | Fallo de descarga tras reintentos | Se registra por archivo |
| `requests.ConnectionError` | `requests` | Red inaccesible, DNS, proxy | Reintento y luego `APIError` |
| `requests.Timeout` | `requests` | Sin respuesta en 10/30 s | Reintento y luego `APIError` |
| `requests.HTTPError` | `requests` | 4xx/5xx no reintentable | Se traduce a excepcion propia |
| `OSError` | `downloader` | Disco lleno, permisos | Detiene descargas restantes |
| `json.JSONDecodeError` | `main` (monitoreo) | Registro de vistos corrupto | Se reinicia el registro |

### Propagacion

```
requests.exceptions.*
        |
        v
APIClient._request  ->  APIError / HTTPError
        |
        v
mercado_publico     ->  InvalidTicketError / LicitacionNotFoundError / APIError
        |
        v
main.procesar_*     ->  mensaje al usuario, continue o sys.exit(1)
```

Reglas de diseno:

1. **No capturar `Exception` sin registrar.** En `main.py` se usa
   `logger.exception(...)` para conservar la traza en el log.
2. **Los errores de autenticacion son fatales.** No tiene sentido seguir
   consultando con un ticket invalido.
3. **Los errores de una licitacion no son fatales.** El monitoreo debe seguir
   con las demas.
4. **Los errores de un archivo no abortan la licitacion.** Se anotan en
   `DownloadResult` y se continua.
5. **Los errores de E/S si abortan.** Un disco lleno afectaria a todos los
   archivos siguientes.

### Mensajes al usuario

Los mensajes deben explicar la causa y la accion:

- Mal: `Error 400`.
- Bien: `Ticket invalido (HTTP 400). Verifica tu MERCADO_PUBLICO_TICKET.`

Mantener ese criterio al agregar nuevas validaciones.

---

## Modelo de datos

### Licitacion

`fetch_licitacion()` devuelve el **item** interno, no la envoltura:

```
{
  "CodigoExterno": str,
  "Nombre": str,
  "Descripcion": str,
  "CodigoEstado": int,
  "Estado": str,
  "Comprador": {"NombreOrganismo": str, "RutUnidad": str, ...},
  "Fechas": {"FechaPublicacion": str, "FechaCierre": str, ...},
  "MontoEstimado": float | None,
  "Moneda": str,
  "Tipo": str,
  "Adjudicacion": {"UrlActa": str, ...},
  "Items": {"Cantidad": int, "Listado": [...]}
}
```

Los campos pueden faltar. El codigo de presentacion usa `or` en cascada y
`_get_nested()` para tolerar ausencias y variantes de mayusculas.

### Archivo

`fetch_archivos()` devuelve una lista de diccionarios heterogeneos. Las claves
se buscan en este orden:

| Dato | Claves aceptadas |
|------|------------------|
| Nombre | `Nombre`, `nombre`, `name` |
| URL | `URL`, `Enlace`, `Href`, `url`, `enlace` |
| Tipo | `Tipo`, `Extension`, `tipo` |
| Tamano | `Tamaño`, `Size`, `tamaño` |

No asumir una forma unica: la API y el endpoint de archivos no siempre
coinciden. Al agregar un nuevo origen de documentos, devolver el mismo contrato
minimo (`Nombre` + `URL`).

### DownloadResult

```python
@dataclass
class DownloadResult:
    filename: str
    success: bool
    path: Optional[str] = None
    error_message: Optional[str] = None
    size_bytes: Optional[int] = None
    skipped: bool = False
```

Es inmutable en la practica: se crea y se agrega a la lista de resultados. Si
se agregan campos, actualizar `metadata.save_metadata()` y el resumen de
`main.display_download_summary()`.

### metadata.json

```json
{
  "licitacion": {},
  "archivos_count": 0,
  "archivos": [],
  "descargas": [
    {
      "nombre": "",
      "url_origen": "",
      "archivo_local": null,
      "descargado": false,
      "tamano_bytes": null,
      "error": null,
      "saltado": false
    }
  ],
  "fecha_descarga": "ISO-8601",
  "codigo_licitacion": "",
  "ticket_hash": "sha256:..."
}
```

`save_metadata()` empareja `archivos_data` con `download_results` por indice.
Si la descarga se interrumpe antes de generar resultados, rellena las entradas
faltantes con `"No se proceso (error antes de descargar)"`.

### Estado del monitoreo

```json
{
  "ultima_actualizacion": "ISO-8601 local",
  "terminos": ["..."],
  "vistos": ["CODIGO-1", "CODIGO-2"]
}
```

Se escribe completo en cada ciclo. No hay escritura atomica: si el proceso
muere a mitad de escritura, el siguiente ciclo detecta el JSON invalido y
reinicia el registro.

---

## Convenciones de codigo

- **Python 3.9+**: se usan genericos `list[...]` y `dict[...]`, no `|` en
  anotaciones.
- **Docstrings** en todas las funciones publicas, con Args/Returns/Raises.
- **Logging** mediante `logging.getLogger(__name__)`, nunca `print()` fuera de
  `main.py`.
- **Mensajes de usuario** en espanol; nombres de funciones y variables en
  espanol cuando el dominio lo justifica (`buscar_licitaciones`,
  `procesar_licitacion`).
- **Constantes** en mayusculas al inicio del modulo.
- **Una responsabilidad por modulo**; si una funcion necesita tres capas,
  probablemente pertenece a otro archivo.
- **Errores explicitos**: preferir excepciones propias a devolver `None` ante
  fallos.
- **Sin dependencias nuevas** salvo justificacion fuerte. El proyecto se
  mantiene deliberadamente pequeno.

### Estilo de funciones

```python
def nombre_claro(parametro: str, opcional: int = 10) -> dict[str, Any]:
    """
    Una linea que explica que hace.

    Args:
        parametro: Que representa.
        opcional: Valor por defecto y unidad.

    Returns:
        Que devuelve y en que forma.

    Raises:
        ErrorPropio: Cuando ocurre la condicion.
    """
```

---

## Recetas de extension

### 1. Filtrar por fecha en la API

La API acepta `fecha=DDMMAAAA`, pero el cliente actual no lo envia. Cambio
minimo en `mercado_publico.buscar_licitaciones()`:

```python
def buscar_licitaciones(api_client, ticket, terminos=None,
                        solo_vigentes=True, fecha=None):
    params = {"ticket": ticket}
    if fecha:
        params["fecha"] = fecha          # "26062026"
    data = api_client.get_json(LICITACIONES_ENDPOINT, params=params)
    ...
```

Y en `main.py`, agregar la pregunta o un argumento de linea de comandos. No
cambiar la firma de `fetch_licitacion()`: el detalle por codigo no usa fecha.

### 2. Ampliar el criterio de vigencia

Hoy el filtro es `CodigoEstado == 5`. Para incluir los otros codigos de
"Publicada" (1 y 11):

```python
ESTADOS_VIGENTES = {1, 5, 11}

if solo_vigentes and item.get("CodigoEstado") not in ESTADOS_VIGENTES:
    continue
```

Conviene definir la constante junto a `ESTADOS_LICITACION` y documentar el
cambio, porque altera que procesos se consideran disponibles.

### 3. Salida no interactiva

El mayor limite operativo es que `main.py` siempre pide entrada. Un punto de
entrada alternativo puede usar `argparse`:

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--codigo")
parser.add_argument("--terminos")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()

if args.codigo:
    data = fetch_licitacion(client, args.codigo, ticket)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data.get("Nombre"))
```

No es necesario tocar `main.py`: se puede crear `cli.py` y reutilizar los
modulos. Si se quiere reemplazar el menu, mantener `main()` como envoltorio
para no romper la invocacion documentada.

### 4. Exportar a CSV o JSON

Ver el ejemplo del README. Para uso recurrente, crear `exportar.py` con una
funcion `exportar(resultados, destino)` y llamarla desde un ciclo programado.
Mantener `utf-8` y `csv.writer` con `newline=""` para evitar filas dobles en
Windows.

### 5. Notificaciones

No hay envio de correo incluido. Un agregado simple con `smtplib`:

```python
import smtplib
from email.message import EmailMessage

def notificar(asunto: str, cuerpo: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = "monitor@ejemplo.cl"
    msg["To"] = "tu-correo@ejemplo.cl"
    msg.set_content(cuerpo)
    with smtplib.SMTP("smtp.ejemplo.cl", 587) as s:
        s.starttls()
        s.login("usuario", "password")
        s.send_message(msg)
```

Las credenciales deben venir de variables de entorno, nunca del codigo. Para
produccion, preferir un servicio transaccional con API y registrar los fallos
de envio.

### 6. Ajustar tiempos

| Que cambiar | Donde | Efecto |
|-------------|-------|--------|
| Reintentos | `MAX_RETRIES` o `APIClient(max_retries=...)` | Menos/mas tolerancia a fallos |
| Timeout de lectura | `APIClient(timeout=...)` | Espera maxima por respuesta |
| Pausa entre peticiones | `RATE_LIMIT_MIN_WAIT` / `MAX_WAIT` | Menor riesgo de 429 |
| Pausa entre archivos | `min_pause` / `max_pause` | Menor carga al servidor |
| Intervalo de monitoreo | `INTERVALO_MINUTOS` | Frecuencia de sondeo |

No bajar las pausas por debajo de 0,5 segundos. El beneficio es marginal y el
riesgo de bloqueo, real.

### 7. Agregar un endpoint nuevo

Patron:

1. Definir la constante de ruta en `mercado_publico.py`.
2. Crear una funcion que reciba `api_client`, `ticket` y parametros.
3. Llamar `api_client.get_json(...)`.
4. Detectar el sobre `{Codigo, Mensaje}` antes de parsear.
5. Devolver una estructura estable y documentada.
6. Agregar una prueba manual y una entrada en este documento.

No agregar logica de presentacion en `mercado_publico.py`.

### 8. Pruebas con pytest

El proyecto no incluye pruebas automatizadas. Para empezar:

```python
# tests/test_utils.py
from utils import sanitize_filename, resolve_filename_collision
from pathlib import Path

def test_sanitiza_barras():
    assert sanitize_filename("a/b:c.pdf") == "a_b_c.pdf"

def test_colision(tmp_path: Path):
    (tmp_path / "a.pdf").write_text("x")
    assert resolve_filename_collision(tmp_path, "a.pdf") == "a_1.pdf"
```

Para la capa HTTP, `responses` o `requests-mock` permiten simular la API sin
red. No es necesario agregarlas al `requirements.txt` de produccion: van en
`requirements-dev.txt`.

---

## Empaquetado y despliegue

### Estructura de dependencias

`requirements.txt` contiene solo las tres librerias de ejecucion. Si se agregan
pruebas, crear `requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8.0
responses>=0.25
```

### Instalacion reproducible

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.lock.txt
```

El `lock` no se versiona necesariamente, pero sirve para reproducir un entorno
exacto en un servidor.

### Servicio systemd

Ver el ejemplo del README. Puntos criticos:

- `WorkingDirectory` debe ser la raiz del proyecto para que `.env` y
  `descargas/` se resuelvan igual que en la ejecucion manual.
- `EnvironmentFile` apunta al `.env`; el servicio no hereda el entorno del
  shell.
- `Restart=on-failure` evita que un fallo transitorio deje el monitoreo muerto.
- El entrypoint debe ser no interactivo. `main.py` no lo es.

### Contenedor (opcional)

No se incluye Dockerfile. Un esquema minimo:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "ciclo_monitoreo.py"]
```

Montar `descargas/` como volumen y pasar `MERCADO_PUBLICO_TICKET` como variable
de entorno. No copiar `.env` dentro de la imagen.

### Windows

- Usar `venv\Scripts\activate`.
- Programar con el Programador de tareas.
- Evitar rutas con acentos si el equipo tiene una configuracion regional
  antigua.
- Verificar UTF-8 en la consola.

---

## Deuda tecnica y roadmap

### Deuda conocida

| Tema | Detalle | Impacto |
|------|---------|---------|
| Interfaz solo interactiva | No hay argumentos CLI ni modo batch | Dificulta cron/systemd |
| Monitoreo dentro de `main.py` | Mezcla presentacion, persistencia y ciclo | Dificulta pruebas |
| Filtro de vigencia fijo | Solo `CodigoEstado == 5` | Puede omitir estados 1 y 11 |
| Sin pruebas automatizadas | Validacion manual | Regresiones silenciosas |
| `ESTADOS_LICITACION` sin uso | Mapa definido pero no consultado | Deuda menor |
| Imports duplicados | `procesar_licitacion` reimporta modulos | Ruido, sin efecto funcional |
| Colision antes de "saltar" | El chequeo de existente casi no se alcanza | `saltado` rara vez verdadero |
| Sin escritura atomica del registro | `monitoreo_vistos.json` se sobrescribe | Posible perdida ante corte |
| Ventana historica limitada | Depende de la API v1 | No hay solucion local completa |

### Roadmap sugerido

1. **CLI con argumentos** (`--codigo`, `--terminos`, `--monitor`, `--json`).
2. **Modulo `monitor.py`** separado de la interfaz.
3. **Pruebas** de sanitizacion, filtros y metadata con `pytest`.
4. **Exportacion** CSV/JSON integrada.
5. **Filtro por fecha** usando el parametro de la API.
6. **Notificaciones** por correo o webhook.
7. **Empaquetado** como modulo instalable (`pyproject.toml`).
8. **Soporte de ordenes de compra** si la API lo permite.

Cada punto debe ir acompanado de documentacion y de una prueba manual de los
tres modos.

---

## Checklist de revision

Antes de dar por cerrado un cambio:

- [ ] `python -m compileall .` sin errores.
- [ ] Los tres modos se ejecutan sin excepciones no controladas.
- [ ] El ticket no aparece en `metadata.json` ni en los logs.
- [ ] `.env` sigue en `.gitignore`.
- [ ] Los mensajes nuevos explican causa y accion.
- [ ] Las funciones nuevas tienen docstring.
- [ ] `README.md`, `docs/datasheet.md` y este documento reflejan el cambio.
- [ ] No se agregaron dependencias sin justificacion.
- [ ] No se rompio el formato de `metadata.json`.
- [ ] No se modifico el comportamiento del monitoreo sin documentarlo.

---

## Referencias

- Documentacion oficial de la API: https://api.mercadopublico.cl/documentacion
- Obtencion de ticket: https://api.mercadopublico.cl/documentacion/obtencion-de-ticket
- Mercado Publico Chile: https://www.mercadopublico.cl
- PDF de referencia (incluido en el proyecto): `Documentacion-API-Mercado-Publico-Licitaciones.pdf`
- Fuentes ampliadas y glosario: `docs/REFERENCES.md`
- Decisiones y lecciones: `docs/BITACORA.md`
