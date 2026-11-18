# 01 · Decisiones del reencuadre (fase 0)

Fecha: 2026-11-18 · Estado: aceptado

Decisiones cerradas al replantear el proyecto desde cero. Sustituyen al plan anterior (operaciones de edificios con Parte A de inventario y Parte B de incidencias). Todo el escenario es ficticio y las cifras son supuestos del ejercicio, no mediciones.

Tras una revisión se añadieron D33 y D34 y se ajustaron D24 y D30 (ver el apartado [Cambios tras la revisión](#cambios-tras-la-revisión)).

Tras el diseño (fase 2), el campo "Pendiente o a validar" de cada decisión afectada remite a [04-solution-design.md](04-solution-design.md) o al ADR donde se cerró o se modificó.

## 1. Enfoque y caso

### D01 · Enfoque del proyecto

**Decisión:** un único caso integrado, con un flujo vertical de principio a fin: discovery, diseño, construcción, evaluación, adopción y portfolio. La IA forma parte de la solución desde el diseño, combinada con reglas, revisión humana y evaluación.

**Justificación:** un proyecto así pide entender un proceso, diseñar un workflow con IA, conectarlo a sistemas, medirlo y explicar su adopción. Una sola historia muestra criterio; una lista de tecnologías sueltas, no.

**Alternativas descartadas:** dos historias separadas (migración + proceso operativo) con el mismo peso; "reglas primero y la IA solo si los datos lo justifican" como principio de arranque; una plataforma general con RAG o agentes como pieza central.

**Pendiente o a validar:** nada.

### D02 · Retirada

### D03 · Caso elegido

**Decisión:** entrada automatizada de pedidos B2B que llegan por email en un distribuidor de suministros industriales. Cada correo acaba como pedido validado en el ERP con confirmación al cliente, como petición concreta de datos al cliente o como excepción para una persona.

**Justificación:**
- Es un proceso real y muy extendido (en distribución, gran parte de los pedidos de clientes pequeños y medianos llegan por email), con proveedores comerciales que se dedican a resolverlo.
- Tiene un principio y un final claros, y en la demo se ve un resultado tangible.
- Combina las tres piezas del caso: extracción con IA, reglas contra datos maestros y revisión humana.
- Los errores se miden línea a línea.
- La migración de datos maestros encaja de forma natural.

**Alternativas descartadas:**
- Incidencias de mantenimiento en edificios: la decisión final es solo clasificar y enrutar, con poca validación contra datos.
- Siniestros de seguros: dominio complejo, datos sensibles y poco que automatizar de forma honesta.
- Facturas de proveedores: muy visto y dependiente de leer PDFs.
- Fugas de facturación SaaS y migración SaaS como caso principal: encajan peor con el caso.

**Pendiente o a validar:** nada.

### D04 · Cómo se demuestra el valor

**Decisión:** el valor no se demuestra con euros calculados sobre datos sintéticos, sino con la calidad medida sobre un conjunto etiquetado y el cronómetro. El business case proyecta horas y coste con supuestos explícitos, en rango, e incluye la comparación comprar o construir frente a soluciones comerciales.

**Justificación:** en datos sintéticos, los "euros detectados" los pone quien diseña los datos y solo demuestran que las reglas encuentran lo plantado. Estimar horas, coste y retorno con supuestos declarados es lo que necesita quien decide. Cualquier comité preguntaría primero por qué no comprar una solución existente.

**Alternativas descartadas:** elegir el caso por "valor calculable en la demo"; dar una cifra única de ahorro.

**Pendiente o a validar:** las cifras de los proveedores comerciales que se usen como contexto se etiquetan como material de marketing, no como datos.

## 2. Escenario

### D05 · Empresa y contexto

**Decisión:** Orvalle Suministros Industriales, S.L. (ficticia). Distribuidor de tornillería, EPIs, herramienta y consumibles, con sede y almacén en un polígono del Vallès (Barcelona). El proyecto arranca porque la dirección prevé crecer un 20 % sin contratar más personal en administración de ventas y quiere que ese equipo dedique tiempo al seguimiento de clientes.

**Justificación:** es un sector realista, con volumen de pedidos repetitivos y un motivo de negocio creíble.

**Alternativas descartadas:** facility services (el caso anterior).

**Pendiente o a validar:** solo se ha hecho una búsqueda rápida del nombre "Orvalle" en el sector, sin coincidencias; no es una comprobación exhaustiva.

### D06 · Cifras del escenario (supuestos)

**Decisión:**

| Dato | Valor |
|---|---|
| Plantilla / facturación | ~60 personas / ~15 M€ |
| Catálogo | 6.000 referencias; ~2.500 se venden habitualmente |
| Clientes activos | ~900 (talleres, mantenimiento industrial, pequeñas fábricas, instaladores) |
| Grandes cuentas | 25, por EDI o portal (fuera de alcance) |
| Pedidos por email | ~1.800/mes ≈ 90/día, con picos los lunes y después de festivos |
| Líneas por pedido | media de 4 (de 1 a 25) |
| Formato | 45 % texto en el correo · 30 % Excel adjunto · 20 % PDF · 5 % otros |
| Correos en pedidos@ | 80 % pedidos nuevos · 8 % cambios o anulaciones · 12 % otros |
| Tiempo manual | ~6 min por pedido → ~180 h/mes ≈ 32 % del tiempo del equipo de administración de ventas |
| Corte logístico | lo que entra en el ERP antes de las 13:00 sale el mismo día |

**Justificación:** son cifras coherentes entre sí. El corte de las 13:00 da un valor concreto a la rapidez.

**Alternativas descartadas:** —

**Pendiente o a validar:** todas son supuestos que se contrastan en el taller de descubrimiento simulado.

### D07 · Roles

**Decisión:**
- **Administración de ventas** (1 responsable y 3 gestoras): procesa pedidos@, define las reglas operativas y usa la revisión.
- **Comerciales** (5): pactan tarifas, cada uno en su propio Excel, y reenvían pedidos.
- **Dirección comercial:** dueña de precios, sustitutos y umbral de importe.
- **Finanzas:** bloqueos de clientes.
- **Dirección de operaciones:** patrocina el proyecto.
- **IT** (1 persona + partner del ERP): permisos e integración.
- **Almacén:** fuera de alcance.

**Justificación:** cada regla tiene un dueño que la confirma; así queda claro quién decide qué.

**Alternativas descartadas:** —

**Pendiente o a validar:** —

### D08 · Sistemas y alcance de formatos

**Decisión:** Google Workspace (buzón compartido pedidos@ y Excels en Drive), ERP simulado y CRM sencillo (de donde sale la exportación de contactos). La demo cubre texto y Excel (75 % de los pedidos). El PDF queda para la fase 2 y se envía a revisión como formato no soportado. El EDI queda fuera.

**Justificación:** empezar por lo más estándar y medir antes de ampliar, como en un proyecto real.

**Alternativas descartadas:** incluir PDF desde el principio.

**Pendiente o a validar:** —

## 3. Parte A: datos maestros

### D09 · Qué se migra

**Decisión:** el ERP simulado se inicializa con su exportación de productos y clientes, que tiene pocos errores. Lo que se migra de verdad son los datos que viven fuera del ERP:
- **Productos:** exportación del ERP en CSV (`;`, latin-1, decimal con coma).
- **Clientes y direcciones de entrega:** exportación del ERP y un Excel de administración de ventas con las direcciones secundarias.
- **Contactos:** exportación del CRM. Sirven para identificar al cliente por el remitente.
- **Tarifas pactadas:** 5 Excels, uno por comercial, cada uno con su estilo.
- **Equivalencias de referencias** (cliente → Orvalle): la "chuleta" de administración de ventas y columnas sueltas en los Excels.

**Justificación:** sin estos datos, la automatización no puede validar nada. Es la "configuración del cliente" previa a la puesta en marcha, más realista y más pequeña que migrar un ERP entero.

**Alternativas descartadas:** migración completa de ERP; eliminar la Parte A.

**Pendiente o a validar:** modificada por D35 ([03-discovery-workshop.md](03-discovery-workshop.md)): las equivalencias salen de 3 chuletas en Word, una por gestora. Ampliada en el diseño ([04](04-solution-design.md#53-tablas)): se carga también el histórico de pedidos de los últimos 6 meses (cabecera y líneas).

### D10 · Errores que se plantan

**Decisión:**
- Caracteres rotos por la codificación y códigos con espacios.
- Unidades escritas de varias formas.
- Descatalogados sin sustituto.
- CIF con y sin guion, y código postal sin el 0 inicial.
- Nombre de empresa en texto libre, emails duplicados y buzones genéricos.
- Tarifas que mezclan % de descuento y precio neto, vigencias en formatos distintos o ausentes, y notas dentro de celdas de precio.
- El mismo cliente y producto con dos precios distintos.
- Equivalencias ambiguas o que apuntan a descatalogados.

**Justificación:** son errores habituales en implantaciones reales.

**Alternativas descartadas:** —

**Pendiente o a validar:** catálogo cerrado en [05](05-synthetic-data-and-evaluation-set.md): 39 tipos, con anclas para la Parte B y controles (filas raras pero válidas).

### D11 · Cómo se carga

**Decisión:**
- **Orden:** productos → clientes → contactos → tarifas → equivalencias.
- **Volumen de la demo:** ~500 referencias y ~120 clientes, como subconjunto declarado.
- **Fila válida:** se carga.
- **Error de formato corregible:** se normaliza, se carga y queda registrado como aviso.
- **Fila inválida:** se rechaza y va al informe.
- **Duplicado o conflicto:** no se carga y va a revisión. Nunca se fusiona automáticamente.
- **Nota en una celda de precio:** se carga el precio y la nota va a revisión.
- **Se puede repetir sin duplicar:** se inserta o se actualiza por clave natural.
- **Mapeo configurable:** un archivo por fuente, más un documento de mapeo que valida el "cliente".
- **Informe por ejecución:** CSV con fichero, fila, campo, valor original, problema y acción, más un resumen.
- Las decisiones de revisión quedan registradas, para que una nueva carga no vuelva a preguntar lo mismo.

**Justificación:** una migración se ejecuta varias veces (prueba, ensayo y definitiva). Fusionar mal es caro y difícil de deshacer; revisar cuesta poco y pasa una vez.

**Alternativas descartadas:** fusión automática de duplicados; carga de todo o nada.

**Pendiente o a validar:** el orden termina con el histórico de pedidos, sin errores plantados ([04](04-solution-design.md#53-tablas)). Corregida en la fase 3 ([05](05-synthetic-data-and-evaluation-set.md)):
- **Nota en una celda de precio:** la tarifa se carga como `pendiente`, y R11 no la usa hasta que se resuelve la revisión. Cargar el precio sin más era peligroso cuando la nota es una condición ("4,20 si >100 uds").
- **Vigencia ausente:** se carga hasta la fecha de la migración + 90 días, con aviso. Un precio sin caducidad podría salir en automático cuando ya no vale.
- Las decisiones de revisión de la demo están en un fichero fijo que hace de ADV.

### D12 · Herramienta de la Parte A

**Decisión:** Python (pandas + rapidfuzz). En la Parte A no hay IA, por decisión deliberada.

**Justificación:** es un proceso por lotes que debe ser reproducible, versionado y con tests. n8n sirve para orquestar eventos, no para transformar miles de filas con un informe de errores. Power Query sirve para explorar, no para cargar por API. Las reglas y las coincidencias aproximadas resuelven el problema sin IA.

**Alternativas descartadas:** n8n, Power Query, IA para el mapeo.

**Pendiente o a validar:** una de las chuletas está en prosa. Lo que la migración no interpreta va al informe y se transcribe a mano; sigue sin IA ([05](05-synthetic-data-and-evaluation-set.md)).

## 4. Parte B: flujo de pedidos

### D13 · Tipos de correo y tratamiento

**Decisión:**

| Tipo | Tratamiento | Automático |
|---|---|---|
| Pedido nuevo | Extracción y validación → una de 3 salidas (D14) | Sí, cuando está claro |
| Modificación o anulación | Busca el pedido original, prepara el cambio propuesto y lo manda a revisión | No |
| Consulta | Se etiqueta y pasa a administración de ventas, sin respuesta automática | No (posible fase futura) |
| Reclamación | Se etiqueta como prioritaria y pasa a una persona | Nunca |
| No es pedido | Las facturas se reenvían a contabilidad y el spam se archiva, con registro | Sí |

La IA clasifica entre estos tipos; si no está segura, el correo va a revisión, nunca a "spam".

**Justificación:** solo se automatiza lo claro y de bajo riesgo. Modificar un pedido que puede estar ya en preparación es caro.

**Alternativas descartadas:** responder consultas automáticamente; aplicar modificaciones de forma automática.

**Pendiente o a validar:** las modificaciones están en la lista de recortes si falta tiempo.

### D14 · Las tres salidas de un pedido nuevo

**Decisión:**
- **Automático:** se crea el pedido en el ERP y se envía la confirmación.
- **Pedir datos:** cuando falta algo que solo sabe el cliente.
- **Revisión interna:** cuando hay que tomar una decisión de negocio o hay riesgo.

**Justificación:** el criterio es quién tiene la información y la autoridad. Al cliente solo se le pregunta lo que solo él sabe; las decisiones comerciales, como aceptar un precio, las toma alguien de Orvalle.

**Alternativas descartadas:** preguntarle todo al cliente; mandarlo todo a revisión.

**Pendiente o a validar:** —

### D15 · Pedido con alguna línea dudosa

**Decisión:** el pedido se retiene entero.

**Justificación:** crear pedidos parciales genera duplicados cuando llega la respuesta del cliente y lía al almacén.

**Alternativas descartadas:** crear el pedido parcial y añadir la línea después.

**Pendiente o a validar:** —

### D16 · Casos reales que el flujo debe aguantar

**Decisión:**
- **Pedido reenviado por un comercial:** se identifica al cliente original desde el hilo; la confirmación va al cliente con el comercial en copia.
- **Pedido duplicado** (llega a pedidos@ y además lo reenvía el comercial): va a revisión.
- **"Repite el pedido X":** se monta si cita un número; si es vago, va a revisión.
- **Varios pedidos en un correo:** van a revisión en la demo.

**Justificación:** son las situaciones que hacen creíble el escenario.

**Alternativas descartadas:** dividir automáticamente un correo con varios pedidos (queda como mejora).

**Pendiente o a validar:** —

### D17 · Estados y trazabilidad

**Decisión:** cada correo pasa por estos estados: recibido → clasificado → (automático | pendiente del cliente | en revisión | derivado) → pedido creado / descartado. Se guarda el correo original tal cual y un registro de eventos de cada paso: clasificación, extracción, reglas evaluadas, decisión y quién aprueba.

**Justificación:** así se sabe cuántos correos hay sin procesar y se puede reconstruir y explicar cualquier pedido (gobierno del dato).

**Alternativas descartadas:** —

**Pendiente o a validar:** sustituida en el diseño por los estados de [04, sección 2.5](04-solution-design.md#25-estados-del-caso): "automático" pasa a ser una salida, no un estado, y se añade `cerrado` con su resultado.

## 5. Reglas de decisión

### D18 · Reglas, orden y dueños

**Decisión:**

| ID | Regla | Si falla | Confirma |
|---|---|---|---|
| R01 | Es un pedido nuevo (clasificación con señales claras) | Revisión | Responsable de administración de ventas |
| R02 | El email del remitente coincide exactamente con un contacto de un único cliente | Revisión (se da de alta el contacto) | Responsable de administración de ventas |
| R03 | En un reenvío interno, el cliente original cumple R02 | Revisión | Responsable de administración de ventas |
| R04 | Cliente no bloqueado | Revisión | Finanzas |
| R05 | Dirección de entrega única o indicada | Pedir datos | Responsable de administración de ventas |
| R06 | Fecha posible; si no indica fecha, la estándar | Pedir datos | Responsable de administración de ventas |
| R07 | No es duplicado (mismo número de pedido del cliente, o mismas líneas en menos de 48 h) | Revisión | Responsable de administración de ventas |
| R08 | Referencia por código exacto o equivalencia → OK; solo por descripción → revisión; no encontrada → pedir datos | Según el caso | Responsable de administración de ventas |
| R09 | Producto activo; descatalogado → revisión | Revisión | Dirección comercial |
| R10 | Cantidad ≥ mínimo y múltiplo del embalaje | Pedir datos | Responsable de administración de ventas |
| R11 | Sin precio → tarifa pactada vigente o general; mismo precio → OK; precio distinto → revisión | Revisión | Dirección comercial |
| R12 | Extracción de la línea fiable según señales comprobables | Revisión | Responsable de administración de ventas |
| R13 | Importe total ≤ 3.000 € | Revisión | Dirección comercial |

R01–R04 cortan el flujo. R05–R13 se evalúan todas y se acumulan los motivos. Si hay algún motivo de revisión, el pedido va a revisión. Si solo faltan datos, se envía un único correo de petición. Si no hay ningún motivo, es automático.

**Justificación:** se automatiza cuando un error es barato y reversible, y va a revisión cuando es caro o difícil de deshacer. Los umbrales arrancan conservadores y se relajan solo con datos de la evaluación.

**Alternativas descartadas:** R10 con redondeo al alza y aviso al cliente (arriesga devoluciones).

**Pendiente o a validar:** el umbral de 3.000 € lo confirma dirección comercial en el taller (sesión 7), donde también se fijan la tolerancia de R11 y los sustitutos de R09 ([03-discovery-workshop.md](03-discovery-workshop.md)). Sigue siendo un supuesto que ~3-5 % de los pedidos lo superen. Revisada en el diseño ([04, sección 3](04-solution-design.md#3-reglas)): cambios en R02, R04, R05, R10, R11 y R13, nueva R14 (cantidad anómala), motivos M01–M05 y qué motivos puede forzar ADV.

### D19 · Confianza de la IA

**Decisión:** no se usa la "confianza" que declara el modelo. R12 se basa en señales comprobables: coincidencia exacta de código o equivalencia, JSON válido contra el esquema, cantidad numérica limpia, línea presente literalmente en la entrada.

**Justificación:** la confianza que declara el modelo no está calibrada y suele ser demasiado optimista.

**Alternativas descartadas:** un umbral sobre la confianza declarada por el modelo.

**Pendiente o a validar:** la evaluación debe comprobar qué señales predicen de verdad los errores.

### D20 · Mejora continua de R08

**Decisión:** cada corrección en la revisión se guarda como equivalencia para ese cliente. La revisión por descripción se relaja solo para los casos en que la evaluación demuestre un acierto muy alto (p. ej., ≥ 98 % con un único candidato).

**Justificación:** el modelo no aprende solo; lo que mejora son los datos y las reglas que lo rodean.

**Alternativas descartadas:** fiarse de que la IA "esté segura".

**Pendiente o a validar:** el umbral concreto se fija tras la evaluación.

### D21 · Prioridad de la cola de revisión

**Decisión:** la asigna el sistema. Primero las reclamaciones, después los pedidos que todavía llegan al corte de las 13:00, y el resto por antigüedad. Un "URGENTE" del remitente se registra pero no altera la prioridad; una fecha pedida es un dato del pedido.

**Justificación:** se mantiene la decisión previa: la prioridad la asigna el sistema con reglas, nunca el remitente.

**Alternativas descartadas:** prioridad declarada por el cliente.

**Pendiente o a validar:** la prioridad se calcula al consultar la cola, no se guarda ([04, sección 2.2](04-solution-design.md#22-flujo-paso-a-paso)).

## 6. Datos mínimos

### D22 · Mínimos y qué pasa si faltan

**Decisión:**

Pedido nuevo:
- Cliente obligatorio; si falta, revisión.
- Al menos una línea con referencia y cantidad; si falta, pedir datos.
- Dirección obligatoria salvo que el cliente solo tenga una; si falta, pedir datos.
- Fecha, número de pedido del cliente, precio y observaciones son opcionales, con valor por defecto.

Modificación: identificar el pedido original y qué cambia; lo que falte lo completa la revisión.

Consulta, reclamación u otros: sin mínimos.

Correo de "pedir datos":
- Es uno solo, va en el mismo hilo y cita la referencia del cliente.
- Dice qué falta exactamente y en qué línea.
- No promete plazos.
- Sin respuesta en 24 h, o con respuesta incompleta, el pedido pasa a revisión. Nunca se repregunta de forma automática.

**Justificación:** se evitan bucles de correos automáticos y peticiones sueltas.

**Alternativas descartadas:** un correo por cada dato que falta; recordatorios automáticos.

**Pendiente o a validar:** ampliada en el diseño ([04, sección 4](04-solution-design.md#4-datos-mínimos)): unidad, observaciones, respuesta del cliente, opciones cerradas en la petición y "o indíquenos otra".

## 7. Evaluación

### D23 · Conjuntos de datos

**Decisión:**
- **Conjuntos:** 20 correos de desarrollo (para ajustar) y 60 de prueba (se ejecutan solo al final). Si se cambia algo después de la prueba, se declara.
- **Mezcla de la prueba:** 42 pedidos nuevos (18 en texto, 14 en Excel, 5 reenviados, 3 en PDF, 2 "repite el pedido X"), 6 modificaciones, 4 consultas, 3 reclamaciones y 5 que no son pedido.
- **Trampas obligatorias:** duplicados, buzón genérico, cliente bloqueado, precio distinto, más de 3.000 €, descatalogado, cantidad que no encaja con el embalaje y "adjunto pedido" sin adjunto.
- **Etiquetas:** tipo, salida, motivos, cabecera y líneas.

**Justificación:** separar desarrollo y prueba evita "estudiar el examen". La mezcla está enriquecida con casos difíciles a propósito.

**Alternativas descartadas:** un conjunto único; una mezcla que replique la realidad.

**Pendiente o a validar:** el % automático de la prueba no se traslada tal cual; se recalcula con la mezcla del escenario. Concretada en [05](05-synthetic-data-and-evaluation-set.md): trampas combinadas en el mismo correo cuando es natural, cuatro tipos de trampa solo en la prueba, respuestas del cliente y una respuesta automática como casos con varios `.eml`, y la prueba congelada con un manifiesto de hashes. Las etiquetas llevan además si la revisión era necesaria y las salidas aceptables.

### D24 · Quién escribe los correos

**Decisión:** la mayoría se generan con IA, usando un modelo distinto del que hace la extracción. David escribe unos 15 a mano, imitando cómo escriben los clientes reales, y revisa todos.

**Justificación:** si la misma IA que procesa los correos los escribe todos, salen demasiado "limpios" y los resultados quedan inflados. Usar un modelo distinto para generar reduce los sesgos compartidos entre generación y extracción, y los correos escritos a mano añaden la variedad que ningún modelo imita bien.

**Alternativas descartadas:** todos generados por IA; todos escritos a mano; generar con el mismo modelo que extrae.

**Pendiente o a validar:** cerrada en el [ADR 0005](decisions/0005-modelo-de-ia.md), revisado el 19-11-2026 por el requisito de gratuidad: extrae Gemini y los correos los genera Claude. David escribe ~15: 12 con ficha (incluidos los de catalán) y 3 libres ([05](05-synthetic-data-and-evaluation-set.md)).

### D25 · Métricas y comparación

**Decisión:**

Métricas:
- **Métrica crítica:** pedidos automáticos con algún error (objetivo: 0), junto con los casos que debían ir a revisión y salieron automáticos.
- Acierto de la salida y del tipo, con tabla de confusión.
- Líneas correctas.
- % automático y % de revisión por motivo.
- Revisiones innecesarias.
- Calidad del correo de pedir datos.
- Coste y tiempo por correo.

**Comparación:** solo reglas, solo IA e híbrido sobre el mismo conjunto de prueba. Las reglas deciden siempre; lo que cambia es la extracción y la clasificación. Cada configuración con IA se ejecuta 3 veces.

**Cronómetro:** 20 correos a mano y 20 con la demo, distintos pero equivalentes. Es la medición de una sola persona y no se puede generalizar.

**Análisis de errores:** cada fallo se analiza uno a uno (extracción, regla o dato maestro).

**Justificación:** "uso IA" pasa de afirmación a criterio demostrado.

**Alternativas descartadas:** medir solo el acierto global.

**Pendiente o a validar:** que el híbrido gane es una hipótesis. En el diseño, las tres configuraciones son dos interruptores sobre las mismas piezas, y una evaluación completa son 420 ejecuciones ([04, sección 7](04-solution-design.md#7-cómo-se-evalúa-este-diseño)). Las revisiones innecesarias se miden con un campo propio en la etiqueta, y si hay correcciones de etiquetas después de la prueba, las métricas se publican con las dos versiones ([05](05-synthetic-data-and-evaluation-set.md)).

### D26 · Presentación del valor

**Decisión:** en tres capas etiquetadas:
1. Lo medido en la demo, con el número de casos y sus límites.
2. La proyección, en rango pesimista y central, con sensibilidad.
3. Lo que no se puede afirmar: el ahorro real, la adopción y el rendimiento con datos reales.

Un 70 % de pedidos automáticos no es un 70 % de tiempo ahorrado: lo automático es lo fácil, la revisión también cuesta y la mezcla de la prueba no es la real. La forma de validarlo sería un piloto en paralelo de 2-4 semanas.

**Justificación:** honestidad y credibilidad ante un comité de dirección.

**Alternativas descartadas:** una cifra única de ahorro.

**Pendiente o a validar:** —

## 8. Solución, plan y repositorio

### D27 · Stack provisional

**Decisión:**
- n8n como orquestador.
- Gmail y Drive de una cuenta de prueba.
- Supabase como ERP simulado (base de datos, API REST, SQL y roles).
- Python para la migración.
- App de revisión con Lovable o Claude Code.
- SQL comentado con 6-8 preguntas de negocio.

**Justificación:** encaja con el enfoque del proyecto (low-code conectado a herramientas del cliente y prototipos rápidos) sin programar un backend propio.

**Alternativas descartadas:** API propia programada a mano.

**Pendiente o a validar:** confirmado en los ADR [0001](decisions/0001-reglas-en-sql.md)–[0005](decisions/0005-modelo-de-ia.md): n8n autoalojado en Docker con túnel para la demo y la app de revisión en local (una app publicada en la web no llegaría al Supabase local). Revisado el 19-11-2026, **todo el proyecto es gratuito**: Gemini por Google AI Studio en el nivel gratuito como modelo de IA, y la app de revisión hecha con Claude Code, sin Lovable. Nueva consulta SQL: líneas facturadas a un precio que no está en ninguna tarifa cargada ([05](05-synthetic-data-and-evaluation-set.md)).

### D28 · Piezas añadidas al proyecto

**Decisión:** el proyecto incluye:
- priorización de oportunidades por impacto y viabilidad (discovery);
- business case con comprar o construir;
- adopción: guía de una página y guion de una formación de 30 minutos;
- gobierno: permisos por rol, mínimos de datos personales, clasificación según el AI Act (previsiblemente riesgo mínimo) con supervisión humana y registro, y un plan de puesta en marcha en paralelo y después gradual.

**Justificación:** son baratas de hacer y completan el caso.

**Alternativas descartadas:** —

**Pendiente o a validar:** —

### D29 · Fases

**Decisión:**

| # | Fase | Sale |
|---|---|---|
| 0 | Reencuadre | Este documento; plan y repositorio limpios |
| 1 | Discovery | AS-IS, mapa del proceso, oportunidades priorizadas, business case con supuestos |
| 2 | Diseño | TO-BE, reglas, datos mínimos, criterios de aceptación, stack (ADR). Los requisitos van integrados aquí |
| 3 | Datos y evaluación | Datos sintéticos y casos etiquetados, antes de construir |
| 4 | Construcción | Ver orden más abajo |
| 5 | Evaluación | Comparación de configuraciones, cronómetro, coste por caso |
| 6 | Adopción y gobierno | Guía, formación, permisos, AI Act |
| 7 | Portfolio | README, página del caso, vídeo de 3 min |

Orden de construcción:
1. Supabase y la carga de datos maestros.
2. n8n: de Gmail a la extracción con IA en JSON.
3. Reglas y creación del pedido.
4. Respuestas automáticas y excepciones.
5. App de revisión.
6. Consultas SQL.
7. Evaluación.

Cada incremento se cierra con su check y un commit. La demo debe poder enseñarse en directo en 3 minutos.

**Justificación:** un incremento cada vez, y la evaluación antes que el pulido.

**Alternativas descartadas:** el plan anterior de 8 fases con requisitos separados.

**Pendiente o a validar:** sin calendario fijo; la construcción llevará más sesiones que en el plan anterior, sobre todo el incremento de n8n.

### D30 · Recortes si falta tiempo (en este orden)

**Decisión:** PDF → panel → modificaciones de pedido → correos con varios pedidos → app de revisión (se sustituiría por la vista de Supabase). La evaluación no se recorta.

**Plan B del incremento de n8n:** si tras 2 sesiones el incremento de n8n no funciona, el flujo corre como script de Python con los mismos pasos, llamando a las mismas reglas y a la misma extracción (D33). El motivo se documenta en un ADR. n8n sigue siendo la pieza principal del portfolio y el plan B no se activa por comodidad.

**Justificación:** se protege lo que demuestra criterio, y el incremento más arriesgado tiene una salida acotada en el tiempo.

**Alternativas descartadas:** —

**Pendiente o a validar:** el criterio concreto del plan B y lo que se pierde con él están en el [ADR 0003](decisions/0003-n8n-orquestador-plan-b.md).

### D31 · Principios (actualizados)

**Decisión:**
1. **Honestidad:** se distinguen siempre escenario, supuestos, medición y proyección.
2. **Hecho con IA, y se dice:** `AI_USAGE.md`.
3. **Entenderlo todo:** el porqué de cada decisión y preguntas de comprensión. Ante una pregunta, razonar siempre en voz alta.
4. **IA donde aporta:** las reglas son la línea base y el control; las decisiones de negocio nunca las toma solo la IA.
5. **Realismo.**
6. **Una cosa cada vez.**

**Justificación:** el principio 4 sustituye a "reglas primero".

**Alternativas descartadas:** —

**Pendiente o a validar:** —

### D32 · Repositorio

**Decisión:** `b2b-order-intake-automation-case-study`. Documentación de trabajo en español; el idioma del README y de la página del caso se decide en la fase 7.

**Justificación:** "order intake" es el término del sector, se entiende sin abrirlo y no pone "IA" delante.

**Alternativas descartadas:** `email-order-automation-case-study` (suena genérico), `ai-order-entry-automation-case-study` (roza el hype).

**Pendiente o a validar:** —

### D33 · Una sola fuente para reglas y extracción

**Decisión:** las reglas R01–R13 se implementan como funciones SQL en Supabase, y n8n y el script de evaluación las llaman por API. Lo mismo vale para la extracción: el prompt y el esquema JSON viven en un único sitio versionado en el repositorio, y n8n y el script usan exactamente esos. n8n queda como orquestador: recibe el correo, llama a la extracción, llama a las reglas y envía la respuesta.

**Justificación:** la evaluación (60 correos × 3 configuraciones × 3 ejecuciones) es mucho más práctica con un script que con el flujo de Gmail. Si n8n y el script tuvieran cada uno su copia de las reglas o del prompt, se evaluaría algo distinto de lo que funciona.

**Alternativas descartadas:** reglas dentro de nodos de n8n y reimplementadas en el script; prompt copiado en n8n.

**Pendiente o a validar:** confirmada con un cambio en los ADR [0001](decisions/0001-reglas-en-sql.md) y [0002](decisions/0002-prompt-y-esquema-fuente-unica.md): el prompt y el esquema se cargan en una tabla de versiones que leen n8n y el script, y la evaluación no duplica el flujo en un script, sino que entra por una puerta de pruebas del propio flujo de n8n.

### D34 · Reproducible con tus propias claves

**Decisión:** el repositorio se puede ejecutar en local con tus propias claves:
- Supabase local (CLI + Docker) con el esquema, las funciones de reglas y la carga de datos maestros.
- `.env.example` con las variables necesarias; cada persona pone su propia clave del proveedor de IA.
- Los correos de prueba como archivos `.eml` en `data/` y un script que los procesa con las mismas reglas y la misma extracción que n8n (D33).
- Las respuestas de la IA para el conjunto de prueba se guardan en el repositorio, de modo que la evaluación se puede reproducir sin clave ni coste.

El vídeo de 3 minutos enseña el flujo completo con Gmail y n8n; el repositorio demuestra que la lógica funciona y que las métricas publicadas se pueden reproducir.

**Justificación:** con Gmail de prueba, n8n y Lovable, quien abra el repositorio no podría probar nada. Guardar las respuestas de la IA hace que las métricas sean verificables, y no solo creíbles.

**Alternativas descartadas:** un repositorio que solo funciona con las cuentas del autor.

**Pendiente o a validar:** el diseño fija dos niveles de reproducción ([04, sección 7](04-solution-design.md#7-cómo-se-evalúa-este-diseño)). Formato cerrado en [05](05-synthetic-data-and-evaluation-set.md): manifiesto, resultados en JSONL por pasada y respuestas del modelo con clave por hash de la entrada. La clave del proveedor de IA es gratuita (Google AI Studio).

## Cambios tras la revisión

- **D24:** los correos se generan con un modelo distinto del que hace la extracción.
- **D30:** plan B de Python para el incremento de n8n, solo tras 2 sesiones fallidas y con ADR.
- **D33 (nueva):** reglas como funciones SQL; prompt y esquema en un único sitio versionado.
- **D34 (nueva):** reproducible en local con tus propias claves y respuestas de la IA guardadas.

## Acciones en el repositorio

- [x] Renombrar el repositorio.
- [x] Guardar este documento en `docs/` (hoy `01-reframe-decisions.md`).
- [x] Reescribir `00-project-plan.md` según D29–D31.
- [x] Reescribir el caso de negocio (hoy `02-business-case.md`) para el nuevo caso.
- [x] Actualizar `README.md`.
- [x] Preparar el taller de discovery (hoy `03-discovery-workshop.md`, fase 1).
