# Datasheet -- Mercado Publico Downloader

Documentacion de usuario para el programa de busqueda y descarga de licitaciones
del Mercado Publico de Chile.

## Indice

1. [Que es Mercado Publico](#que-es-mercado-publico)
2. [Como obtener un ticket de acceso](#como-obtener-un-ticket-de-acceso)
3. [Guia paso a paso de uso](#guia-paso-a-paso-de-uso)
4. [Dependencias](#dependencias)
5. [Estructura de la salida](#estructura-de-la-salida)
6. [Solucion de problemas comunes](#solucion-de-problemas-comunes)

---

## Que es Mercado Publico

Mercado Publico (www.mercadopublico.cl) es la plataforma electronica oficial de
compras y contrataciones del Estado de Chile. A traves de ella, los organismos
publicos publican licitaciones, cotizaciones y procesos de compra. Proveedores y
ciudadanos pueden consultar estas publicaciones, revisar documentos (bases
administrativas, bases tecnicas, anexos, aclaraciones, etc.) y participar en los
procesos que correspondan.

La plataforma expone una API REST publica (api.mercadopublico.cl) que permite
consultar licitaciones y sus documentos asociados de forma programatica. El
acceso requiere un ticket de autenticacion, que se obtiene gratuitamente en el
sitio de documentacion de la API.

## Como obtener un ticket de acceso

1. Accede a la documentacion oficial de la API de Mercado Publico:
   https://api.mercadopublico.cl/documentacion/obtencion-de-ticket

2. Sigue las instrucciones del sitio para generar tu ticket. El proceso es
   gratuito y requiere un registro basico.

3. Una vez obtenido, el ticket es una cadena alfanumerica que debes conservar de
   forma segura. No lo compartas ni lo subas a repositorios publicos.

4. Configuralo en el proyecto usando una de las dos opciones:
   - Copia `.env.example` a `.env` y edita el valor de `MERCADO_PUBLICO_TICKET`.
   - Exporta la variable de entorno `MERCADO_PUBLICO_TICKET` en tu shell.

## Guia paso a paso de uso

### 1. Instalacion del entorno

Abre una terminal en el directorio del proyecto y ejecuta:

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

Verifica que no haya errores en la instalacion de las dependencias.

### 2. Configuracion del ticket

Copia la plantilla y edita el archivo:

```bash
cp .env.example .env
```

Abre `.env` con un editor de texto y reemplaza `tu_ticket_aqui` por el ticket
que obtuviste de Mercado Publico:

```
MERCADO_PUBLICO_TICKET=F21A2B3C4D5E6F7G8H9I0J...
```

Guarda el archivo. Verifica que `.env` esta listado en `.gitignore` para no
subirlo accidentalmente a un repositorio Git.

### 3. Ejecucion del programa

Con el entorno virtual activado:

```bash
python main.py
```

### 4. Ingreso del codigo de licitacion

El programa mostrara un banner ASCII y un prompt:

```
Codigo de licitacion:
```

Ingresa el codigo de la licitacion que deseas buscar. Ejemplos de formatos
validos:

- `1234567-8-LP24`
- `9876543-2-LQ24`
- `5555555-1-LP25`

El programa normaliza automaticamente:
- Espacios al inicio y final (los elimina).
- Guiones especiales (—, –, −) que se convierten a guion estandar (-).
- Multiples guiones consecutivos (se reducen a uno solo).

Si el codigo esta vacio, el programa pedira que lo ingreses nuevamente (maximo 3
intentos).

### 5. Revision del resumen

Una vez encontrada la licitacion, el programa muestra un resumen en consola con:

- Codigo de la licitacion
- Nombre o descripcion
- Organismo publico licitante
- Estado actual
- Tipo de licitacion
- Fecha de publicacion y fecha de cierre
- Monto estimado
- Descripcion (truncada a 200 caracteres si es muy extensa)

Ejemplo:

```
------------------------------------------------------------
  Codigo          : 1234567-8-LP24
  Nombre          : Construccion Centro Comunitario
  Organismo       : Municipalidad de Providencia
  Estado          : Publicada
  Tipo            : Licitacion Publica
  Publicacion     : 2026-05-01T10:00:00
  Cierre          : 2026-06-30T15:00:00
  Monto estimado  : 150000000
------------------------------------------------------------
```

### 6. Confirmacion de descarga

El programa preguntara:

```
Descargar documentos? [S/n]:
```

- Responde `s` (o presiona Enter, que usa el valor por defecto "Si") para
  continuar con la descarga.
- Responde `n` para omitir la descarga y volver a preguntar si deseas buscar
  otra licitacion.

### 7. Descarga de archivos

Si confirmas, el programa consulta los documentos asociados, los lista y los
descarga uno a uno con barra de progreso:

```
Se encontraron 3 documento(s):
    1. Bases Administrativas.pdf  [pdf]
    2. Bases Tecnicas.pdf  [pdf] (1250000 bytes)
    3. Anexo N1 - Planos.zip  [zip]

Descargando archivos a: descargas/1234567-8-LP24/

Bases Administrativas.pdf: 100%|####| 1.25M/1.25M [00:02<00:00, 512kB/s]
Bases Tecnicas.pdf: 100%|####| 890k/890k [00:01<00:00, 445kB/s]
Anexo N1 - Planos.zip: 100%|####| 4.50M/4.50M [00:08<00:00, 562kB/s]
```

Los archivos se guardan en `descargas/<codigo_licitacion>/`. Si la carpeta ya
existe (por una descarga anterior), el programa preguntara si deseas sobrescribir
los archivos existentes.

### 8. Metadatos

Al finalizar la descarga se genera automaticamente un archivo `metadata.json` en
la misma carpeta con:

- Los datos completos de la licitacion (respuesta original de la API).
- La lista completa de archivos con sus metadatos.
- El estado de cada descarga (exito, fallo, saltado).
- La fecha de descarga en formato ISO 8601.
- Un hash SHA-256 del ticket para referencia (el ticket nunca se guarda en
  texto plano).

### 9. Continuar con otra licitacion

El programa preguntara:

```
Buscar otra licitacion? [S/n]:
```

Responde `s` (o Enter) para buscar otra licitacion y repetir el proceso. Responde
`n` para salir. Tambien puedes presionar Ctrl+C en cualquier momento para
interrumpir el programa limpiamente.

---

## Dependencias

El proyecto utiliza las siguientes librerias de terceros, especificadas en
`requirements.txt`:

| Libreria      | Version minima | Proposito                                      |
|---------------|----------------|------------------------------------------------|
| `requests`    | 2.28.0         | Cliente HTTP para consumir la API              |
| `python-dotenv`| 1.0.0         | Carga de variables de entorno desde archivo .env|
| `tqdm`        | 4.65.0         | Barras de progreso en consola                  |

Para instalar las dependencias dentro del entorno virtual del proyecto:

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

---

## Estructura de la salida

Al completar una descarga, la carpeta de salida tiene la siguiente estructura:

```
descargas/
    1234567-8-LP24/
        Bases Administrativas.pdf
        Bases Tecnicas.pdf
        Anexo N1 - Planos.zip
        metadata.json
```

### Contenido de metadata.json

```json
{
  "licitacion": { ... },
  "archivos_count": 3,
  "archivos": [ ... ],
  "descargas": [
    {
      "nombre": "Bases_Administrativas.pdf",
      "url_origen": "http://...",
      "archivo_local": "descargas/1234567-8-LP24/Bases_Administrativas.pdf",
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

---

## Solucion de problemas comunes

### Error: "No se encontro MERCADO_PUBLICO_TICKET"

**Causa**: El programa no encuentra el ticket en la variable de entorno ni en el
archivo `.env`.

**Solucion**:
1. Verifica que creaste el archivo `.env` a partir de `.env.example` y que
   contiene `MERCADO_PUBLICO_TICKET=<tu_ticket>`.
2. Si usas variable de entorno, verifica que la exportaste correctamente:
   `echo $MERCADO_PUBLICO_TICKET` (Linux/Mac) o `echo %MERCADO_PUBLICO_TICKET%`
   (Windows).
3. Asegurate de que el ticket no esta vacio o compuesto solo de espacios.

### Error: "Ticket invalido (HTTP 400)"

**Causa**: La API rechazo el ticket proporcionado.

**Solucion**:
1. Verifica que el ticket este completo y sin espacios extra al inicio o final.
2. Si copiaste el ticket de un correo o pagina web, revisa que no tenga saltos
   de linea.
3. Genera un nuevo ticket desde el sitio de documentacion de la API si el
   anterior expiro o fue revocado.

### Error: "Licitacion no encontrada (HTTP 404)"

**Causa**: El codigo ingresado no corresponde a una licitacion existente en el
sistema.

**Solucion**:
1. Verifica que el codigo este bien escrito. Los codigos de Mercado Publico
   suelen tener el formato `NNNNNNN-N-LLNN` (numeros, guion, numero, guion,
   letras y numeros).
2. Confirma que la licitacion existe buscandola manualmente en
   www.mercadopublico.cl.
3. Ten en cuenta que algunas licitaciones muy antiguas pueden no estar
   disponibles en la API.

### Error: "No tiene URL de descarga"

**Causa**: El endpoint de archivos devolvio un registro que no contiene un campo
de URL valido. Esto puede ocurrir si la estructura de la respuesta de la API
cambio.

**Solucion**:
1. Verifica el archivo `metadata.json` generado para inspeccionar los datos
   crudos de la API.
2. Si el problema es sistematico, puede ser necesario actualizar el mapeo de
   campos en `mercado_publico.py`.

### Error: "Error de E/S" durante la descarga

**Causa**: Problema de escritura en disco, normalmente por espacio insuficiente
o permisos.

**Solucion**:
1. Verifica el espacio disponible en disco.
2. Asegurate de tener permisos de escritura en la carpeta del proyecto y en
   `descargas/`.
3. Si usas un sistema de archivos en red o una unidad extraible, verifica que
   este montada correctamente.

### Las descargas son muy lentas

**Causa**: La API de Mercado Publico opera sobre HTTP y puede tener latencia
variable. Las pausas de cortesia del programa (1-2 segundos entre peticiones)
son deliberadas para no saturar el servicio.

**Solucion**:
1. Las pausas de cortesia no son configurables por el usuario final. Si necesitas
   ajustarlas, modifica las constantes `RATE_LIMIT_MIN_WAIT` y
   `RATE_LIMIT_MAX_WAIT` en `api_client.py` (requiere conocimientos de Python).
2. Verifica tu conexion a Internet.

### El programa se congela o no muestra progreso

**Causa**: Puede deberse a que la API no incluye la cabecera `Content-Length` en
la respuesta de descarga, en cuyo caso la barra de progreso no muestra porcentaje
pero si muestra los bytes descargados acumulados.

**Solucion**:
1. Espera unos segundos. La barra de `tqdm` deberia actualizar al menos los
   bytes descargados.
2. Si el programa no responde por mas de 60 segundos, presiona Ctrl+C para
   interrumpirlo. El timeout de conexion es de 10 segundos y el de lectura de 30
   segundos; si se superan, el programa reintenta automaticamente.

### Error de conexion o timeout repetido

**Causa**: Problemas de red o la API no esta disponible temporalmente.

**Solucion**:
1. Verifica tu conexion a Internet.
2. Intenta acceder a http://api.mercadopublico.cl desde un navegador para
   confirmar que el servicio esta operativo.
3. El programa reintenta automaticamente hasta 3 veces con backoff exponencial
   (1s, 2s, 4s). Si los reintentos se agotan, puedes ejecutar el programa
   nuevamente mas tarde.
