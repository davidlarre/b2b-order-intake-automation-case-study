# 01 · Caso de negocio — Orvalle Suministros Industriales

## Propósito y naturaleza

Este documento es el caso de negocio inicial de un proyecto educativo de portfolio: la entrada automatizada de pedidos B2B que llegan por email a un distribuidor de suministros industriales. Se completa en la fase de discovery (fase 1).

**Caso ficticio y datos sintéticos.** Orvalle Suministros Industriales, S.L., sus clientes, procesos, sistemas y cifras son inventados. No es un cliente real ni un proyecto profesional ya realizado. Las cifras son supuestos del ejercicio, no mediciones ni investigación de mercado.

Cada cifra lleva su etiqueta:

- **Escenario (D06):** cifra fijada en las decisiones del reencuadre ([0001](decisions/0001-reframe.md)).
- **Derivado:** cálculo a partir de otras cifras.
- **Supuesto (SNxx):** cifra añadida en este documento para poder proyectar. Se recogen todos en [Supuestos de la proyección](#supuestos-de-la-proyección).

## Perfil del cliente y contexto

Orvalle es un distribuidor de tornillería, EPIs, herramienta y consumibles, con sede y almacén en un polígono del Vallès (Barcelona). Sus clientes son talleres, empresas de mantenimiento industrial, pequeñas fábricas e instaladores.

| Dato | Valor | Origen |
|---|---|---|
| Plantilla / facturación | ~60 personas / ~15 M€ | Escenario |
| Catálogo | 6.000 referencias; ~2.500 de venta habitual | Escenario |
| Clientes activos | ~900; las 25 grandes cuentas piden por EDI o portal | Escenario |
| Pedidos por email | ~1.800/mes ≈ 90/día, con picos los lunes y después de festivos | Escenario |
| Correos en pedidos@ | ~2.250/mes (80 % pedidos nuevos, 8 % cambios o anulaciones, 12 % otros) | Derivado |
| Líneas por pedido | media de 4 (de 1 a 25) | Escenario |
| Formato | 45 % texto · 30 % Excel · 20 % PDF · 5 % otros | Escenario |
| Equipo de administración de ventas | 1 responsable y 3 gestoras | Escenario |
| Corte logístico | lo que entra en el ERP antes de las 13:00 sale el mismo día | Escenario |

**Por qué ahora.** La dirección prevé crecer un 20 % sin contratar más personal en administración de ventas, y quiere que ese equipo dedique más tiempo al seguimiento de clientes y menos a teclear pedidos.

## Problema de negocio

Los pedidos de los clientes pequeños y medianos llegan a un buzón compartido en formatos muy distintos: texto libre, Excel propio del cliente, PDF o reenvíos de un comercial. Para cada uno, una gestora tiene que identificar al cliente, traducir las referencias del cliente a las de Orvalle, comprobar precios contra la tarifa pactada (que está en el Excel de cada comercial), revisar cantidades, embalajes y dirección, y teclear el pedido en el ERP.

Además, la información necesaria para validar un pedido no está en el ERP: las tarifas pactadas, las equivalencias de referencias y parte de las direcciones y contactos viven en Excels y en la memoria del equipo.

**Enunciado:** Orvalle dedica en torno a un tercio de la capacidad de administración de ventas a transcribir pedidos, valida contra datos dispersos fuera del ERP y no tiene trazabilidad de qué pasó con cada correo. Con el crecimiento previsto, el proceso actual no escala sin contratar.

Este enunciado es una hipótesis de diseño que se contrasta en el taller de descubrimiento simulado.

## Proceso actual — AS-IS hipotético

1. El cliente envía el pedido a pedidos@ o a su comercial, que lo reenvía.
2. Una gestora abre el correo y decide si es un pedido nuevo, un cambio, una consulta, una reclamación u otra cosa.
3. Identifica al cliente por el remitente o por el texto.
4. Traduce las referencias del cliente con la "chuleta" o buscando por descripción.
5. Comprueba el precio en el Excel del comercial y, si no coincide, pregunta al comercial o a dirección comercial.
6. Si falta algo, escribe al cliente y deja el correo pendiente.
7. Teclea el pedido en el ERP y envía la confirmación.

No hay registro de cuántos correos están sin procesar ni de por qué un pedido se retuvo. Los pasos son una representación inicial; se validan en el taller.

## Objetivos de negocio

- Absorber el crecimiento del 20 % sin contratar en administración de ventas.
- Que los pedidos claros entren en el ERP sin intervención y con confirmación al cliente, con cero pedidos automáticos con errores como objetivo.
- Que más pedidos entren antes del corte de las 13:00.
- Que las excepciones lleguen a la persona adecuada con el motivo explicado, y que al cliente solo se le pregunte lo que solo él sabe.
- Trazabilidad completa de cada correo: qué se extrajo, qué reglas se evaluaron, qué se decidió y quién aprobó.
- Datos maestros (tarifas, equivalencias, contactos y direcciones) cargados y validados en un solo sitio.

## Alcance

**Incluido:**
- **Parte A, datos maestros:** migración de productos, clientes y direcciones, contactos, tarifas pactadas y equivalencias con mapeo, validación, informe de errores y carga repetible (subconjunto de ~500 referencias y ~120 clientes en la demo).
- **Parte B, flujo de pedidos:** clasificación del correo; extracción de pedidos en texto y Excel (75 % de los pedidos); validación con las reglas R01–R13; tres salidas (automático, pedir datos, revisión); cola de revisión; confirmaciones y peticiones de datos; registro de eventos; métricas.

**Fuera de alcance:** PDF en la primera fase (va a revisión como formato no soportado); EDI y grandes cuentas; almacén y preparación; respuestas automáticas a consultas; aplicar modificaciones de pedido sin revisión; datos reales.

## Stakeholders

| Rol | Interés o responsabilidad |
|---|---|
| Dirección de operaciones | Patrocina el proyecto y fija los criterios de éxito |
| Administración de ventas (1 responsable y 3 gestoras) | Procesa pedidos@, define las reglas operativas y usa la revisión |
| Comerciales (5) | Pactan tarifas, reenvían pedidos y reciben copia de las confirmaciones |
| Dirección comercial | Dueña de precios, sustitutos y umbral de importe |
| Finanzas | Bloqueos de clientes |
| IT (1 persona + partner del ERP) | Permisos e integración |

Son roles del escenario ficticio, no personas reales. Cada regla tiene un dueño que la confirma (D18).

## Línea base

| Concepto | Valor | Origen |
|---|---|---|
| Tiempo manual por pedido nuevo | ~6 min | Escenario |
| Carga del proceso | 1.800 × 6 min = 10.800 min ≈ **180 h/mes** | Derivado |
| Capacidad del equipo | 4 personas × ~140 h = ~560 h/mes | Derivado de SN01 |
| Peso sobre el equipo | 180 ÷ 560 ≈ **32 %** | Derivado |
| Carga con +20 % de pedidos y el proceso actual | 2.160 × 6 min ≈ **216 h/mes** (+36 h, ≈ 0,25 personas) | Derivado |

Las 180 h solo cubren los pedidos nuevos (SN02). Cambios, consultas y reclamaciones consumen tiempo aparte que no se proyecta.

## Proyección en rango

Se proyectan las horas del equipo con la solución. No es un resultado: es un cálculo con los supuestos de la tabla siguiente, que la evaluación de la demo (fase 5) y un piloto en paralelo de 2–4 semanas tendrían que confirmar o corregir.

### Supuestos de la proyección

**Todos los supuestos de esta tabla son nuevos y están pendientes de revisión.**

| ID | Supuesto | Pesimista | Central |
|---|---|---|---|
| SN01 | Jornada efectiva por persona en administración de ventas | ~140 h/mes | ~140 h/mes |
| SN02 | Los 6 min por pedido cubren solo pedidos nuevos (lectura, validación, tecleo y confirmación) | — | — |
| SN03 | Pedidos que salen automáticos con la mezcla real del escenario | 30 % | 50 % |
| SN04 | Tiempo residual por pedido automático (consulta del registro, incidencias puntuales) | 0,5 min | 0,5 min |
| SN05 | Tiempo por pedido en revisión o con petición de datos, con los datos ya extraídos | 6 min | 4 min |
| SN06 | Mantenimiento de reglas y equivalencias, y supervisión del flujo | 12 h/mes | 8 h/mes |
| SN07 | Coste empresa por hora de administración de ventas | 28 €/h | 28 €/h |
| SN08 | Coste de implantación en un proyecto real (incluye la integración con el ERP por el partner y la carga de datos maestros) | 12.500 € | 10.000 € |
| SN09 | Coste de funcionamiento (IA, orquestador y mantenimiento técnico menor) | 150 €/mes | 100 €/mes |

El SN03 no sale de la demo: el % automático de la prueba no se traslada tal cual, porque la mezcla está enriquecida con casos difíciles y lo automático es lo fácil (D23, D26). En la fase 5 se recalcula con la mezcla del escenario.

### Resultado

| | Pesimista | Central |
|---|---|---|
| Horas con la solución (1.800 pedidos/mes) | ~143 h | ~76 h |
| Capacidad liberada | **~38 h/mes** (21 %) | **~105 h/mes** (58 %) |
| Horas con la solución y +20 % de pedidos | ~169 h | ~89 h |
| Valor de la capacidad liberada (SN07) | ~1.050 €/mes | ~2.900 €/mes |
| Valor neto de funcionamiento (SN09) | ~900 €/mes | ~2.800 €/mes |
| Recuperación de la implantación (SN08) | ~14 meses | ~3,5 meses |

Cómo se lee:

- **Incluso en el pesimista, el crecimiento del 20 % se absorbe:** ~169 h frente a las 180 h actuales. Este es el objetivo de la dirección, más que el ahorro en euros.
- **La capacidad liberada no es dinero ahorrado.** Solo se convierte en euros si se evita una contratación o el tiempo se dedica a seguimiento de clientes. Los euros de la tabla son el valor de esas horas, no una reducción de costes.
- **Un 50 % automático no es un 50 % de tiempo ahorrado.** La revisión también cuesta y los casos que van a revisión son los más lentos.

### Sensibilidad

Capacidad liberada (h/mes) con 1.800 pedidos y 8 h de mantenimiento, según el % automático y el tiempo de revisión:

| % automático → | 30 % | 40 % | 50 % | 60 % |
|---|---|---|---|---|
| Revisión de 4 min | 84 | 94 | 105 | 115 |
| Revisión de 6 min | 42 | 58 | 75 | 91 |

El tiempo de revisión pesa tanto como el % automático: pasar de 6 a 4 min vale más que subir 20 puntos de automático. Por eso la pantalla de revisión, con los datos ya extraídos y el motivo explicado, es parte del valor, no un accesorio.

## Comprar o construir

Antes de construir, un comité preguntaría por qué no comprar. Opciones:

| Opción | A favor | En contra |
|---|---|---|
| **Seguir igual y reforzar el equipo** (horas extra o media jornada) | Sin riesgo técnico ni cambio de proceso | Coste recurrente que crece con el volumen; no aporta trazabilidad ni datos maestros ordenados |
| **Solución comercial de entrada de pedidos por email** | Producto probado, soporte y mantenimiento del proveedor | Licencia recurrente; integración con el ERP y carga de tarifas y equivalencias igualmente necesarias; menos control sobre las reglas |
| **Portal B2B para clientes** | Pedidos estructurados desde el origen | Exige que ~900 clientes pequeños cambien de hábito; adopción lenta e incierta |
| **Construir con low-code e IA** (este caso) | Reglas propias y explicables; encaja con Google Workspace; coste de funcionamiento bajo | Mantenimiento interno; depende de la calidad de los datos maestros |

En las tres opciones que cambian el proceso, la Parte A (datos maestros ordenados) es necesaria. Por eso se hace primero.

Las cifras de los proveedores comerciales (precios, % de automatización declarados) se recogen en el discovery y se etiquetan como material de marketing, no como datos (D04).

## KPIs

| KPI | Definición | Línea base / seguimiento |
|---|---|---|
| Pedidos automáticos con errores | Pedidos creados sin intervención con algún error ÷ pedidos automáticos | Objetivo: 0. Métrica crítica |
| Casos que debían ir a revisión y salieron automáticos | Recuento sobre el conjunto de prueba | Objetivo: 0 |
| % automático y % de revisión por motivo | Sobre correos procesados | Medir en la demo; recalcular con la mezcla del escenario |
| Líneas correctas | Líneas con referencia, cantidad y precio correctos ÷ líneas | Medir en la demo |
| Revisiones innecesarias | Casos enviados a revisión que podrían haber sido automáticos | Medir en la demo |
| Tiempo por pedido | Cronómetro manual frente a demo (20 + 20 correos) | 6 min, supuesto; medición de una sola persona |
| Pedidos en el ERP antes del corte | Pedidos recibidos antes de las 13:00 que entran a tiempo ÷ pedidos recibidos antes de las 13:00 | Sin línea base; se mide en el piloto |
| Coste por correo | Coste de IA y orquestación por correo procesado | Medir en la demo |
| Errores de carga de datos maestros (A) | Filas rechazadas, avisos y conflictos por fuente | Informe por ejecución |

## Riesgos y dependencias

| Riesgo o dependencia | Consecuencia posible | Respuesta inicial |
|---|---|---|
| Datos maestros incompletos o contradictorios | Reglas que fallan o aprueban mal | Parte A con informe de errores; conflictos a revisión, nunca fusión automática |
| Errores de extracción de la IA | Pedido con referencia o cantidad equivocada | R12 con señales comprobables; el pedido con alguna línea dudosa se retiene entero |
| Confianza excesiva en la IA | Automatizar lo que no se debe | Las reglas deciden siempre; no se usa la confianza declarada por el modelo |
| Cambios de pedido ya en preparación | Errores caros en almacén | Modificaciones siempre a revisión |
| Bucles de correo con el cliente | Mala experiencia y ruido | Un único correo de petición; sin respuesta en 24 h, a revisión |
| Adopción del equipo | Se ignora la cola o se duplica el trabajo | Guía, formación de 30 min y puesta en marcha en paralelo y después gradual |
| Datos personales en correos | Exposición innecesaria | Mínimos de datos, permisos por rol, datos sintéticos en la demo |
| Integración con el ERP real | Retraso o coste mayor | ERP simulado en la demo; en un proyecto real, coste incluido en SN08 |
| Dependencia de un proveedor de IA | Coste, disponibilidad o cambios de modelo | Prompt y esquema versionados en un único sitio; evaluación repetible |
| Resultados inflados por datos sintéticos | Métricas poco creíbles | Desarrollo y prueba separados; correos generados con un modelo distinto del que extrae y ~15 escritos a mano |

## Restricciones

- Datos enteramente sintéticos. El repositorio es reproducible con tus propias claves: Supabase local, `.env.example` y las respuestas de la IA para el conjunto de prueba guardadas en el repositorio (D34).
- Revisión humana para excepciones y decisiones de negocio.
- En el portfolio se distinguen escenario, supuestos, medición y proyección.
- No se presenta el desarrollo asistido por IA como experiencia profesional de ingeniería en producción.

## Criterio para pasar al diseño

El caso está listo para el diseño cuando, tras el taller de discovery, estén contrastadas las cifras del escenario y los supuestos SN01–SN09, el AS-IS validado, las oportunidades priorizadas por impacto y viabilidad, y el comprar o construir argumentado. Este documento no declara que la solución funcione ni que genere ahorros.

## Preguntas para el taller de discovery simulado

**Proceso y volumen**
1. ¿Las cifras de D06 representan un mes típico? ¿Cómo son los picos de los lunes y después de festivos?
2. ¿Qué incluyen los 6 minutos por pedido y cuánto tiempo se va en cambios, consultas y reclamaciones?
3. ¿Cuántos pedidos recibidos antes de las 13:00 no entran a tiempo hoy?

**Datos maestros**

4. ¿Dónde vive cada tarifa pactada, quién la mantiene y cómo se sabe cuál está vigente?
5. ¿Cuántas equivalencias de referencias hay y quién las actualiza?
6. ¿Cómo se identifica hoy al cliente cuando escribe desde un buzón genérico o un email nuevo?

**Reglas y excepciones**

7. ¿El umbral de 3.000 € es razonable para dirección comercial?
8. ¿Qué hace hoy el equipo con un precio distinto al pactado, un descatalogado o una cantidad que no encaja con el embalaje?
9. ¿Cómo se gestionan hoy los duplicados entre pedidos@ y los reenvíos de los comerciales?

**Valor y alternativas**

10. ¿Qué haría la dirección con la capacidad liberada: evitar una contratación o dedicarla a seguimiento de clientes?
11. ¿Se ha valorado alguna solución comercial o un portal B2B? ¿Con qué resultado?
12. ¿Qué tendría que pasar en un piloto de 2–4 semanas para decidir seguir adelante?

## Siguiente documento

**02-discovery-workshop.md:** el taller de descubrimiento simulado. Cada pregunta anterior se responde como decisión del escenario, con su justificación y las alternativas descartadas, sin presentarlas como respuestas de personas reales. De ahí salen el AS-IS validado, el mapa del proceso, las oportunidades priorizadas y la versión revisada de este caso de negocio.
