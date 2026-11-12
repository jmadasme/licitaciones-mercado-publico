# Bitácora técnica — Licitaciones Mercado Público

Registro de problemas, decisiones y descartes del proyecto. No es un changelog de funcionalidades: es la memoria de **por qué** el código quedó como quedó, para no repetir discusiones ni reintentar caminos que ya fallaron.

> **Contexto del repositorio:** este proyecto se conserva como una **versión única en la raíz**, sin carpeta `versions/`. Proviene de `jmadasme/licitaciones-mercado-publico`. La documentación se amplió en 2026 sin modificar el código funcional.

---

## 1. Problemas encontrados y cómo se resolvieron

### 1.1 La API devuelve errores con HTTP 200/203

**Síntoma:** una consulta con ticket inválido "funcionaba" a nivel HTTP, pero el programa no encontraba datos y fallaba más adelante con un mensaje confuso.

**Causa raíz:** la API puede responder con un cuerpo `{"Codigo": 203, "Mensaje": "Ticket no válido."}` usando un status de éxito. El código HTTP no alcanza para decidir si la consulta fue válida.

**Solución:** `fetch_licitacion()` y `fetch_archivos()` inspeccionan el JSON. Si aparecen simultáneamente `Codigo` y `Mensaje`, clasifican el error:

- mensaje con "ticket" → `InvalidTicketError`;
- mensaje con "no encontrad" → `LicitacionNotFoundError`;
- otro → `APIError`.

**Lección:** en integraciones con APIs públicas, el status HTTP es solo la primera capa. Hay que validar el contrato del cuerpo.

---

### 1.2 El endpoint de archivos no existe para todas las licitaciones

**Síntoma:** `GET /licitaciones/{codigo}/Archivos.json` devolvía 404 en muchos procesos, y el programa lo trataba como error fatal.

**Causa raíz:** el endpoint no está garantizado para todas las licitaciones ni para todos los estados. La documentación no lo promete como obligatorio.

**Solución:**

1. Se tolera el 404 en silencio: no es un error del usuario.
2. Se agrega `Adjudicacion.UrlActa` como fuente adicional de documentos.
3. Si no hay documentos, se guarda igual `metadata.json` y se muestra el enlace a la ficha web:

   ```
   https://www.mercadopublico.cl/Procurement/Modules/RFB/Details.aspx?q={codigo}
   ```

**Lección:** un 404 en un endpoint opcional no es lo mismo que un 404 en el recurso principal. El código debe distinguir "no existe el documento" de "no existe la licitación".

---

### 1.3 Solo hay una ventana de ~188 licitaciones y no hay búsqueda por texto

**Síntoma:** los usuarios esperaban buscar "sensores" en todo el historial y obtener resultados de años anteriores.

**Causa raíz:** la API v1 expone únicamente el listado reciente y no acepta un parámetro de búsqueda textual.

**Solución:**

1. Se implementó un filtro local sobre `Nombre` y `Descripcion`.
2. Se advierte en la interfaz, antes de buscar, que el universo es acotado.
3. Se agregó el modo monitoreo para acumular oportunidades con el tiempo.
4. Se documentan los límites en README, datasheet y esta bitácora.

**Descartado:** intentar paginar o recorrer fechas antiguas con la v1. No hay evidencia de que el endpoint lo soporte y el intento solo genera tráfico inútil.

**Lección:** cuando la fuente es limitada, la herramienta debe hacer explícito el límite en el punto de uso, no solo en el manual.

---

### 1.4 Campos ausentes, con otra capitalización o anidados

**Síntoma:** `KeyError` y resúmenes con "N/A" aunque el dato existía.

**Causa raíz:** la API no es perfectamente consistente entre el listado y el detalle; algunos campos vienen como `CodigoExterno` y otros como `codigoExterno`, y varios están anidados (`Comprador.NombreOrganismo`, `Fechas.FechaCierre`).

**Solución:**

- Helper `_get_nested()` para rutas con punto.
- Cadenas de `or` para aceptar variantes.
- Valores por defecto explícitos (`"N/A"`, `"Sin nombre"`).
- Formateo defensivo del monto: solo si es numérico y positivo.

**Lección:** los datos externos se tratan como entrada no confiable. La tolerancia debe estar en la capa de presentación, no repartida en todo el código.

---

### 1.5 Riesgo de filtrar el ticket

**Síntoma:** el ticket viaja en la URL y podía terminar en logs, capturas o metadatos.

**Causa raíz:** la API usa autenticación por query string; no hay header ni OAuth.

**Solución:**

1. El ticket se carga desde `.env` o variable de entorno, nunca desde el código.
2. `.env` está en `.gitignore`.
3. `metadata.json` guarda `sha256(ticket)` con prefijo `sha256:`, no el valor.
4. El cliente HTTP enmascara el parámetro `ticket` como `***` antes de loguear.
5. La URL de descarga se construye en memoria y no se persiste.

**Limitación documentada:** `metadata.json` guarda `url_origen` tal como lo entrega la API. Si esa URL incluyera el ticket, quedaría persistida. Por eso se recomienda revisar el JSON antes de compartirlo.

**Lección:** la redacción de secretos debe hacerse en la capa de transporte, no confiar en que cada llamador se acuerde.

---

### 1.6 Descargas interrumpidas y archivos corruptos

**Síntoma:** cortes de red dejaban archivos de tamaño parcial con el nombre final, indistinguibles de una descarga correcta.

**Causa raíz:** escribir directamente sobre el destino no permite saber si el archivo está completo.

**Solución:**

1. Se descarga a `<nombre>.part`.
2. Al terminar, `os.rename()` mueve al nombre definitivo.
3. Ante error de red o HTTP, se elimina el `.part`.
4. Ante `OSError` (disco lleno, permisos), se detienen las descargas restantes.

**Lección:** la escritura atómica es barata y evita una clase entera de errores. Aplicarla también a los JSON de estado sería una mejora pendiente.

---

### 1.7 Nombres de archivo inválidos y colisiones

**Síntoma:** documentos con `/`, `:`, `?` o `|` fallaban al guardarse; dos archivos con el mismo nombre se pisaban.

**Solución:**

- `sanitize_filename()` reemplaza `/ \ : * ? " < > |` por `_`, colapsa espacios y recorta puntos finales.
- `resolve_filename_collision()` agrega `_1`, `_2`, etc. antes de la extensión.
- Si el nombre queda vacío, se usa `archivo_sin_nombre`.

**Deuda detectada:** como la colisión se resuelve antes de comprobar si el archivo existe, la rama `skipped=True` casi nunca se alcanza. El resultado práctico es correcto (se conserva el anterior y se agrega una copia), pero el contador "saltados" del resumen suele quedar en cero. No se corrigió para no alterar el comportamiento documentado.

**Lección:** cuando dos mecanismos cubren el mismo caso (resolver colisión y saltar existente), hay que decidir cuál manda y documentarlo.

---

### 1.8 Códigos de estado duplicados

**Síntoma:** los estados 1, 5 y 11 aparecen todos como "Publicada"; el filtro de vigentes solo consideraba el 5.

**Causa raíz:** el portal usa códigos distintos para variantes internas del mismo estado.

**Decisión:** mantener `CodigoEstado == 5` como criterio conservador y documentarlo. Ampliarlo a `{1, 5, 11}` es una receta de extensión, pero no se aplicó porque cambiaría qué procesos se muestran sin evidencia suficiente sobre el significado de cada variante.

**Lección:** ante datos ambiguos, es preferible una decisión conservadora y explícita que una interpretación optimista silenciosa.

---

### 1.9 La interfaz es interactiva y se quiere automatizar

**Síntoma:** cron y systemd no pueden elegir la opción `3` del menú; el proceso queda esperando entrada y termina por EOF.

**Causa raíz:** `main.py` fue diseñado como CLI conversacional, no como comando con argumentos.

**Solución documentada:**

- Ejecutar el modo 3 dentro de `tmux`/`screen` para sesiones largas.
- Para automatización real, usar un envoltorio que importe `buscar_licitaciones()` y escriba su propio reporte.
- Se documentan ejemplos de cron, systemd y Programador de tareas, con la advertencia explícita de que el menú no es apto para ejecución desatendida.

**Descartado por ahora:** reescribir la interfaz con `click` o `typer`. Agrega dependencias y cambia la experiencia sin resolver el problema de fondo (falta de un entrypoint no interactivo).

**Lección:** una herramienta interactiva puede ser excelente para uso manual y pésima para automatización. Son dos contratos distintos y conviene declararlo.

---

### 1.10 Persistencia del monitoreo

**Síntoma:** sin memoria, cada ciclo reportaba las mismas licitaciones.

**Solución:** `descargas/monitoreo_vistos.json` con un `set` serializado como lista. Se actualiza al final de cada ciclo.

**Limitaciones aceptadas:**

- No hay escritura atómica: un corte a mitad de escritura puede corromper el JSON. El siguiente ciclo lo detecta y reinicia el registro.
- El archivo crece indefinidamente.
- Borrarlo hace que todo se reporte como nuevo.

**Lección:** para estado pequeño, un JSON simple es suficiente; si se vuelve crítico, conviene escritura atómica y poda por antigüedad.

---

### 1.11 Límites de tasa desconocidos

**Síntoma:** no hay documentación pública sobre cuántas peticiones por minuto tolera la API.

**Solución defensiva:**

- Pausa de 1 a 2 segundos con jitter entre peticiones.
- Pausa de 1 a 2 segundos entre archivos.
- Backoff exponencial 1/2/4 s en reintentos.
- Espera de 5 s ante HTTP 429.
- Sin descargas en paralelo.
- Recomendación de no ejecutar dos instancias con el mismo ticket.

**Lección:** cuando el límite es desconocido, la estrategia correcta es parecerse a un humano lento, no a un cliente optimizado.

---

### 1.12 Codificación y consola

**Síntoma:** caracteres raros al mostrar nombres con tildes o símbolos en Windows.

**Solución:** archivos en UTF-8, `ensure_ascii=False` en los JSON y recomendación de `chcp 65001` con Windows Terminal. La sanitización no elimina caracteres Unicode: solo los reservados por el sistema de archivos.

**Lección:** UTF-8 en disco no garantiza UTF-8 en la consola; son dos capas distintas.

---

## 2. Enfoques descartados y por qué

| Enfoque | Por qué se descartó |
|---|---|
| Selenium / Playwright sobre el portal | Frágil ante cambios de HTML, pesado, innecesario si existe API, y con implicancias de términos de uso |
| Scraping con BeautifulSoup | Mismo problema de fragilidad; además el portal requiere navegación y sesión |
| Base de datos SQLite | El volumen es bajo y el estado es naturalmente archivos; agrega complejidad operativa |
| `asyncio` + `aiohttp` | El cuello de botella es la tasa permitida, no la concurrencia; complica el código sin beneficio |
| Descargas en paralelo | Aumenta el riesgo de 429 y de agotar disco; el orden secuencial es más predecible |
| Framework CLI (`click`, `typer`) | Dependencia extra para un menú de cuatro opciones |
| Guardar el ticket en `metadata.json` | Riesgo de filtración; se reemplazó por hash |
| Usar HTTP en lugar de HTTPS | Expone el ticket y los documentos; nunca es una solución aceptable |
| Paginar el historial con la v1 | No hay evidencia de soporte; generaría tráfico inútil |
| Filtrar por descripción en el listado | El listado no siempre trae la descripción completa; se resuelve al abrir el detalle |
| Renombrar archivos con hash | Dificulta la lectura humana; se prefirió sanitización + sufijo numérico |
| Notificaciones push integradas | Fuera del alcance; se documenta como extensión |

---

## 3. Decisiones técnicas y su justificación

| Decisión | Alternativa considerada | Motivo |
|---|---|---|
| Monolito modular | Microservicios | Un solo usuario, un solo proceso; la separación en módulos basta |
| `requests.Session` | `urllib` o `httpx` | Conexiones reutilizadas, API conocida, sin dependencias pesadas |
| Cliente HTTP propio con retry | `urllib3.Retry` | Se necesita rate limiting por intento y detección de errores en el cuerpo |
| Backoff 1/2/4 s | Retry inmediato | Evita ráfagas y da tiempo a la API a recuperarse |
| Jitter de 1–2 s | Pausa fija | Evita un patrón perfectamente periódico |
| JSON para metadatos | SQLite, CSV | Legible, portable, inspeccionable con `jq` |
| Hash del ticket | Guardar el ticket | Trazabilidad sin secreto |
| `.part` + rename | Escritura directa | Evita archivos corruptos con nombre final |
| Filtro de vigentes por código 5 | Todos los estados | Conservador y documentado |
| Monitoreo cada 30 min | 5 min o tiempo real | La API no es un flujo de eventos; 30 min reduce carga |
| Menú interactivo | CLI con argumentos | Prioridad a la usabilidad manual; la automatización queda documentada como pendiente |
| Términos fijos en monitoreo | Configuración externa | Simplicidad; se pueden reemplazar al iniciar |
| Sin tests automatizados | Suite con pytest | Deuda reconocida; se priorizó la entrega funcional |

---

## 4. Lecciones aprendidas

1. **El status HTTP no es el contrato.** Validar siempre el cuerpo y la forma de los datos.
2. **Los límites de la API son parte del producto.** Si el usuario no los ve en la interfaz, va a concluir que la herramienta está rota.
3. **Diseñar para el fallo parcial.** Un archivo que falla no debe tirar abajo una licitación; una licitación que falla no debe tirar abajo el monitoreo.
4. **Redactar secretos en la capa correcta.** Un helper central evita olvidos repartidos.
5. **La escritura atómica es una inversión pequeña con retorno alto.**
6. **El estado en archivos simples es suficiente** para volúmenes personales; no conviene adelantar complejidad.
7. **Documentar las decisiones conservadoras** evita que alguien las "corrija" sin contexto.
8. **Una interfaz interactiva no es automatizable por accidente.** Si se necesita cron, hace falta un entrypoint distinto.
9. **La documentación de una API pública envejece.** Verificar contra respuestas reales antes de confiar en un campo.
10. **Sin pruebas, cada refactor es una apuesta.** La próxima iteración debería empezar por `pytest` en utils, filtros y metadata.

---

## 5. Preguntas abiertas

- ¿Los estados 1 y 11 se comportan igual que el 5 en cuanto a vigencia real?
- ¿El parámetro `fecha=DDMMAAAA` funciona de forma consistente y en qué zona horaria?
- ¿Existe un límite de tasa documentado o publicado en algún canal de soporte?
- ¿Qué determina que `Archivos.json` exista para un proceso y para otro no?
- ¿La API puede devolver URLs de descarga que ya incluyan el ticket?
- ¿Cuál es la vía recomendada para obtener historial: datos abiertos, otro endpoint o acumulación local?
- ¿Conviene migrar el monitoreo a un módulo propio antes de agregar argumentos CLI?

Estas preguntas no bloquean el uso actual, pero deberían resolverse antes de una versión 2.

---

## 6. Cómo actualizar esta bitácora

- Agregar una entrada por cada problema relevante, con síntoma, causa, solución y lección.
- Registrar también los enfoques descartados: evita que futuros contribuyentes los reintenten.
- No borrar decisiones antiguas: si cambian, marcar la nueva como reemplazo.
- Mantener las fechas solo cuando se conozcan con certeza; si no, usar el contexto de la versión.
- Enlazar a los archivos y funciones involucrados.
- No incluir tickets, rutas personales ni datos de clientes.

---

## 7. Estado del proyecto

| Aspecto | Estado |
|---|---|
| Versión | Única, en la raíz del repositorio |
| Código funcional | Estable, sin cambios durante la ampliación documental de 2026 |
| Documentación | README, datasheet, developer, referencias y esta bitácora |
| Pruebas | Manuales; automatización pendiente |
| Dependencias | `requests`, `python-dotenv`, `tqdm` |
| Licencia | MIT (2026 jmadasme) |
| Dependencia externa | API de Mercado Público v1, ticket obligatorio |

La herramienta cumple su objetivo: reducir el tiempo entre la publicación de una licitación y su revisión. Todo lo demás es mejora incremental.
