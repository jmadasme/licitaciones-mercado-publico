# Mercado Publico Downloader

Buscador y descargador de licitaciones y documentos del Mercado Publico de Chile
(api.mercadopublico.cl). Programa interactivo de linea de comandos que, dado un
codigo de licitacion, consulta la API oficial, obtiene los metadatos, lista los
documentos asociados (bases administrativas, bases tecnicas, anexos, etc.) y los
descarga a una carpeta local organizada por licitacion, generando ademas un
archivo JSON con los metadatos completos para trazabilidad.

## Requisitos

- Python 3.10 o superior
- Dependencias listadas en `requirements.txt`:
  - `requests` (>=2.28.0) -- cliente HTTP
  - `python-dotenv` (>=1.0.0) -- carga de variables de entorno desde `.env`
  - `tqdm` (>=4.65.0) -- barras de progreso

## Instalacion

Clona o copia el proyecto en tu maquina local y crea un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

## Configuracion

El programa requiere un ticket de acceso a la API de Mercado Publico. Este ticket
se puede obtener gratuitamente en el sitio oficial de la API.

Una vez obtenido el ticket, existen dos formas de proporcionarlo:

**Opcion A -- Archivo `.env` (recomendada para desarrollo local):**

Copia el archivo de ejemplo y edita el ticket:

```bash
cp .env.example .env
```

Luego edita `.env` y reemplaza `tu_ticket_aqui` por tu ticket real:

```
MERCADO_PUBLICO_TICKET=F21A2B3C4D5E6F7G8H9I0J...
```

**Opcion B -- Variable de entorno del sistema:**

```bash
export MERCADO_PUBLICO_TICKET=F21A2B3C4D5E6F7G8H9I0J...
```

La variable de entorno tiene prioridad sobre el archivo `.env`. Si el ticket no
se encuentra en ninguna de las dos fuentes, el programa mostrara un mensaje de
error explicativo y terminara con codigo de salida 1.

## Uso

Con el entorno virtual activado y el ticket configurado, ejecuta:

```bash
python main.py
```

El programa presenta un banner ASCII y entra en un bucle interactivo:

1. Solicita el codigo de licitacion (ejemplo: `1234567-8-LP24`).
2. Consulta la licitacion y muestra un resumen con nombre, organismo, estado,
   fechas y monto.
3. Pregunta si deseas descargar los documentos.
4. Si confirmas, consulta los archivos asociados, los lista y los descarga uno a
   uno con barra de progreso.
5. Guarda un archivo `metadata.json` con toda la informacion en la carpeta
   `descargas/<codigo_licitacion>/`.
6. Pregunta si deseas buscar otra licitacion. El flujo se repite hasta que
   respondas que no o presiones Ctrl+C.

## Ejemplo de ejecucion

A continuacion se muestra un ejemplo simulado de sesion interactiva:

```
$ python main.py

============================================================
          Mercado Publico -- Buscador y Descargador
            de Licitaciones y Documentos
============================================================

------------------------------------------------------------
Codigo de licitacion: 1234567-8-LP24

Buscando licitacion: 1234567-8-LP24 ...

------------------------------------------------------------
  Codigo          : 1234567-8-LP24
  Nombre          : Construccion Centro Comunitario
  Organismo       : Municipalidad de Providencia
  Estado          : Publicada
  Tipo            : Licitacion Publica
  Publicacion     : 2026-05-01T10:00:00
  Cierre          : 2026-06-30T15:00:00
  Monto estimado  : 150000000
  Descripcion     : Construccion de centro comunitario en sector norte...
------------------------------------------------------------

Descargar documentos? [S/n]: s

Consultando documentos asociados...

Se encontraron 3 documento(s):
    1. Bases Administrativas.pdf  [pdf]
    2. Bases Tecnicas.pdf  [pdf] (1250000 bytes)
    3. Anexo N1 - Planos.zip  [zip]

Descargando archivos a: descargas/1234567-8-LP24/

Bases Administrativas.pdf: 100%|####| 1.25M/1.25M [00:02<00:00, 512kB/s]
Bases Tecnicas.pdf: 100%|####| 890k/890k [00:01<00:00, 445kB/s]
Anexo N1 - Planos.zip: 100%|####| 4.50M/4.50M [00:08<00:00, 562kB/s]

------------------------------------------------------------
  Archivos procesados : 3
  Descargados         : 3
  Saltados (existentes): 0
  Fallidos            : 0
------------------------------------------------------------

  Ruta: /home/usuario/apiMercadoPublico/descargas/1234567-8-LP24/

Buscar otra licitacion? [S/n]: n
```

## Estructura del proyecto

```
apiMercadoPublico/
    main.py                  Punto de entrada, CLI interactiva
    config.py                Carga del ticket desde env o .env
    api_client.py            Cliente HTTP generico (retry, rate-limit, streaming)
    mercado_publico.py       Logica de negocio: endpoints de la API
    downloader.py            Descarga de archivos con barra de progreso
    metadata.py              Serializacion y guardado de metadatos JSON
    utils.py                 Utilidades: sanitizacion, logging, colisiones
    requirements.txt         Dependencias del proyecto (requests, dotenv, tqdm)
    .env.example             Plantilla para el archivo .env
    .gitignore               Exclusiones de Git
    descargas/               Directorio de descargas (creado en ejecucion)
        {codigo_licitacion}/
            archivo1.pdf
            archivo2.docx
            ...
            metadata.json
    docs/                    Documentacion
        datasheet.md         Documentacion de usuario
        developer.md         Documentacion tecnica para desarrolladores
```

## Funcionamiento interno

### Control de tasa y reintentos

- **Pausa de cortesia**: el programa espera de 1 a 2 segundos (jitter aleatorio)
  entre cada peticion HTTP, para no saturar la API.
- **Backoff exponencial**: si una peticion falla, reintenta automaticamente hasta
  3 veces adicionales con esperas de 1s, 2s y 4s.
- **Errores HTTP**: los codigos 5xx activan reintento; los codigos 400 (ticket
  invalido) y 404 (licitacion no encontrada) no reintentan y se manejan con
  mensajes especificos.

### Descarga robusta de archivos

- Los archivos se descargan en modo streaming para soportar tamanos grandes sin
  saturar la memoria.
- Se usa un archivo temporal con extension `.part` durante la descarga; al
  finalizar exitosamente se renombra al nombre final, evitando archivos
  corruptos por descargas interrumpidas.
- Si un archivo falla tras los reintentos, se continua con el siguiente y al
  final se listan los que no pudieron descargarse.
- Los nombres de archivo con caracteres invalidos para el sistema de archivos
  (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`) son sanitizados automaticamente.

### Metadatos

En cada descarga se genera un archivo `metadata.json` con:

- La respuesta completa de la API de licitacion.
- La lista completa de archivos con sus metadatos originales.
- El estado de cada descarga (exito, fallo, saltado).
- Hash SHA-256 del ticket para referencia (nunca se guarda el ticket en texto
  plano).
- Fecha de descarga en formato ISO 8601.

## Advertencias y precauciones

1. **No compartas tu ticket**. El ticket de acceso a la API de Mercado Publico
   es personal e intransferible. El archivo `.env` esta listado en `.gitignore`
   para evitar que se suba accidentalmente a un repositorio.
2. **Limites de la API**. La API de Mercado Publico opera sobre HTTP (no HTTPS),
   lo que implica que los datos viajan sin cifrado. No se recomienda usar este
   programa en redes publicas no confiables.
3. **Tasa de uso**. Aunque el programa implementa pausas de cortesia, no hay una
   documentacion oficial publica sobre los limites exactos de la API. Si
   recibes errores HTTP 429 (rate limit), el programa esperara automaticamente
   antes de reintentar.
4. **Disco lleno**. Si el disco se llena durante la descarga, el programa
   captura el error, detiene las descargas restantes e informa del problema.
5. **Ejecucion concurrente**. No se recomienda ejecutar multiples instancias del
   programa simultaneamente con el mismo ticket, ya que podria interpretarse
   como abuso de la API.
6. **Codigos de licitacion**. Los codigos deben ingresarse sin espacios extra.
   El programa normaliza automaticamente guiones (—, –, −) al guion estandar
   (-) y rechaza codigos con caracteres potencialmente peligrosos (`/`, `\`,
   `..`).

## Licencia

Este proyecto se distribuye sin licencia especifica. Consulta con el autor
antes de redistribuir o modificar.
