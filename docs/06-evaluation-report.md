# 06 · Informe de evaluación (v2)

**La prueba congelada (tag `prueba-v2.1`, 60 casos, 66 `.eml`), ejecutada una sola vez por configuración, con la base recién cargada y los correos por orden de su cabecera `Date`.** Solo reglas e híbrido, el 26-11-2026. **Solo IA, pendiente:** la cuota diaria de Gemini no daba para las dos pasadas con IA el mismo día, y una pasada cortada por cuota no vale ([ejecuciones](#ejecuciones)).

Alcance, métrica y reglas de lectura, fijados antes de congelar: [alcance-prueba-v2.md](../eval/alcance-prueba-v2.md). Todos los datos son sintéticos.

## Resultado principal

**Híbrido, 38 casos en alcance: 1 de 10 pedidos automáticos fue erróneo o indebido (P52).**

- **P52 es una consulta que el sistema convirtió en pedido.** "¿Tenéis en stock LIJ-HOJ-80 (necesito 100) y ADH-EPO-25 (3)? Si es que sí, mandadlos. Si no, no hagáis nada". La clasificación lo leyó como `pedido_nuevo`, la extracción leyó bien las dos líneas, las reglas no encontraron nada raro y se creó el pedido sin que nadie mirara las existencias. Es el error de la frontera entre consulta y pedido, el que la etiqueta marcaba como trampa.
- **Con 1 error en 10, el error real puede ser mucho mayor:** el límite superior al 95 % (Clopper-Pearson, unilateral) es del 39 %. La regla del 3 solo se aplica con 0 errores.
- **Los otros 9 automáticos, bien:** producto y cantidad en unidad de venta iguales a la etiqueta.
- **El otro fallo en alcance es seguro:** P02 pidió datos al cliente en lugar de crear el pedido (abajo).

| Configuración | Automáticos erróneos o indebidos, en alcance | OK | ACEPTABLE | FALLO | M03 |
|---|---|---|---|---|---|
| **Híbrido** | **1 de 10** | 36 | 0 | 2 | 0 |
| Solo reglas | 1 de 6 | 13 | 14 | 11 | 0 |
| Solo IA | Pendiente (27-11) | | | | |

ACEPTABLE es una salida segura que no era la esperada: el caso llega a una persona. M03 es el servicio de IA caído; va en su columna y no cuenta como acierto ni como fallo.

- **Solo reglas no clasifica:** las 18 modificaciones, consultas, reclamaciones y "otros" van a revisión con M01 o M02 en lugar de R01 o derivarse. Es seguro, pero no dice por qué. Y no puede leer lo que no es un código exacto: 5 pedidos claros van a revisión.
- **El indebido de solo reglas es P38:** sin segundo lector no hay R12, y una discrepancia entre el Excel y el cuerpo se crea con lo que dice el Excel.

## Tipo de correo, en los 60 casos

Híbrido. Cada caso se mide por su primer `.eml`.

| Etiqueta \ leído | pedido_nuevo | modificacion_anulacion | consulta | reclamacion | otros | dudoso | sin clasificar | Total |
|---|---|---|---|---|---|---|---|---|
| pedido_nuevo | **42** | 0 | 0 | 0 | 0 | 0 | 0 | 42 |
| modificacion_anulacion | 0 | **6** | 0 | 0 | 0 | 0 | 0 | 6 |
| consulta | 1 | 0 | **3** | 0 | 0 | 0 | 0 | 4 |
| reclamacion | 0 | 0 | 0 | **3** | 0 | 0 | 0 | 3 |
| otros | 0 | 0 | 0 | 0 | **5** | 0 | 0 | 5 |

**59 de 60 bien.** El único error es P52. Ningún pedido se clasificó como `otros` (el error que lo sacaría de la cola) y ninguna modificación como pedido. El modelo no usó `dudoso` ni una vez, tampoco en P52, donde la etiqueta lo admitía.

Solo IA clasifica con el mismo prompt; su tabla irá aquí cuando se ejecute. Solo reglas no clasifica.

## Fallos en alcance, uno a uno

| Caso | Configuración | Qué pasó | Por qué | Coste |
|---|---|---|---|---|
| P52 | Híbrido | Pedido automático de una consulta condicional | La clasificación leyó "si es que sí, mandadlos" como un pedido. El prompt dice que "si el pedido depende de la respuesta, es una consulta", y aun así | **Pedido indebido:** sale material que el cliente no ha confirmado |
| P02 | Híbrido | Pedir datos (R08) en lugar de automático | La IA copió el rótulo dentro de la referencia ("Ref. T-0830 INOX" en lugar de "T-0830 INOX"), y la equivalencia del cliente no se encontró. El lector de reglas no lee esa línea | Seguro: no se crea nada, pero se pregunta al cliente algo que ya había dicho |
| P38 | Solo reglas | Automático con la cantidad del Excel | Sin IA no hay segunda lectura ni R12. Es lo que se pierde sin IA, no un fallo a corregir ([05](05-synthetic-data-and-evaluation-set.md#5-conjunto-de-evaluación-d23)) | **Pedido indebido** |
| P02, P04, P09, P12, P13 | Solo reglas | Revisión con M01 en lugar de automático | El lector de reglas no lee equivalencias, ni texto libre, ni algunos Excel | Revisiones innecesarias |
| P32 | Solo reglas | Revisión con M01 en lugar de R11 | Sin líneas leídas no se puede comprobar el precio | Seguro, peor explicado |
| P53, P54, P55, P56 | Solo reglas | M01 o M02 en lugar de R01 o derivado | No clasifica | Seguro; P56, una factura, ocupa la cola |

## Fuera de alcance: 22 casos

Dependen de reglas que no existen. No entran en la métrica principal ni en ningún porcentaje. **Su propio recuento de automáticos erróneos o indebidos:**

- **Híbrido: 12 de 12 automáticos.** P06, P14, P16, P17, P18, P25, P26, P29, P31, P35, P36 y P37.
- **Solo reglas: 9 de 9.**

Es lo que pasaría hoy con esos correos: un cliente bloqueado (P25), una cantidad anómala (P35), cajas tomadas como unidades (P06), kilos sin conversión (P31), una instrucción en el cuerpo (P37) o una dirección que no se sabe cuál es (P14, P17, P18), todos creados sin que nadie los mire. **Es la medida de lo que cuestan las reglas que faltan, y es alta:** de los 22 correos que necesitan una regla no construida, más de la mitad acaban hoy en un pedido automático que no debería existir.

| Caso | Regla que falta | Salida etiquetada | Híbrido | Solo reglas |
|---|---|---|---|---|
| P05 | R03 | automático | revisión R02 | revisión R02 |
| P06 | R10 | automático | automático, **erróneo**: 3 y 2 en vez de 300 y 200 (cajas de 100) | revisión M01 |
| P11 | D16 | automático | revisión M01 | revisión M01 |
| P14 | R05, RESPUESTA | pedir datos R05 | automático, **indebido** | automático, **indebido** |
| P15 | RESPUESTA | pedir datos R08 | pedir datos R08: lo esperado | pedir datos R08 |
| P16 | R10, RESPUESTA | pedir datos R10 | automático, **indebido** | automático, **indebido** |
| P17 | R05, RESPUESTA | pedir datos R05 | automático, **indebido** | revisión M01 |
| P18 | R05, R10, RESPUESTA | pedir datos R05, R10 | automático, **indebido** | automático, **indebido** |
| P19 | R03, R06 | pedir datos R06 | revisión R02 | revisión M01 |
| P20 | D22 | pedir datos | revisión M01, aceptable según el alcance | revisión M01 |
| P25 | R04 | revisión R04 | automático, **indebido** | automático, **indebido** |
| P26 | R05, M04 | revisión M04, R05 | automático, **indebido** | automático, **erróneo e indebido**: le falta una línea |
| P27 | R03, R07 | revisión R07, R10 | revisión R02 | revisión R02 |
| P28 | R03, R07 | revisión R07 | revisión M02 | revisión M02 |
| P29 | R07 | revisión R07 | automático, **indebido** | revisión M01 |
| P30 | R09 | revisión R08, R09 | revisión R08 | automático, **erróneo e indebido**: le falta la línea por descripción |
| P31 | R10 | revisión R10 | automático, **erróneo e indebido**: 5 "unidades" de algo pedido en kilos | revisión M01 |
| P33 | R03 | revisión R11 | revisión R02 | revisión R02 |
| P34 | R13 | revisión R11, R13 | revisión R11 | revisión R11 |
| P35 | R14 | revisión R14 | automático, **indebido** | automático, **indebido** |
| P36 | R14 | revisión R14 | automático, **indebido** | automático, **indebido** |
| P37 | M04 | revisión M04 | automático, **indebido** | automático, **indebido** |

**¿Alguno falla por otra causa?** En el híbrido, **ninguno**: los 22 se clasificaron como `pedido_nuevo`, que es su tipo, y en los 12 automáticos la IA leyó lo que decía el correo (en P06 y P31, la cantidad y la unidad tal cual: falta la conversión, R10). En solo reglas, **2** (P26 y P30): el lector de reglas deja fuera una línea, que es lo que se pierde sin IA.

## Respuestas del cliente: 6 `.eml`

Entran como correos nuevos, porque la respuesta no se enlaza con su caso (RESPUESTA). Van con los fuera de alcance.

| `.eml` | Qué es | Híbrido | Solo reglas |
|---|---|---|---|
| P14b | Elige la dirección | `pedido_nuevo`, revisión M01 | revisión M01 |
| P15b | Da el código que faltaba | `pedido_nuevo`, revisión M01 | revisión M01 |
| P16b | "Pues 50, y de paso añade 2 cajas de GUA-NIT-M" | `pedido_nuevo`, **automático**: un segundo pedido (DIS-COR-125 ×50 y GUA-NIT-M ×2, cajas sin convertir) | revisión M01 |
| P17b | "la de siempre": no da la dirección | `pedido_nuevo`, revisión M01 | revisión M01 |
| P18b | Respuesta automática de "fuera de la oficina" | `otros`, derivado: sale de la cola y se ve en "No son pedidos" | revisión M01 |
| P18c | "Que sean 100": responde a una de las dos preguntas | `pedido_nuevo`, revisión M01 | revisión M01 |

**P16b es el caso más caro de los fuera de alcance:** P16 ya había creado un pedido automático (indebido), y la respuesta crea otro, con una línea nueva en cajas sin convertir. Sin enlazar respuestas, un cliente que contesta a una petición de datos puede acabar con dos pedidos.

## M03 y servicio

**Ningún M03 en ninguna pasada**, y ningún 429 ni 503. Las dos pasadas son la primera de su configuración.

## Ejecuciones

| Configuración | Fecha | Commit | Prompts | Llamadas a Gemini | Fichero |
|---|---|---|---|---|---|
| Solo reglas | 26-11-2026, 14:15 | `669edad` | — (no llama a la IA) | 0 | [intento 1](../eval/ejecuciones/prueba-v2.1-solo_reglas-intento1.jsonl) |
| Híbrido | 26-11-2026, 14:16–14:37 | `669edad` | clasificación `3fb185e49636` (texto v2), extracción `ea73c9fd7c06` | 110 (66 clasificaciones y 44 extracciones; 49.771 tokens de entrada y 6.895 de salida) | [intento 1](../eval/ejecuciones/prueba-v2.1-hibrido-intento1.jsonl) |
| Solo IA | Pendiente | | | | |

- **Cómo:** `scripts/ejecutar_prueba.py`, que antes de enviar nada comprueba el manifiesto, el tag, que el código está commiteado, que los prompts activos son los de `extraction/` y que la base no tiene casos. Guarda cada `.eml` con la clasificación y la extracción en bruto. Las tablas salen de `scripts/informe_prueba.py`, escrito y probado antes de ejecutar.
- **Por qué solo IA va otro día:** los dos prompts usan `gemini-3.5-flash-lite` y comparten 500 peticiones al día. Ese día ya se habían gastado más de 220 (contadas en la base) en las pasadas de desarrollo y en las regresiones del texto v2, más las de la mañana, antes de recargar la base; el híbrido gastó 110. Solo IA necesita otras ~110: no cabían con margen, y una pasada cortada por 429 se repite entera.
- El texto v2 del prompt de clasificación se ajustó antes de ejecutar, solo con desarrollo ([registro de cambios](../eval/registro-de-cambios.md)). **Después de ver resultados no se ha cambiado nada:** ni el sistema ni las etiquetas.

## Límites

- **Las etiquetas son de una IA, con segunda lectura de otra IA y sin revisión humana.** Claude Code escribió los 80 correos y sus etiquetas, conociendo el sistema; otra instancia de Claude [revisó](../eval/revision-etiquetas-v2.md) las de los 38 casos en alcance antes de ejecutar. Los 22 fuera de alcance no se revisaron con el mismo detalle.
- **El catálogo es generado, y nadie ha comprobado a mano sus equivalencias.** Productos, equivalencias y tarifas salen de [un generador](../scripts/generar_maestros.py) con semilla fija; las etiquetas se contrastaron con él en Python, no a mano. Si el generador tuviera un error, etiqueta y sistema lo compartirían.
- **38 casos en alcance y 10 pedidos automáticos.** Un error en 10 deja un intervalo muy ancho. Para confiar harían falta cientos, en un piloto con correos reales.
- **Los correos los escribió un modelo** que había leído el código, y el mismo modelo escribió después el prompt de clasificación. El catalán es más correcto que el de un cliente real.
- **Una pasada por configuración:** no mide cuánto varía la IA entre ejecuciones.
- **Lo que no está construido no se mide aquí:** los 22 fuera de alcance dicen cuánto cuesta, no si las reglas que faltan funcionarían.

## Fe de erratas

Ninguna errata tras ejecutar. La corrección de P23 se hizo antes de ejecutar (tag `prueba-v2.1`, [revisión de etiquetas](../eval/revision-etiquetas-v2.md)) y no toca la métrica principal. Si apareciera una errata, irá aquí con las métricas en las dos versiones de la etiqueta.

## Anexo: tablas completas

Salida de `uv run scripts/informe_prueba.py`, sin editar.

<details>
<summary>Tablas generadas</summary>

#### Ejecuciones

| Configuración | Intento | Commit | Inicio | Prompts |
|---|---|---|---|---|
| solo_reglas | 1 | `669edad` | 2026-11-26T14:15:52+01:00 | clasificacion `3fb185e49636`, extraccion `ea73c9fd7c06` |
| hibrido | 1 | `669edad` | 2026-11-26T14:16:36+01:00 | clasificacion `3fb185e49636`, extraccion `ea73c9fd7c06` |

#### Métrica principal: automáticos erróneos o indebidos, 38 casos en alcance

| Configuración | Automáticos erróneos o indebidos | Erróneos | Indebidos | OK | ACEPTABLE | FALLO | M03 |
|---|---|---|---|---|---|---|---|
| solo_reglas | 1 de 6 automáticos | 0 | 1 | 13 | 14 | 11 | 0 |
| hibrido | 1 de 10 automáticos | 1 | 1 | 36 | 0 | 2 | 0 |

#### Tipo de correo, 60 casos, hibrido

| Etiqueta \ leído | pedido_nuevo | modificacion_anulacion | consulta | reclamacion | otros | dudoso | sin clasificar | Total |
|---|---|---|---|---|---|---|---|---|
| pedido_nuevo | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 42 |
| modificacion_anulacion | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 6 |
| consulta | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 4 |
| reclamacion | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 3 |
| otros | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 5 |

OK 59, ACEPTABLE 0, FALLO 1, sin clasificar 0.

#### Casos en alcance, uno a uno

| Caso | Tipo etiquetado | Tipo leído (híbrido) | Salida etiquetada | solo_reglas | hibrido |
|---|---|---|---|---|---|
| P01 | pedido_nuevo | pedido_nuevo | automatico | automatico · OK | automatico · OK |
| P02 | pedido_nuevo | pedido_nuevo | automatico | revision M01 · FALLO (salida revision, esperada automatico; motivos M01, esperados -) | pedir_datos R08 · FALLO (salida pedir_datos, esperada automatico; motivos R08, esperados -) |
| P03 | pedido_nuevo | pedido_nuevo | automatico | automatico · OK | automatico · OK |
| P04 | pedido_nuevo | pedido_nuevo | automatico | revision M01 · FALLO (salida revision, esperada automatico; motivos M01, esperados -) | automatico · OK |
| P07 | pedido_nuevo | pedido_nuevo | automatico | automatico · OK | automatico · OK |
| P08 | pedido_nuevo | pedido_nuevo | automatico | automatico · OK | automatico · OK |
| P09 | pedido_nuevo | pedido_nuevo | automatico | revision M01 · FALLO (salida revision, esperada automatico; motivos M01, esperados -) | automatico · OK |
| P10 | pedido_nuevo | pedido_nuevo | automatico | automatico · OK | automatico · OK |
| P12 | pedido_nuevo | pedido_nuevo | automatico | revision M01 · FALLO (salida revision, esperada automatico; motivos M01, esperados -) | automatico · OK |
| P13 | pedido_nuevo | pedido_nuevo | automatico | revision M01 · FALLO (salida revision, esperada automatico; motivos M01, esperados -) | automatico · OK |
| P21 | pedido_nuevo | pedido_nuevo | revision R02 | revision R02 · OK | revision R02 · OK |
| P22 | pedido_nuevo | pedido_nuevo | revision R02 | revision R02 · OK | revision R02 · OK |
| P23 | pedido_nuevo | pedido_nuevo | revision R02 | revision R02 · OK | revision R02 · OK |
| P24 | pedido_nuevo | pedido_nuevo | revision R02 | revision R02 · OK | revision R02 · OK |
| P32 | pedido_nuevo | pedido_nuevo | revision R11 | revision M01 · FALLO (motivos M01, esperados R11) | revision R11 · OK |
| P38 | pedido_nuevo | pedido_nuevo | revision R12 | automatico · FALLO (salida automatico, esperada revision; motivos -, esperados R12) | revision R12 · OK |
| P39 | pedido_nuevo | pedido_nuevo | revision M01 | revision M01 · OK | revision M01 · OK |
| P40 | pedido_nuevo | pedido_nuevo | revision M02 | revision M02 · OK | revision M02 · OK |
| P41 | pedido_nuevo | pedido_nuevo | revision M02 | revision M02 · OK | revision M02 · OK |
| P42 | pedido_nuevo | pedido_nuevo | revision M02 | revision M02 · OK | revision M02 · OK |
| P43 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P44 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P45 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P46 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P47 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P48 | modificacion_anulacion | modificacion_anulacion | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P49 | consulta | consulta | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P50 | consulta | consulta | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P51 | consulta | consulta | revision R01 | revision M01 · ACEPTABLE | revision R01 · OK |
| P52 | consulta | pedido_nuevo | revision R01 | revision M01 · ACEPTABLE | automatico · FALLO (salida automatico, esperada revision; motivos -, esperados R01; líneas ADH-EPO-25 x3, LIJ-HOJ-80 x100 en lugar de ) |
| P53 | reclamacion | reclamacion | revision R01 | revision M01 · FALLO (motivos M01, esperados R01) | revision R01 · OK |
| P54 | reclamacion | reclamacion | revision R01 | revision M01 · FALLO (motivos M01, esperados R01) | revision R01 · OK |
| P55 | reclamacion | reclamacion | revision R01 | revision M01 · FALLO (motivos M01, esperados R01) | revision R01 · OK |
| P56 | otros | otros | derivado | revision M02 · FALLO (salida revision, esperada derivado; motivos M02, esperados -) | derivado · OK |
| P57 | otros | otros | derivado | revision M01 · ACEPTABLE | derivado · OK |
| P58 | otros | otros | derivado | revision M01 · ACEPTABLE | derivado · OK |
| P59 | otros | otros | derivado | revision M01 · ACEPTABLE | derivado · OK |
| P60 | otros | otros | derivado | revision M01 · ACEPTABLE | derivado · OK |

#### Fuera de alcance: 22 casos

- solo_reglas: 9 de 9 automáticos.
- hibrido: 12 de 12 automáticos.

| Caso | Depende de | Salida etiquetada | Tipo leído (híbrido) | solo_reglas | hibrido |
|---|---|---|---|---|---|
| P05 | R03 | automatico | pedido_nuevo | revision R02 (salida revision, esperada automatico; motivos R02, esperados -) | revision R02 (salida revision, esperada automatico; motivos R02, esperados -) |
| P06 | R10 | automatico | pedido_nuevo | revision M01 (salida revision, esperada automatico; motivos M01, esperados -) | automatico · **erróneo** (líneas ARA-M10-A2 x2, TUE-M10-A2 x3 en lugar de ARA-M10-A2 x200, TUE-M10-A2 x300) |
| P11 | D16 | automatico | pedido_nuevo | revision M01 (salida revision, esperada automatico; motivos M01, esperados -) | revision M01 (salida revision, esperada automatico; motivos M01, esperados -) |
| P14 | R05, RESPUESTA | pedir_datos R05 | pedido_nuevo | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R05) | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R05) |
| P15 | RESPUESTA | pedir_datos R08 | pedido_nuevo | pedir_datos R08 | pedir_datos R08 |
| P16 | R10, RESPUESTA | pedir_datos R10-EMBALAJE | pedido_nuevo | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R10-EMBALAJE) | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R10-EMBALAJE) |
| P17 | R05, RESPUESTA | pedir_datos R05 | pedido_nuevo | revision M01 (salida revision, esperada pedir_datos; motivos M01, esperados R05) | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R05) |
| P18 | R05, R10, RESPUESTA | pedir_datos R05, R10-EMBALAJE | pedido_nuevo | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R05, R10-EMBALAJE) | automatico · **indebido** (salida automatico, esperada pedir_datos; motivos -, esperados R05, R10-EMBALAJE) |
| P19 | R03, R06 | pedir_datos R06 | pedido_nuevo | revision M01 (salida revision, esperada pedir_datos; motivos M01, esperados R06) | revision R02 (salida revision, esperada pedir_datos; motivos R02, esperados R06) |
| P20 | D22 | pedir_datos | pedido_nuevo | revision M01 (salida revision, esperada pedir_datos; motivos M01, esperados -) | revision M01 (salida revision, esperada pedir_datos; motivos M01, esperados -) |
| P25 | R04 | revision R04 | pedido_nuevo | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R04) | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R04) |
| P26 | R05, M04 | revision M04, R05 | pedido_nuevo | automatico · **erróneo** · **indebido** (salida automatico, esperada revision; motivos -, esperados M04, R05; líneas  en lugar de LLC-22 x4) | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados M04, R05) |
| P27 | R03, R07 | revision R07, R10-EMBALAJE | pedido_nuevo | revision R02 (motivos R02, esperados R07, R10-EMBALAJE) | revision R02 (motivos R02, esperados R07, R10-EMBALAJE) |
| P28 | R03, R07 | revision R07 | pedido_nuevo | revision M02 (motivos M02, esperados R07) | revision M02 (motivos M02, esperados R07) |
| P29 | R07 | revision R07 | pedido_nuevo | revision M01 (motivos M01, esperados R07) | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R07) |
| P30 | R09 | revision R08, R09 | pedido_nuevo | automatico · **erróneo** · **indebido** (salida automatico, esperada revision; motivos -, esperados R08, R09; líneas  en lugar de DIS-COR-230 x50) | revision R08 (motivos R08, esperados R08, R09) |
| P31 | R10 | revision R10-UNIDAD | pedido_nuevo | revision M01 (motivos M01, esperados R10-UNIDAD) | automatico · **erróneo** · **indebido** (salida automatico, esperada revision; motivos -, esperados R10-UNIDAD; líneas ARA-M10-ZN x5 en lugar de ARA-M10-ZN xNone) |
| P33 | R03 | revision R11 | pedido_nuevo | revision R02 (motivos R02, esperados R11) | revision R02 (motivos R02, esperados R11) |
| P34 | R13 | revision R11, R13 | pedido_nuevo | revision R11 (motivos R11, esperados R11, R13) | revision R11 (motivos R11, esperados R11, R13) |
| P35 | R14 | revision R14 | pedido_nuevo | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R14) | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R14) |
| P36 | R14 | revision R14 | pedido_nuevo | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R14) | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados R14) |
| P37 | M04 | revision M04 | pedido_nuevo | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados M04) | automatico · **indebido** (salida automatico, esperada revision; motivos -, esperados M04) |

#### Respuestas del cliente: 6 .eml, entran como correos nuevos

| .eml | Salida final etiquetada del caso | solo_reglas | hibrido |
|---|---|---|---|
| P14b | automatico | - → revision M01 | pedido_nuevo → revision M01 |
| P15b | automatico | - → revision M01 | pedido_nuevo → revision M01 |
| P16b | revision | - → revision M01 | pedido_nuevo → automatico |
| P17b | revision | - → revision M01 | pedido_nuevo → revision M01 |
| P18b | revision | - → revision M01 | otros → derivado |
| P18c | revision | - → revision M01 | pedido_nuevo → revision M01 |

#### M03

- solo_reglas: 0.
- hibrido: 0.

</details>
