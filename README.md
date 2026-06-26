# Mercado Publico Downloader

Buscador, descargador y monitor de licitaciones del Mercado Publico de Chile
(api.mercadopublico.cl). Programa interactivo de linea de comandos con **tres modos
de operacion**:

1. **Busqueda por codigo** — consulta una licitacion especifica, lista sus
   documentos (bases, anexos, actas) y los descarga con barra de progreso.
2. **Busqueda por palabras clave** — filtra las licitaciones recientes (~200) por
   terminos como "telemetria", "iot", "sensores", etc. Muestra resultados
   numerados, permite seleccionar una y descargar sus documentos.
3. **Modo monitoreo** — revision automatica cada 30 minutos con terminos
   predefinidos. Detecta licitaciones NUEVAS, muestra sus detalles y guarda
   reportes con timestamp. Ideal para vigilancia continua de oportunidades.

Toda la informacion se organiza en `descargas/<codigo_licitacion>/` con un archivo
`metadata.json` para trazabilidad completa.

## Requisitos

- Python 3.10 o superior
- Dependencias listadas en `requirements.txt`:
  - `requests` (>=2.28.0) — cliente HTTP
  - `python-dotenv` (>=1.0.0) — carga de variables de entorno desde `.env`
  - `tqdm` (>=4.65.0) — barras de progreso

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

**Opcion A — Archivo `.env` (recomendada para desarrollo local):**

Copia el archivo de ejemplo y edita el ticket:

```bash
cp .env.example .env
```

Luego edita `.env` y reemplaza `tu_ticket_aqui` por tu ticket real:

```
MERCADO_PUBLICO_TICKET=F21A2B3C4D5E6F7G8H9I0J...
```

**Opcion B — Variable de entorno del sistema:**

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

El programa muestra un banner y presenta el **menu principal** con 3 opciones:

```
╔══════════════════════════════════════════════════════════╗
║       Mercado Público — Buscador y Descargador          ║
║         de Licitaciones y Documentos                    ║
╚══════════════════════════════════════════════════════════╝

══════════════════════════════════════════════════════════════
  MENU PRINCIPAL
══════════════════════════════════════════════════════════════
  1. Buscar licitacion por codigo
  2. Buscar licitaciones por palabras clave
  3. Modo monitoreo cada 30 min (terminos fijos)
  0. Salir
──────────────────────────────────────────────────────────────
  Opcion:
```

### Opcion 1 — Buscar por codigo (funcionalidad original)

Ingresa el codigo de licitacion (ejemplo: `1234567-8-LP24`). El programa:

1. Consulta la licitacion y muestra un resumen con nombre, organismo, estado,
   fechas y monto estimado (formateado en CLP).
2. Pregunta si deseas descargar los documentos.
3. Si confirmas, consulta los archivos asociados, los lista y los descarga uno a
   uno con barra de progreso.
4. Guarda un archivo `metadata.json` en `descargas/<codigo_licitacion>/`.
5. Vuelve al menu principal para otra operacion.

**Ejemplo de codigos validos**: `1234567-8-LP24`, `9876543-2-LQ24`, `5555555-1-LP25`.

El programa normaliza automaticamente:
- Espacios al inicio y final (los elimina).
- Guiones especiales (—, –, −) que se convierten a guion estandar (-).
- Multiples guiones consecutivos (se reducen a uno solo).

### Opcion 2 — Buscar por palabras clave

Permite buscar licitaciones filtrando por terminos en el nombre. El programa:

1. Te pide que ingreses terminos separados por comas.
   - Ejemplo: `telemetria, iot, monitoreo, medicion, sensor`
   - Si dejas el campo vacio, lista **todas** las licitaciones vigentes.
2. Pregunta si buscar solo licitaciones **vigentes** (Publicadas) o en **todos
   los estados** (incluye cerradas, adjudicadas, desiertas, etc.).
3. Filtra las ~200 licitaciones mas recientes expuestas por la API v1.
4. Muestra los resultados numerados con codigo y nombre.
5. Seleccionas una licitacion por su numero.
6. Obtiene los detalles completos (descripcion, fechas, monto, organismo).
7. Ofrece descargar sus documentos (igual que en la Opcion 1).

```
──────────────────────────────────────────────────────────────
  BUSQUEDA POR PALABRAS CLAVE
──────────────────────────────────────────────────────────────
  Ingresa terminos separados por comas
  Ej: telemetria, iot, monitoreo, medicion, sensor

  NOTA: La API solo permite buscar entre las ~188
  licitaciones mas recientes, sin incluir descripciones.
  Si no hay resultados, prueba terminos mas generales.
──────────────────────────────────────────────────────────────
  Terminos (vacio = todas las vigentes): telemetria, iot, sensor
  ¿Solo licitaciones vigentes? [S/n]: s
  Buscando solo licitaciones vigentes (Publicadas)...
  Terminos: telemetria, iot, sensor

  Se encontraron 3 licitacion(es):
──────────────────────────────────────────────────────────────
    1. [1234-5-LP26] Adquisicion de sensores de temperatura y humedad
    2. [5678-9-LQ26] Sistema de monitoreo IoT para cuencas hidricas
    3. [9012-3-LP26] Plataforma de telemetria para redes de riego
──────────────────────────────────────────────────────────────
  0. Volver al menu principal

  Selecciona una licitacion (1-3): 2

  Obteniendo detalles de 5678-9-LQ26 ...
```

### Opcion 3 — Modo monitoreo

Vigilancia automatica que busca nuevas licitaciones periodicamente. Ideal para
estar al tanto de oportunidades sin intervencion manual.

**Terminos fijos predefinidos:**

> telemetria, monitor, monitoreo, medicion, sensores, riego, software, alerta,
> reporte, iot, domotica, notificacion, temperatura, humedad, presion, frio

Al iniciar el monitoreo:
1. Muestra los terminos fijos y te permite aceptarlos (Enter) o ingresar otros
   personalizados separados por comas.
2. Cada **30 minutos** consulta la API y filtra las licitaciones que coincidan
   con los terminos.
3. Compara con un registro de licitaciones ya vistas (`descargas/monitoreo_vistos.json`).
4. Si encuentra licitaciones **NUEVAS** (no vistas antes):
   - Las muestra en pantalla con codigo, nombre, descripcion, fecha de cierre,
     estado y monto estimado.
   - Guarda un reporte en `descargas/monitoreo/YYYYMMDD_HHMMSS.txt`.
5. Si no hay novedades, imprime un punto o mensaje de estado.
6. Se detiene presionando **Ctrl+C** limpiamente.

```
──────────────────────────────────────────────────────────────
  MODO MONITOREO
──────────────────────────────────────────────────────────────
  Terminos fijos:
  telemetria, monitor, monitoreo, medicion, sensores, riego, software, alerta, reporte, iot, domotica, notificacion, temperatura, humedad, presion, frio

  Presiona Enter para aceptarlos,
  o ingresa otros separados por comas.
──────────────────────────────────────────────────────────────
  Terminos (Enter = fijos):

  Monitoreando: telemetria, monitor, monitoreo, medicion, sensores, riego, software, alerta, reporte, iot, domotica, notificacion, temperatura, humedad, presion, frio
  Cada 30 min. Ctrl+C para salir.

[11:00:25] Sin novedades. [11:30:25] Sin novedades. [12:00:25] Sin novedades. [12:30:25] Sin novedades.
[13:00:25] NUEVAS LICITACIONES ENCONTRADAS:

  Codigo     : 1234-56-LP26
  Nombre     : Sistema de Telemetria para redes hidricas
  Descripcion: Implementacion de plataforma IoT con sensores para monitoreo...
  Cierre     : 2026-07-25T15:00:00
  Estado     : 5
  Monto      : $ 45,000,000
----------------------------------------------------------------------

  Reporte guardado: descargas/monitoreo/20260701_130025.txt
```

## Ejemplo de ejecucion (Opcion 1 — flujo completo)

A continuacion se muestra un ejemplo simulado de sesion interactiva usando la
opcion de busqueda por codigo:

```
$ python main.py

╔══════════════════════════════════════════════════════════╗
║       Mercado Público — Buscador y Descargador          ║
║         de Licitaciones y Documentos                    ║
╚══════════════════════════════════════════════════════════╝

══════════════════════════════════════════════════════════════
  MENU PRINCIPAL
══════════════════════════════════════════════════════════════
  1. Buscar licitacion por codigo
  2. Buscar licitaciones por palabras clave
  3. Modo monitoreo cada 30 min (terminos fijos)
  0. Salir
──────────────────────────────────────────────────────────────
  Opcion: 1

──────────────────────────────────────────────────────────────
Codigo de licitacion: 1234567-8-LP24

Buscando licitacion: 1234567-8-LP24 ...

──────────────────────────────────────────────────────────────
  Codigo          : 1234567-8-LP24
  Nombre          : Construccion Centro Comunitario
  Organismo       : Municipalidad de Providencia
  Estado          : Publicada
  Tipo            : Licitacion Publica
  Publicacion     : 2026-05-01T10:00:00
  Cierre          : 2026-06-30T15:00:00
  Monto estimado  : $ 150,000,000
  Descripcion     : Construccion de centro comunitario en sector norte...
──────────────────────────────────────────────────────────────

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

──────────────────────────────────────────────────────────────
  Archivos procesados : 3
  Descargados         : 3
  Saltados (existentes): 0
  Fallidos            : 0
──────────────────────────────────────────────────────────────

  Ruta: /home/usuario/apiMercadoPublico/descargas/1234567-8-LP24/

══════════════════════════════════════════════════════════════
  MENU PRINCIPAL
══════════════════════════════════════════════════════════════
  1. Buscar licitacion por codigo
  2. Buscar licitaciones por palabras clave
  3. Modo monitoreo cada 30 min (terminos fijos)
  0. Salir
──────────────────────────────────────────────────────────────
  Opcion: 0
```

## Estructura del proyecto

```
apiMercadoPublico/
    main.py                  Punto de entrada, CLI interactiva con menu
    config.py                Carga del ticket desde env o .env
    api_client.py            Cliente HTTP generico (retry, rate-limit, streaming)
    mercado_publico.py       Logica de negocio: endpoints de la API, busqueda
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
        monitoreo/
            20260626_110025.txt   Reportes de monitoreo
            20260626_120025.txt
            ...
        monitoreo_vistos.json     Registro de licitaciones ya vistas
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
- **Deteccion de errores en cuerpo JSON**: la API puede devolver HTTP 200/203 con
  un mensaje de error en el cuerpo (ej. ticket invalido). El programa inspecciona
  el JSON para detectar estos casos y emitir mensajes claros.

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

### Extraccion de datos

- La API v1 devuelve los datos dentro de una estructura `{"Cantidad": N, "Listado": [...]}`.
  El programa extrae automaticamente `Listado[0]` para licitaciones individuales.
- Soporta campos anidados como `Comprador.NombreOrganismo` y `Fechas.FechaPublicacion`.
- Los montos estimados se formatean automaticamente como pesos chilenos (`$ 150,000,000`).

### Metadatos

En cada descarga se genera un archivo `metadata.json` con:

- La respuesta completa de la API de licitacion.
- La lista completa de archivos con sus metadatos originales.
- El estado de cada descarga (exito, fallo, saltado).
- Hash SHA-256 del ticket para referencia (nunca se guarda el ticket en texto
  plano).
- Fecha de descarga en formato ISO 8601.

## Nota sobre limitaciones de la API v1

La API v1 de Mercado Publico (`https://api.mercadopublico.cl/servicios/v1/publico`)
tiene las siguientes limitaciones a tener en cuenta:

- **Solo expone las ~200 licitaciones mas recientes**. No es posible buscar en
  todo el historial de licitaciones.
- **El listado general no incluye descripciones completas**. La busqueda por
  palabras clave (Opcion 2) filtra por el campo `Nombre` del listado, y solo al
  seleccionar una licitacion se obtiene su `Descripcion` completa.
- **No tiene endpoint de busqueda por texto**. El filtrado por palabras clave se
  realiza localmente sobre los datos obtenidos del listado general.
- **El endpoint de archivos (`Archivos.json`) no siempre esta disponible** para
  todas las licitaciones. En esos casos, el programa sugiere visitar la pagina
  web de Mercado Publico para acceder a los documentos.
- **Los estados de licitacion se representan con codigos numericos** (ej. 5 =
  Publicada, 4 = Adjudicada, 6 = Cerrada), no con texto descriptivo en el
  listado general.

## Advertencias y precauciones

1. **No compartas tu ticket**. El ticket de acceso a la API de Mercado Publico
   es personal e intransferible. El archivo `.env` esta listado en `.gitignore`
   para evitar que se suba accidentalmente a un repositorio.
2. **Conexion HTTPS**. La API de Mercado Publico opera sobre HTTPS. Verifica que
   tu entorno tenga los certificados SSL actualizados.
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
7. **Modo monitoreo continuo**. El modo monitoreo (Opcion 3) se ejecuta
   indefinidamente hasta que se presione Ctrl+C. Asegurate de que el entorno de
   ejecucion (terminal, servidor, etc.) permanezca activo. Considera usar
   herramientas como `tmux`, `screen` o `nohup` si ejecutas en un servidor
   remoto.

## Licencia

Este proyecto se distribuye sin licencia especifica. Consulta con el autor
antes de redistribuir o modificar.
