# Datasheet -- Mercado Publico Downloader

Documentacion de usuario para el programa de busqueda, descarga y monitoreo de
licitaciones del Mercado Publico de Chile.

## Indice

1. [Que es Mercado Publico](#que-es-mercado-publico)
2. [Como obtener un ticket de acceso](#como-obtener-un-ticket-de-acceso)
3. [Guia paso a paso de uso](#guia-paso-a-paso-de-uso)
   - [Opcion 1: Buscar por codigo](#opcion-1-buscar-por-codigo)
   - [Opcion 2: Buscar por palabras clave](#opcion-2-buscar-por-palabras-clave)
   - [Opcion 3: Modo monitoreo](#opcion-3-modo-monitoreo)
4. [Dependencias](#dependencias)
5. [Estructura de la salida](#estructura-de-la-salida)
6. [Archivos del modo monitoreo](#archivos-del-modo-monitoreo)
7. [Solucion de problemas comunes](#solucion-de-problemas-comunes)

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

El programa mostrara un banner ASCII y el **menu principal** con tres modos de
operacion:

```
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

---

### Opcion 1: Buscar por codigo

Busca una licitacion especifica por su codigo unico. Este es el flujo original
del programa.

**Paso a paso:**

1. Ingresa `1` en el menu y presiona Enter.
2. Ingresa el codigo de la licitacion. Ejemplos de formatos validos:
   - `1234567-8-LP24`
   - `9876543-2-LQ24`
   - `5555555-1-LP25`
3. El programa consulta la API y muestra un resumen con todos los datos
   disponibles.
4. Confirma si deseas descargar los documentos (`[S/n]`).
5. Si confirmas, se listan los archivos y se descargan con barra de progreso.
6. Se genera `metadata.json` en `descargas/<codigo>/`.
7. Vuelve al menu principal.

**El programa normaliza automaticamente:**
- Espacios al inicio y final (los elimina).
- Guiones especiales (—, –, −) que se convierten a guion estandar (-).
- Multiples guiones consecutivos (se reducen a uno solo).

Si el codigo esta vacio, el programa pedira que lo ingreses nuevamente (maximo 3
intentos).

**Resumen mostrado:**

```
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
```

**Campos mostrados:**

| Campo | Descripcion |
|-------|------------|
| Codigo | Identificador unico de la licitacion |
| Nombre | Titulo o nombre del proceso |
| Organismo | Entidad publica que publica la licitacion (extraido de `Comprador.NombreOrganismo`) |
| Estado | Estado actual (ej. Publicada, Cerrada, Adjudicada) |
| Tipo | Tipo de licitacion (Licitacion Publica, Licitacion Privada, etc.) |
| Publicacion | Fecha y hora de publicacion (extraido de `Fechas.FechaPublicacion`) |
| Cierre | Fecha y hora limite para presentar ofertas |
| Monto estimado | Presupuesto estimado, formateado en CLP si es un valor numerico |
| Descripcion | Detalle de la licitacion (truncado a 200 caracteres) |

---

### Opcion 2: Buscar por palabras clave

Permite descubrir licitaciones filtrando por terminos de interes. Util cuando
no conoces el codigo exacto y quieres explorar que hay disponible.

**Paso a paso:**

1. Ingresa `2` en el menu y presiona Enter.
2. Ingresa los terminos de busqueda separados por comas:
   ```
   Terminos (vacio = todas las vigentes): telemetria, iot, sensor
   ```
   Si dejas el campo vacio, se listaran **todas** las licitaciones vigentes.
3. Responde si quieres buscar solo licitaciones **vigentes** (Publicadas) o en
   todos los estados (incluye cerradas, adjudicadas, desiertas, revocadas, etc.):
   ```
   ¿Solo licitaciones vigentes? [S/n]:
   ```
   - Enter o `s` = solo vigentes.
   - `n` = todos los estados.
4. El programa filtra el listado de ~200 licitaciones recientes y muestra los
   resultados numerados:
   ```
   Se encontraron 3 licitacion(es):
   ──────────────────────────────────────────────────────────────
       1. [1234-5-LP26] Adquisicion de sensores de temperatura y humedad
       2. [5678-9-LQ26] Sistema de monitoreo IoT para cuencas hidricas
       3. [9012-3-LP26] Plataforma de telemetria para redes de riego
   ──────────────────────────────────────────────────────────────
     0. Volver al menu principal
   ```
5. Selecciona una licitacion por su numero (ej. `2`).
6. El programa obtiene los datos completos de esa licitacion y muestra el
   resumen detallado (igual que en la Opcion 1).
7. Ofrece descargar los documentos asociados.

**Consideraciones importantes:**
- La API v1 solo expone las ~200 licitaciones mas recientes. No busca en todo el
  historial.
- El filtrado se hace sobre el campo `Nombre` del listado general. Las
  descripciones completas solo se obtienen al seleccionar una licitacion
  especifica.
- Si no aparecen resultados, prueba con terminos mas generales o cortos
  (ej. `agua`, `digital`, `sistema`, `equipo`, `red`, `obra`, `informe`).
- Puedes usar esta opcion sin terminos (dejando el campo vacio y confirmando
  Enter) para ver **todas** las licitaciones vigentes recientes.

**Estados de licitacion:**

| Codigo | Estado |
|--------|--------|
| 1, 5, 11 | Publicada (vigente) |
| 2, 6 | Cerrada |
| 3, 7 | Desierta |
| 4, 8 | Adjudicada |
| 9 | Revocada |
| 10, 15 | Suspendida |

---

### Opcion 3: Modo monitoreo

Ejecuta una vigilancia automatica que revisa periodicamente si aparecen nuevas
licitaciones que coincidan con palabras clave predefinidas. Ideal para monitoreo
continuo de oportunidades sin intervencion manual.

**Paso a paso:**

1. Ingresa `3` en el menu y presiona Enter.
2. El programa muestra los **terminos fijos predefinidos**:

   > telemetria, monitor, monitoreo, medicion, sensores, riego, software,
   > alerta, reporte, iot, domotica, notificacion, temperatura, humedad,
   > presion, frio

3. Tienes dos opciones:
   - Presiona **Enter** para aceptar los terminos fijos.
   - Ingresa tus propios terminos separados por comas (ej. `construccion, obras, puente`).
4. El monitoreo comienza. Cada **30 minutos**:
   - Consulta la API y filtra las licitaciones que coincidan con los terminos.
   - Compara contra el archivo `descargas/monitoreo_vistos.json` (registro de
     codigos ya conocidos).
   - Si encuentra licitaciones **NUEVAS** (no registradas antes):
     - Las muestra en pantalla con: codigo, nombre, descripcion, fecha de cierre,
       estado y monto estimado.
     - Guarda un reporte detallado en `descargas/monitoreo/YYYYMMDD_HHMMSS.txt`.
     - Las agrega al registro de ya vistas para no repetirlas en futuros ciclos.
   - Si no hay novedades, imprime `[HH:MM:SS] Sin novedades.` en la misma linea
     (cada 4 ciclos pasa a la siguiente linea para legibilidad).
5. Para detener el monitoreo, presiona **Ctrl+C**. El programa sale limpiamente
   guardando el estado del registro de vistas.

**Ejemplo de salida durante el monitoreo:**

```
[11:00:25] Sin novedades. [11:30:25] Sin novedades. [12:00:25] Sin novedades. [12:30:25] Sin novedades.
[13:00:25] NUEVAS LICITACIONES ENCONTRADAS:

  Codigo     : 1234-56-LP26
  Nombre     : Sistema de Telemetria para redes hidricas
  Descripcion: Implementacion de plataforma IoT con sensores para monitoreo de calidad de agua...
  Cierre     : 2026-07-25T15:00:00
  Estado     : 5
  Monto      : $ 45,000,000
----------------------------------------------------------------------

  Reporte guardado: descargas/monitoreo/20260701_130025.txt
```

**Ejecucion prolongada:**
- Usa `tmux` o `screen` en servidores Linux para mantener el monitoreo activo
  aunque cierres la terminal:
  ```bash
  tmux new -s monitoreo
  python main.py
  # Selecciona opcion 3
  # Presiona Ctrl+B, luego D para desconectar
  # Para reconectar: tmux attach -t monitoreo
  ```
- En Windows, puedes dejar la terminal abierta o usar el Programador de Tareas
  para ejecuciones periodicas en lugar del modo monitoreo continuo.

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
    monitoreo/
        20260626_110025.txt
        20260626_130025.txt
    monitoreo_vistos.json
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
      "url_origen": "https://...",
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

## Archivos del modo monitoreo

### monitoreo_vistos.json

Registro persistente de las licitaciones que ya han sido detectadas y
reportadas. Evita que el monitoreo muestre repetidamente las mismas
licitaciones en cada ciclo.

```json
{
  "ultima_actualizacion": "2026-07-01T13:00:25.123456",
  "terminos": ["telemetria", "monitor", "monitoreo", ...],
  "vistos": ["1234-56-LP26", "5678-9-LQ26"]
}
```

- **`ultima_actualizacion`**: Marca de tiempo ISO 8601 del ultimo ciclo exitoso.
- **`terminos`**: Lista de terminos usados en el monitoreo actual.
- **`vistos`**: Array de codigos de licitacion ya reportados.

**Nota**: Si cambias los terminos de busqueda, las licitaciones previamente
vistas no se volveran a mostrar aunque coincidan con los nuevos terminos, porque
el registro de `vistos` es acumulativo. Para reiniciar el registro, elimina el
archivo `monitoreo_vistos.json`.

### Reportes de monitoreo (`YYYYMMDD_HHMMSS.txt`)

Cada vez que se detectan nuevas licitaciones, se genera un archivo de reporte
en `descargas/monitoreo/`. El formato es:

```
Reporte de Monitoreo - 2026-07-01 13:00:25
Terminos: telemetria, monitor, monitoreo, ...
Licitaciones encontradas: 1
======================================================================

  Codigo     : 1234-56-LP26
  Nombre     : Sistema de Telemetria para redes hidricas
  Descripcion: Implementacion de plataforma IoT con sensores...
  Cierre     : 2026-07-25T15:00:00
  Estado     : 5
  Monto      : $ 45,000,000
----------------------------------------------------------------------
```

Estos reportes son acumulativos: cada nuevo reporte es un archivo independiente
con timestamp en el nombre. Puedes revisarlos, archivarlos o eliminarlos segun
tu conveniencia.

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

### Error: "Ticket invalido" (HTTP 400 o error en cuerpo JSON)

**Causa**: La API rechazo el ticket proporcionado. Esto puede venir como HTTP 400
o como HTTP 200/203 con un mensaje de error en el cuerpo JSON.

**Solucion**:
1. Verifica que el ticket este completo y sin espacios extra al inicio o final.
2. Si copiaste el ticket de un correo o pagina web, revisa que no tenga saltos
   de linea.
3. Genera un nuevo ticket desde el sitio de documentacion de la API si el
   anterior expiro o fue revocado.

### Error: "Licitacion no encontrada" (HTTP 404 o Listado vacio)

**Causa**: El codigo ingresado no corresponde a una licitacion existente en el
sistema, o la API devolvio un listado vacio.

**Solucion**:
1. Verifica que el codigo este bien escrito. Los codigos de Mercado Publico
   suelen tener el formato `NNNNNNN-N-LLNN` (numeros, guion, numero, guion,
   letras y numeros).
2. Confirma que la licitacion existe buscandola manualmente en
   www.mercadopublico.cl.
3. Ten en cuenta que algunas licitaciones muy antiguas pueden no estar
   disponibles en la API v1.

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

**Causa**: La API de Mercado Publico puede tener latencia variable. Las pausas
de cortesia del programa (1-2 segundos entre peticiones) son deliberadas para no
saturar el servicio.

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
2. Intenta acceder a https://api.mercadopublico.cl desde un navegador para
   confirmar que el servicio esta operativo.
3. El programa reintenta automaticamente hasta 3 veces con backoff exponencial
   (1s, 2s, 4s). Si los reintentos se agotan, puedes ejecutar el programa
   nuevamente mas tarde.

### Opcion 2: No se encuentran resultados con mis terminos

**Causa**: La API v1 solo expone las ~200 licitaciones mas recientes. Es posible
que ninguna de ellas contenga tus terminos en el nombre.

**Solucion**:
1. Prueba con terminos mas generales o cortos (ej. `agua`, `digital`, `sistema`,
   `equipo`, `red`, `obra`, `informe`, `consultoria`).
2. Deja el campo de terminos vacio y presiona Enter para ver **todas** las
   licitaciones vigentes. Asi puedes revisar manualmente los nombres.
3. Prueba con `n` en la pregunta de solo vigentes para buscar tambien entre
   licitaciones cerradas y adjudicadas.
4. Recuerda que el filtro es sobre el campo `Nombre`, no sobre la descripcion
   completa (la descripcion solo se obtiene al seleccionar una licitacion).

### Opcion 3: El monitoreo no detecta nada por horas

**Causa**: Es normal. Las licitaciones nuevas aparecen cuando los organismos
publicos las publican, lo cual puede ser poco frecuente dependiendo de los
terminos de busqueda.

**Solucion**:
1. Verifica que estas usando terminos relevantes para tu rubro. Los terminos
   fijos estan orientados a IoT, telemetria y sensores.
2. Si necesitas monitorear otros rubros, ingresa terminos personalizados al
   iniciar el monitoreo.
3. Ten paciencia: el monitoreo puede pasar varios ciclos sin novedades. Esta
   disenado para ejecucion prolongada.
4. Revisa los reportes generados en `descargas/monitoreo/` para confirmar que
   el sistema esta funcionando (los archivos se crean solo cuando hay
   novedades, pero `monitoreo_vistos.json` se actualiza en cada ciclo).

### Error SSL o certificados al conectar con la API

**Causa**: La API usa HTTPS y tu sistema puede no tener los certificados raiz
actualizados.

**Solucion**:
1. En Linux, actualiza los certificados: `sudo apt update && sudo apt install ca-certificates` (Debian/Ubuntu) o equivalente en tu distribucion.
2. En Windows, asegurate de que tu Python tenga los certificados correctos.
3. Si estas detras de un proxy corporativo, puede ser necesario configurar las
   variables de entorno `HTTP_PROXY` y `HTTPS_PROXY`.
4. Como ultimo recurso (no recomendado para produccion), puedes modificar
   `mercado_publico.py` y cambiar `https://` por `http://` en `BASE_URL`, pero
   ten en cuenta que los datos viajaran sin cifrado.

### El archivo monitoreo_vistos.json crece demasiado

**Causa**: El registro de licitaciones vistas es acumulativo por diseno, para
evitar mostrar licitaciones repetidas.

**Solucion**:
1. Elimina el archivo `monitoreo_vistos.json` para reiniciar el registro. El
   programa creara uno nuevo en el siguiente ciclo de monitoreo.
2. Si solo quieres limpiar entradas antiguas, puedes editar manualmente el
   archivo (es un JSON simple) y eliminar codigos que ya no te interesen.
