# Alcance de la prueba v2

**Fijado el 25-11-2026, antes de congelar la prueba y antes de ver ningún resultado suyo.** Forma parte de lo congelado: está en el [manifiesto](../data/synthetic/evaluacion-v2/manifiesto-prueba.json).

Las etiquetas describen lo correcto según [04](../docs/04-solution-design.md), exista o no la regla. Los 60 casos se diseñaron para el sistema completo, y hoy faltan reglas. Si la prueba se ejecuta así, un caso de una regla que no existe mide lo que falta por construir, no lo que hay. Por eso se separan.

## Qué está construido

R01 (por la clasificación), R02, R08, R11, R12 (coincidencia de los dos lectores), M01, M02 y M03.

## Métrica principal

**Pedidos automáticos erróneos o indebidos, en el híbrido, sobre los 38 casos en alcance.** El objetivo es 0 ([04, sección 9.2](../docs/04-solution-design.md#92-calidad-de-la-demo)).

- **Erróneo:** pedido creado sin intervención con alguna línea distinta de la etiqueta (producto o cantidad en unidad de venta).
- **Indebido:** pedido creado sin intervención en un caso cuya salida etiquetada no es `automatico`.
- Se publica como "x de n automáticos en alcance", con el límite superior 3/n si x es 0. Solo reglas y solo IA se publican al lado.

## Casos en alcance: 38

<!-- en alcance -->
- **Pedidos (20):** P01, P02, P03, P04, P07, P08, P09, P10, P12, P13, P21, P22, P23, P24, P32, P38, P39, P40, P41, P42.
- **Modificaciones y anulaciones (6):** P43, P44, P45, P46, P47, P48.
- **Consultas (4):** P49, P50, P51, P52.
- **Reclamaciones (3):** P53, P54, P55.
- **Otros (5):** P56, P57, P58, P59, P60.
<!-- fin -->

Criterio: la salida y los motivos etiquetados se obtienen solo con lo construido. Un caso automático está en alcance aunque falte una regla que habría pasado (P08, el importe exacto de R13). En las modificaciones se miden el tipo, la salida y el motivo; el "cambio propuesto" de 04 no existe y no se mide.

## Casos fuera de alcance: 22

| Caso | Depende de | Por qué |
|---|---|---|
| P05 | R03 | Reenvío de un comercial: hoy el remitente es el comercial, que no es contacto de ningún cliente |
| P06 | R10 | Conversión de unidades (3 cajas de 100) |
| P11 | D16 | "Repite el pedido X": no se busca en el histórico |
| P14 | R05, RESPUESTA | Dirección que falta, y respuesta del cliente |
| P15 | RESPUESTA | La petición (R08) sale; la respuesta no se enlaza con el caso |
| P16 | R10, RESPUESTA | Embalaje, y respuesta con algo más (M07) |
| P17 | R05, RESPUESTA | "La de siempre" |
| P18 | R05, R10, RESPUESTA | Dos datos, respuesta automática y respuesta incompleta (M06) |
| P19 | R03, R06 | Reenvío, y entrega hoy después del corte |
| P20 | D22 | Pedido sin líneas: pedir datos. Hoy va a revisión con M01, que es aceptable |
| P25 | R04 | Cliente bloqueado |
| P26 | R05, M04 | Otra nave, e instrucción condicional |
| P27 | R03, R07 | Duplicado de un caso abierto, reenviado |
| P28 | R03, R07 | Número de pedido ya usado, reenviado |
| P29 | R07 | Numeración cíclica |
| P30 | R09 | Descatalogado (la línea por descripción, R08, sí está construida) |
| P31 | R10 | Unidad sin conversión |
| P33 | R03 | Precio pactado por teléfono, reenviado |
| P34 | R13 | Importe (R11 sí está construida) |
| P35 | R14 | Cantidad anómala |
| P36 | R14 | Cantidad grande legítima |
| P37 | M04 | Instrucciones en el cuerpo |

`RESPUESTA`: enlazar la respuesta del cliente con su caso ([04, sección 2.3](../docs/04-solution-design.md#23-respuesta-del-cliente-a-una-petición-de-datos)). `D16` y `D22` son decisiones de [01](../docs/01-reframe-decisions.md) sin regla construida.

## Cómo se informará de los 22

- **En su propia tabla, uno a uno:** qué regla falta, qué salida dio y qué salida tocaba. No entran en la métrica principal ni en ningún porcentaje de acierto.
- **Con su propio recuento de automáticos erróneos o indebidos.** Es lo que pasaría hoy con esos correos, y no se esconde: es la medida de lo que cuestan las reglas que faltan.
- **No se llaman fallos** si la única causa es la regla que falta. Si fallan por otra cosa (una cantidad mal leída, un tipo mal clasificado), se dice, y también se dice cuántos son.
- **El tipo de correo se mide en los 60,** con su tabla de confusión, porque la clasificación está construida. `dudoso` va en su propia columna.

## Reglas de lectura

1. **El alcance no se mueve.** Si antes de ejecutar la prueba se construye alguna regla, la métrica principal sigue siendo la de estos 38 casos. Los que pasen a estar cubiertos se informan en una segunda tabla, declarada como tal.
2. **Los 66 `.eml` se envían por orden de su cabecera `Date`.** Los 6 de respuesta (P14b, P15b, P16b, P17b, P18b y P18c) entran hoy como correos nuevos; se informan con los fuera de alcance.
3. **Una pasada por configuración,** con la base recién cargada. Solo se repite por un fallo de infraestructura, entera y declarada. Un M03 cuenta como servicio caído y va en su columna.
4. Una etiqueta equivocada va a la fe de erratas, con las métricas en las dos versiones ([05, sección 8](../docs/05-synthetic-data-and-evaluation-set.md#8-separación-y-congelación)).
