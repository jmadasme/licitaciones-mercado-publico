# Referencias — Licitaciones Mercado Público

Fuentes oficiales, documentación técnica y criterios de verificación usados para construir y mantener este proyecto. El objetivo es que cualquier persona pueda comprobar de dónde sale cada dato y qué hacer cuando la API cambie.

---

## 1. Fuentes oficiales del Mercado Público

| Recurso | URL | Uso en el proyecto |
|---|---|---|
| Portal Mercado Público | <https://www.mercadopublico.cl> | Ficha pública de cada licitación |
| Documentación de la API | <https://api.mercadopublico.cl/documentacion> | Contrato general, formatos y parámetros |
| Obtención de ticket | <https://api.mercadopublico.cl/documentacion/obtencion-de-ticket> | Alta de la credencial personal |
| API v1 — licitaciones | <https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json> | Endpoint consultado por el programa |
| ChileCompra | <https://www.chilecompra.cl> | Marco institucional de las compras públicas |
| Datos abiertos | <https://datosabiertos.chilecompra.cl> | Alternativa para análisis histórico |
| Ley 19.886 | <https://www.bcn.cl/leychile/navegar?idNorma=213004> | Ley de bases sobre contratos administrativos |
| Unidad Tributaria Mensual (SII) | <https://www.sii.cl/valores_y_fechas/utm/> | Equivalencia de los tramos L1/LE/LP/LQ/LR |
| UNSPSC | <https://www.unspsc.org> | Codificación de productos y servicios |

> **Nota:** las URLs institucionales pueden cambiar sin aviso. Si un enlace falla, buscar el recurso por nombre en el sitio principal antes de asumir que la API desapareció.

---

## 2. Documento incluido en el repositorio

`Documentacion-API-Mercado-Publico-Licitaciones.pdf` es el diccionario de datos oficial de la API. Sus secciones más útiles:

| Sección | Contenido |
|---|---|
| 1. Introducción | Formatos XML, JSON y JSONP; parámetros GET |
| 2. Campos disponibles | Más de 90 campos con tipo y longitud |
| 3.1 Tipo de licitación | Códigos L1, LE, LP, LQ, LR, LS, E2, CO, B2, H2, I2 |
| 3.2 Unidad monetaria | CLP, CLF, USD, UTM, EUR |
| 3.3 Monto estimado | Presupuesto disponible, precio referencial, no estimable |
| 3.4 Modalidad de pago | Códigos 1 a 10 |
| 3.5–3.6 Unidades de tiempo | Horas, días, semanas, meses, años |
| 3.7 Tipo de acto administrativo | Autorización, resolución, acuerdo, decreto, otros |

### Cómo extraer el texto del PDF

Si se necesita buscar una definición concreta:

```bash
pdftotext -layout Documentacion-API-Mercado-Publico-Licitaciones.pdf /tmp/mp_api.txt
grep -n -i "MontoEstimado" /tmp/mp_api.txt
```

El PDF sigue siendo la fuente primaria para los campos que el programa no consume pero que podrían necesitarse en una extensión (por ejemplo `Items`, `Adjudicacion` o `TomaRazon`).

---

## 3. Endpoints y parámetros

URL base:

```
https://api.mercadopublico.cl/servicios/v1/publico
```

| Operación | Ruta | Parámetros | Formato |
|---|---|---|---|
| Detalle por código | `/licitaciones.json` | `codigo`, `ticket` | JSON |
| Listado general | `/licitaciones.json` | `ticket` | JSON |
| Documentos | `/licitaciones/{codigo}/Archivos.json` | `ticket` | JSON |
| Variante XML | `/licitaciones.xml` | `codigo`, `ticket` | XML |
| Variante JSONP | `/licitaciones.jsonp` | `codigo`, `ticket` | JSONP |

Parámetros documentados que **no** usa la implementación actual:

- `fecha=DDMMAAAA`: consulta por fecha de publicación.
- `estado=...`: filtro por estado en el origen.

Ambos son candidatos naturales de extensión. Antes de implementarlos, verificar su comportamiento real con una consulta de prueba y documentar el resultado en `docs/BITACORA.md`.

---

## 4. Códigos que el programa interpreta

### Estados

| Código | Estado | Observación |
|---|---|---|
| 1 | Publicada | No incluido en el filtro de vigentes |
| 2 | Cerrada | — |
| 3 | Desierta | — |
| 4 | Adjudicada | — |
| 5 | Publicada | Único código usado por `solo_vigentes` |
| 6 | Cerrada | — |
| 7 | Desierta | — |
| 8 | Adjudicada | — |
| 9 | Revocada | — |
| 10 | Suspendida | — |
| 11 | Publicada | No incluido en el filtro de vigentes |
| 15 | Suspendida | — |

La duplicidad de códigos sugiere etapas o variantes internas del portal. El filtro conservador por `5` evita falsos positivos, a costa de posibles omisiones.

### Tipos

| Código | Tramo |
|---|---|
| L1 | Pública menor a 100 UTM |
| LE | Pública de 100 a 1.000 UTM |
| LP | Pública de 1.000 a 2.000 UTM |
| LQ | Pública de 2.000 a 5.000 UTM |
| LR | Pública de 5.000 UTM o más |
| LS | Pública de servicios personales especializados |
| E2 | Privada menor a 100 UTM |
| CO | Privada de 100 a 1.000 UTM |
| B2 | Privada de 1.000 a 2.000 UTM |
| H2 | Privada de 2.000 a 5.000 UTM |
| I2 | Privada de más de 5.000 UTM |

### Monedas

`CLP` peso chileno, `CLF` Unidad de Fomento, `USD` dólar, `UTM` Unidad Tributaria Mensual, `EUR` euro.

---

## 5. Documentación técnica de dependencias

| Librería | Versión declarada | Documentación | Licencia |
|---|---|---|---|
| `requests` | >= 2.28.0 | <https://requests.readthedocs.io/> | Apache-2.0 |
| `python-dotenv` | >= 1.0.0 | <https://pypi.org/project/python-dotenv/> | BSD-3-Clause |
| `tqdm` | >= 4.65.0 | <https://tqdm.github.io/> | MPL-2.0 y MIT |

Referencias de la biblioteca estándar usadas:

- `venv`: <https://docs.python.org/3/library/venv.html>
- `logging`: <https://docs.python.org/3/library/logging.html>
- `hashlib`: <https://docs.python.org/3/library/hashlib.html>
- `dataclasses`: <https://docs.python.org/3/library/dataclasses.html>
- `json`: <https://docs.python.org/3/library/json.html>

Estándares relevantes:

- HTTP/1.1 y semántica de status: RFC 9110 — <https://www.rfc-editor.org/rfc/rfc9110>
- JSON: RFC 8259 — <https://www.rfc-editor.org/rfc/rfc8259>
- Fechas ISO 8601: <https://www.iso.org/iso-8601-date-and-time-format.html>
- SHA-256: FIPS 180-4 — <https://csrc.nist.gov/pubs/fips/180-4/upd1/final>

---

## 6. Matriz de verificación

Qué se comprobó, contra qué fuente y con qué resultado:

| Afirmación | Fuente | Resultado |
|---|---|---|
| El ticket se envía como query string | Documentación oficial y PDF | Confirmado |
| La respuesta viene en `Listado` | PDF, sección 2 | Confirmado |
| `Archivos.json` no siempre existe | Pruebas contra la API | Confirmado; 404 tolerado |
| El listado general ronda las 188–200 licitaciones | Observación empírica | Confirmado en el entorno de desarrollo |
| El listado no acepta búsqueda por texto | Documentación y pruebas | Confirmado; filtro local |
| Los estados 1, 5 y 11 son "Publicada" | PDF y observación | Confirmado |
| El monto puede venir como `float` o ausente | PDF y respuestas reales | Confirmado; se formatea si es numérico |
| La API puede devolver error en cuerpo con HTTP 2xx | Pruebas reales | Confirmado; se inspecciona el JSON |
| `Adjudicacion.UrlActa` aparece al adjudicarse | PDF, campo 83 | Confirmado |
| La descarga requiere el ticket en la URL | Pruebas reales | Confirmado; se agrega si falta |

Esta matriz debe actualizarse cuando se detecte un cambio de comportamiento. No es una verdad eterna: es el registro de lo verificado en un momento dado.

---

## 7. Cómo verificar un cambio de la API

1. Guardar una respuesta cruda:

   ```bash
   curl -s "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?codigo=CODIGO&ticket=$MERCADO_PUBLICO_TICKET" \
     -o /tmp/respuesta.json
   ```

2. Revisar la envoltura y los campos:

   ```bash
   python -m json.tool /tmp/respuesta.json | head -40
   ```

3. Comparar contra el ejemplo de `metadata.json` de una ejecución anterior.

4. Si hay campos nuevos o renombrados, anotar el hallazgo en `docs/BITACORA.md` y ajustar el código con tolerancia a ambas variantes.

5. Ejecutar los tres modos con una licitación conocida antes de publicar el cambio.

> **Nunca** ejecutar `curl -v` en un equipo compartido sin filtrar el ticket de la salida. La URL completa queda en el historial del shell.

---

## 8. Glosario de referencias

| Término | Significado |
|---|---|
| API v1 | Primera versión pública de la interfaz de datos de Mercado Público |
| Código externo | Identificador visible del proceso, por ejemplo `1234-5-LP26` |
| Envoltura | Objeto JSON con `Cantidad`, `Listado` y metadatos de la consulta |
| JSONP | Variante JSON con callback, pensada para navegadores antiguos |
| Ticket | Credencial personal que autoriza las consultas |
| UTM | Unidad usada para clasificar el tamaño del proceso |
| UNSPSC | Estándar internacional de categorías de productos y servicios |

---

## 9. Cómo citar este proyecto

```text
jmadasme. (2026). Licitaciones Mercado Público — Buscador, Descargador y Monitor
(versión única en la raíz del repositorio). GitHub.
```

Para citar la API o los datos:

```text
Mercado Público, ChileCompra. API de Licitaciones v1.
https://api.mercadopublico.cl/servicios/v1/publico
```

---

## 10. Mantenimiento de estas referencias

- Revisar los enlaces institucionales cada seis meses.
- Confirmar que el PDF incluido sigue correspondiendo a la versión vigente.
- Anotar en la bitácora cualquier endpoint nuevo o descontinuado.
- No eliminar una referencia sin dejar registro de por qué se descartó.
- Mantener separadas las fuentes oficiales de las notas de observación empírica.
