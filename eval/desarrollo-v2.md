# Desarrollo v2: clasificación

**Los 20 correos de [desarrollo](../data/synthetic/evaluacion-v2/README.md), en el híbrido, con la clasificación integrada en el flujo. Pasada 1 el 25-11-2026; pasada 3, la limpia, el 26-11-2026. La prueba (60 casos, tag `prueba-v2.1`) no se ha ejecutado.**

## Resumen

**Pasada 3 (26-11-2026), limpia:** los 20 casos, sin ningún M03, con el mismo prompt, flujo y reglas que la pasada 1. Es la que se publica.

| Qué | Pasada 3 | Pasada 1 (25-11) |
|---|---|---|
| Tipo de correo | **20 de 20 bien** | 19 de 19 bien; 1 sin clasificar (503) |
| Salida y motivos, casos en alcance (14) | **14 OK, 0 FALLO, 0 M03** | 12 OK, 0 FALLO, 2 M03 |
| Salida y motivos, casos fuera de alcance (6) | 6 FALLO | 5 FALLO, 1 M03 |
| Pedidos automáticos en alcance | 4, con sus líneas bien. Con 4 casos no se puede decir nada de la tasa de error: la regla del 3 da 3/4 | Los mismos 4 |
| Automáticos indebidos fuera de alcance | 4: D03, D05, D09 y D10 | Los mismos 4 |

- **R11 ya está medido:** D04 y D11, los dos casos de precio, van a revisión con R11. En la pasada 1 acabaron en M03.
- **Los 6 FALLO son de reglas que no existen:** R03 (D12 y D13), R06 (D03), R09 (D09), M04 (D10) y varios pedidos en un correo (D05). Ninguno es de la clasificación. D12 es nuevo como FALLO porque en la pasada 1 fue M03: sin R03, va a revisión con R02, como D13.
- **Los 4 automáticos indebidos no son inocuos.** Es lo que haría el sistema hoy: crear un pedido con un producto descatalogado, con entrega en festivo, con dos pedidos juntos o con una orden escondida en una celda. Es la medida de lo que cuestan las reglas que faltan.
- **D20, la factura, se deriva** y ahora se ve en la lista "No son pedidos" de la app. Se usó para probar el botón "Es un pedido: pasar a revisión" ([capturas](#d20-en-la-app)).

## Qué se ajustó

**Nada.** El prompt de clasificación se escribió desde [04](../docs/04-solution-design.md), y en los 20 casos no hubo ningún error que motivara un cambio. La versión 2 es el mismo texto con otro modelo:

| Versión | Hash | Modelo | Por qué |
|---|---|---|---|
| 1 | `c761b231b9f4` | `gemini-3.1-flash-lite` | El del [ADR 0005](../docs/decisions/0005-modelo-de-ia.md) |
| 2, activa | `be628fae8dfd` | `gemini-3.5-flash-lite` | El 3.1 respondió 503 en 20 de 20 casos y en 12 sondas a lo largo de 35 min. Lo motivó la disponibilidad, no un resultado |

**Que los 20 salgan bien no demuestra que la clasificación sea buena.** Son correos cortos y claros; el prompt y los correos los escribió el mismo modelo, que ya conocía los 80; y solo hay una reclamación y un "otros". Los casos difíciles (la reclamación con pedido, la consulta que casi es un pedido, el phishing) están solo en la prueba.

## Llamadas y cuota

- Media por clasificación: 451 tokens de entrada y 22 de salida en la pasada 1; 453 y 22 en la 3.
- **Los dos prompts están ahora en el mismo modelo y comparten 500 peticiones al día.** El reparto del ADR 0005 ya no existe. La prueba completa (unas 120 clasificaciones y unas 90 extracciones, sin reintentos) cabe en un día si ese día no se hace mucho más.
- A las 19:58, Gemini respondió `429 · limit: 500 requests per day`, y se paró. Los reintentos del nodo (hasta 3 por fallo) también gastan.

| Ejecución | Qué pasó | Guardada en |
|---|---|---|
| 0, con el 3.1 | 20 de 20 en M03 (503). El evaluador no paraba solo; ahora para al tercer fallo seguido | [pasada0-503](ejecuciones/desarrollo-v2-pasada0-503.jsonl) |
| 1, con el 3.5 | Primera completa, con 3 M03 | [pasada1](ejecuciones/desarrollo-v2-pasada1.jsonl) |
| 2, con el 3.5 | Parada en el cuarto caso: cuota agotada | [pasada2-parada](ejecuciones/desarrollo-v2-pasada2-parada.jsonl) |
| 3, con el 3.5 | Entera, sin M03 ni 429, con 10 s de pausa. **La que se publica** | [pasada3](ejecuciones/desarrollo-v2-pasada3.jsonl) |

En la pasada 1, el evaluador ponía M03 también al tipo cuando fallaba solo la extracción. Se corrigió después, y las notas de D04 y D12 se recalcularon desde lo guardado, sin volver a llamar a Gemini.

## Repetición tras la cuota

Si una pasada tiene un M03 por 503 o 429, se repite **entera** más tarde, nunca solo los casos fallidos: así cada pasada publicada es una sola ejecución con el mismo estado del servicio. La pasada 3 no lo necesitó. La regresión de la v1.1 con la clasificación está en [regresion-v2.md](regresion-v2.md), sección 2.

## Caso a caso

Pasada 3.

| Caso | Tipo etiquetado | Tipo leído | Salida etiquetada | Salida | Nota | Depende de |
|---|---|---|---|---|---|---|
| D01 | pedido_nuevo | pedido_nuevo | automatico | automatico | OK | — |
| D02 | pedido_nuevo | pedido_nuevo | automatico | automatico | OK | — |
| D03 | pedido_nuevo | pedido_nuevo | pedir datos R06 | automatico | FALLO | R06 |
| D04 | pedido_nuevo | pedido_nuevo | revision R11 | revision R11 | OK | — |
| D05 | pedido_nuevo | pedido_nuevo | revision | automatico | FALLO | D16 |
| D06 | pedido_nuevo | pedido_nuevo | revision R02 | revision R02 | OK | — |
| D07 | pedido_nuevo | pedido_nuevo | automatico | automatico | OK | — |
| D08 | pedido_nuevo | pedido_nuevo | automatico | automatico | OK | — |
| D09 | pedido_nuevo | pedido_nuevo | revision R09 | automatico | FALLO | R09 |
| D10 | pedido_nuevo | pedido_nuevo | revision M04 | automatico | FALLO | M04 |
| D11 | pedido_nuevo | pedido_nuevo | revision R11 | revision R11 | OK | — |
| D12 | pedido_nuevo | pedido_nuevo | automatico | revision R02 | FALLO | R03 |
| D13 | pedido_nuevo | pedido_nuevo | automatico | revision R02 | FALLO | R03 |
| D14 | pedido_nuevo | pedido_nuevo | revision M02 | revision M02 | OK | — |
| D15 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision R01 | OK | — |
| D16 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision R01 | OK | — |
| D17 | consulta | consulta | revision R01 | revision R01 | OK | — |
| D18 | consulta | consulta | revision R01 | revision R01 | OK | — |
| D19 | reclamacion | reclamacion | revision R01 | revision R01 | OK | — |
| D20 | otros | otros | derivado | derivado | OK | — |

## Limitaciones

- Una pasada limpia, una configuración y 20 casos que conocía quien escribió el prompt.
- Las etiquetas no tienen revisión humana.
- Un pedido clasificado como `otros` no llega a la cola: es el error caro de esta pieza, y con un solo "otros" no se ha medido. Desde el 26-11 no desaparece: se ve en "No son pedidos", pero solo si alguien mira esa lista.
- Solo reglas no clasifica, y solo IA no se ha pasado: usa la misma clasificación que el híbrido.

## D20 en la app

El caso de D20 de la pasada 3 (nº 173 en la base local), derivado a contabilidad, en la lista "No son pedidos" y después de pulsar "Es un pedido: pasar a revisión". Sesión de la gestora de ADV, 26-11-2026.

| | |
|---|---|
| ![Lista "No son pedidos" con la factura de D20 y el motivo de la clasificación](../docs/img/app-no-son-pedidos.png) | ![El correo original abierto desde la lista](../docs/img/app-no-son-pedidos-correo.png) |
| ![Confirmación tras pasarlo a revisión; la lista queda vacía](../docs/img/app-no-son-pedidos-pasado.png) | ![El caso en revisión con M01: se teclea a mano o se descarta](../docs/img/app-no-son-pedidos-revision.png) |

![La cola de revisión con el caso 173, "Marcado como pedido desde «No son pedidos»"](../docs/img/app-no-son-pedidos-cola.png)
