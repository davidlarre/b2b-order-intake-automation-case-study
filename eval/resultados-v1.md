# Resultados de la evaluación v1

**Evaluación pequeña, sobre casos de desarrollo.** Sirve para ver qué hace el sistema y dónde falla, no para estimar su tasa de error. La evaluación completa, con prueba congelada, está diseñada en [05](../docs/05-synthetic-data-and-evaluation-set.md) y pasa a la [siguiente fase](../docs/00-project-plan.md#siguiente-fase).

## Resumen

20 correos sintéticos, una pasada por configuración. 25-11-2026.

| Configuración | OK | ACEPTABLE | FALLO | Pedidos automáticos | Automáticos erróneos o indebidos |
|---|---|---|---|---|---|
| Solo reglas | 7 | 5 | 8 | 11 | **8** |
| Solo IA | 18 | 1 | 1 | 11 | **0** |
| Híbrido | 16 | 3 | 1 | 9 | **0** |

- **OK:** la salida, los motivos y, si se creó un pedido, sus líneas son los esperados.
- **ACEPTABLE:** no es lo esperado, pero es una salida segura prevista en la etiqueta: el caso llega a una persona.
- **FALLO:** cualquier otra diferencia. Incluye tanto un pedido equivocado como una salida segura que la etiqueta no preveía.
- **Automáticos erróneos o indebidos:** pedidos creados sin intervención con alguna línea mal, o que tenían que ir a revisión. Es la métrica crítica.

## Qué se puede concluir

1. **Sin IA, el sistema se equivoca sin avisar.** El lector determinista solo entiende códigos exactos y cantidades limpias. 8 de sus 11 pedidos automáticos están mal. Es la línea base, no una candidata a producción ([04, sección 7](../docs/04-solution-design.md#7-cómo-se-evalúa-este-diseño)).
2. **La IA lee bien lo que las reglas no leen:** equivalencias, puntos de miles, multiplicaciones, unidades dentro de una celda y cabeceras desconocidas.
3. **En estos 20 casos, "solo IA" sale mejor que el híbrido.** La comparación de lecturas (R12) costó dos revisiones innecesarias (06 y 15), en las que la IA había leído bien, y no evitó ningún pedido equivocado. Lo que compra R12 es una red para el día en que la IA lea mal con aspecto de haber leído bien. **Este conjunto no lo demuestra ni lo desmiente:** haría falta un caso así, y no apareció.
4. **La IA no lee siempre igual.** En el caso 16, el mismo correo dio dos lecturas distintas en dos configuraciones. Con una sola pasada, esa variación no se mide.

## Los fallos, uno a uno

### Solo IA e híbrido

**16 · El cliente corrige el código en la misma línea.** `TUE-M8-ZN 400 uds (perdón, es TUE-M10-ZN)`. Lo correcto es TUE-M10-ZN × 400.

- **Qué leyó la IA:** metió los dos códigos en la referencia: `TUE-M8-ZN / TUE-M10-ZN` en solo IA y `TUE-M8-ZN (perdón, es TUE-M10-ZN)` en el híbrido. El prompt le pide copiar la referencia tal como la escribe el cliente, y no dice qué hacer con una corrección. Con una cantidad (caso 06) sí resuelve la corrección; con un código, no.
- **Solo IA → pedir datos (R08):** la referencia no existe en el catálogo. No crea un pedido equivocado, pero le pediría al cliente un dato que ya había dado.
- **Híbrido → revisión (R08 y R12):** llega a una persona con las dos lecturas. Es una salida segura, pero cuenta como FALLO porque la etiqueta, escrita antes de ejecutar, solo aceptaba R12. **No se ha cambiado la etiqueta después de ver el resultado.**
- **Qué se haría:** una regla en el prompt ("si el cliente corrige un dato, devuelve solo el corregido") y volver a pasar todos los casos. No se ha hecho: la v1 se publica con lo que midió.

### Solo reglas

En los 8 se creó un pedido automático.

| Caso | Qué pasó | Por qué |
|---|---|---|
| 01 | Falta TOR-M8X30-ZN × 1000 | `TORN 8X30` es la referencia del cliente (una equivalencia); el determinista solo lee códigos de Orvalle. La otra línea sí la lee, y el pedido sale con una línea de menos |
| 03 | Automático; tenía que ir a revisión (R11) | El determinista no lee precios en texto: no ve que el cliente pide a 6,50 € con una tarifa de 6,20 € |
| 06 | TUE-M8-ZN × 1000 en lugar de × 1200 | Lee el primer número y no entiende "perdón, son 1200" |
| 10 | Falta TOR-M8X30-ZN × 1000 | `1.000` no es una cantidad limpia y se descarta la línea (prudente), pero el resto del pedido sale sin ella |
| 11 | Falta TOR-M10X40-ZN × 1000 | `2x500` no es una cantidad limpia: igual que el 10 |
| 14 | Falta TOR-M8X30-ZN × 200 | La celda dice `200 uds`: igual que el 10 |
| 15 | TUE-M8-ZN × 500 en lugar de × 800 | Lee el Excel y no la corrección escrita en el cuerpo |
| 16 | TUE-M8-ZN × 400 en lugar de TUE-M10-ZN × 400 | Lee el primer código y no la corrección |

**El patrón de 01, 10, 11 y 14:** descartar una línea dudosa es prudente; crear el pedido con las demás, no. En solo reglas nadie sabe que falta una línea.

## Los ACEPTABLE

| Caso | Dónde | Por qué |
|---|---|---|
| 06 y 15 | Híbrido | La IA leyó bien la corrección y el determinista no: R12 lo manda a revisión. Segura, pero no hacía falta |
| 07 | Las tres | "Os adjunto el pedido", sin adjunto. Lo correcto es pedir datos; sin clasificación, va a revisión (M01) |
| 09 y 13 | Solo reglas | El determinista no lee ninguna línea: revisión (M01) de un pedido claro |
| 17 y 18 | Solo reglas | Va a revisión (M01), sin el motivo correcto (R08) |

## Limitaciones

- **Son 20 casos de desarrollo.** No hay conjunto de prueba congelado ni segunda lectura de las etiquetas.
- **Con 0 fallos en n casos, el error real puede llegar a 3/n** (regla del 3, al 95 % de confianza). El híbrido creó 9 pedidos automáticos sin error: su tasa real de error podría llegar a **3/9 ≈ 33 %**. Solo IA creó 11: **3/11 ≈ 27 %**. Con los 20 casos enteros sería 3/20 = 15 %, pero ahí sí hubo un FALLO, así que no se aplica. Por eso el criterio del piloto pide al menos 300 pedidos automáticos sin error ([04, sección 9.4](../docs/04-solution-design.md#94-piloto-listón-para-pasar-a-producción)).
- **Los 13 correos nuevos y sus etiquetas los escribió Claude Code, que había leído el código del sistema,** incluido el extractor. Los 7 anteriores ya habían servido para construirlo. Las etiquetas se commitearon antes de ejecutar (`cf2f159`), pero nadie más las ha revisado.
- **La mezcla no es la real:** está elegida para cubrir lo que el sistema hace y tiene más casos difíciles que un día normal. El porcentaje de automáticos no se traslada a producción.
- **Una pasada por configuración.** No mide la variación de la IA, que existe (caso 16).
- **Solo se prueba lo construido.** Quedan fuera huecos conocidos que hoy crearían un pedido equivocado sin avisar. Por ejemplo: las unidades y los embalajes no se validan (R10), así que "10 cajas" de un producto que se vende por unidades saldría como 10 unidades; y una consulta con código y cantidad ("¿tenéis 500 uds de…?") podría acabar en pedido, porque falta la clasificación.
- **Tres clientes y diez productos,** limpios y sintéticos. La Parte A no interviene.
- **El modelo lo eligió la cuota gratuita** ([ADR 0005](../docs/decisions/0005-modelo-de-ia.md)).

## Cómo se ejecutó

- **Casos:** 3 de [corte-vertical](../data/synthetic/corte-vertical/), 4 de [extraccion](../data/synthetic/extraccion/) y 13 de [evaluacion-v1](../data/synthetic/evaluacion-v1/), con lo esperado en el `esperado.json` de cada carpeta.
- **Sistema:** modelo `gemini-3.5-flash-lite`; prompt `extraccion` con hash `f1de6b15b7dd…`; extractor determinista 0.1.1. El sistema no se cambió antes, durante ni después.
- **Entrada:** la puerta de pruebas de n8n, la misma que usa la demo. La IA se llamó 36 veces (los dos formatos no soportados no llegan a ella), con unos 305 tokens de entrada y 136 de salida de media.
- **Diferencia con lo diseñado:** las pasadas se hicieron sin reiniciar la base entre ellas, con `--nuevos`. No afecta al resultado: los datos maestros eran los de arranque y no hay regla de duplicados (R07) todavía.

Para repetirla (los resultados con IA pueden variar):

```
for c in solo_reglas solo_ia hibrido; do
  for d in corte-vertical extraccion evaluacion-v1; do
    uv run scripts/enviar_eml.py data/synthetic/$d --configuracion $c --nuevos
  done
done
```

## Caso a caso

| Correo | Esperado | Solo reglas | Solo IA | Híbrido |
|---|---|---|---|---|
| 01-automatico | automático | **FALLO** · automático | OK · automático | OK · automático |
| 02-remitente-desconocido | revisión R02 | OK · revisión R02 | OK · revisión R02 | OK · revisión R02 |
| 03-precio-distinto | revisión R11 | **FALLO** · automático | OK · revisión R11 | OK · revisión R11 |
| 04-excel-xlsx | automático | OK · automático | OK · automático | OK · automático |
| 05-excel-xls | revisión M02 | OK · revisión M02 | OK · revisión M02 | OK · revisión M02 |
| 06-discrepancia | automático | **FALLO** · automático | OK · automático | ACEPTABLE · revisión R12 |
| 07-adjunto-sin-adjunto | pedir datos | ACEPTABLE · revisión M01 | ACEPTABLE · revisión M01 | ACEPTABLE · revisión M01 |
| 08-texto-catalan | automático | OK · automático | OK · automático | OK · automático |
| 09-equivalencias | automático | ACEPTABLE · revisión M01 | OK · automático | OK · automático |
| 10-punto-de-miles | automático | **FALLO** · automático | OK · automático | OK · automático |
| 11-multiplicacion | automático | **FALLO** · automático | OK · automático | OK · automático |
| 12-excel-con-precios | automático | OK · automático | OK · automático | OK · automático |
| 13-excel-cabeceras-raras | automático | ACEPTABLE · revisión M01 | OK · automático | OK · automático |
| 14-excel-unidad-en-celda | automático | **FALLO** · automático | OK · automático | OK · automático |
| 15-discrepancia-excel-cuerpo | automático | **FALLO** · automático | OK · automático | ACEPTABLE · revisión R12 |
| 16-discrepancia-codigo | automático | **FALLO** · automático | **FALLO** · pedir datos R08 | **FALLO** · revisión R08, R12 |
| 17-solo-descripcion | revisión R08 | ACEPTABLE · revisión M01 | OK · revisión R08 | OK · revisión R08 |
| 18-codigo-inexistente | pedir datos R08 | ACEPTABLE · revisión M01 | OK · pedir datos R08 | OK · pedir datos R08 |
| 19-pdf | revisión M02 | OK · revisión M02 | OK · revisión M02 | OK · revisión M02 |
| 20-consulta-sin-cantidad | revisión M01 | OK · revisión M01 | OK · revisión M01 | OK · revisión M01 |

<details>
<summary>Salida de <code>scripts/enviar_eml.py</code></summary>

```
Configuración: solo_reglas
01-automatico.eml                caso  186  automatico  pedido   55  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
02-remitente-desconocido.eml     caso  187  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  188  automatico  pedido   56  motivos -  FALLO: salida automatico, esperada revision; motivos -, esperados R11
Configuración: solo_reglas
04-excel-xlsx.eml                caso  189  automatico  pedido   57  motivos -  OK
05-excel-xls.eml                 caso  190  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  191  automatico  pedido   58  motivos -  FALLO: faltan TUE-M8-ZN x1200; sobran TUE-M8-ZN x1000
07-adjunto-sin-adjunto.eml       caso  192  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_reglas
08-texto-catalan.eml             caso  193  automatico  pedido   59  motivos -  OK
09-equivalencias.eml             caso  194  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
10-punto-de-miles.eml            caso  195  automatico  pedido   60  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
11-multiplicacion.eml            caso  196  automatico  pedido   61  motivos -  FALLO: faltan TOR-M10X40-ZN x1000
12-excel-con-precios.eml         caso  197  automatico  pedido   62  motivos -  OK
13-excel-cabeceras-raras.eml     caso  198  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
14-excel-unidad-en-celda.eml     caso  199  automatico  pedido   63  motivos -  FALLO: faltan TOR-M8X30-ZN x200
15-discrepancia-excel-cuerpo.eml caso  200  automatico  pedido   64  motivos -  FALLO: faltan TUE-M8-ZN x800; sobran TUE-M8-ZN x500
16-discrepancia-codigo.eml       caso  201  automatico  pedido   65  motivos -  FALLO: faltan TUE-M10-ZN x400; sobran TUE-M8-ZN x400
17-solo-descripcion.eml          caso  202  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado revision)
18-codigo-inexistente.eml        caso  203  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
19-pdf.eml                       caso  204  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  205  revision    pedido    -  motivos M01  OK
Configuración: solo_ia
01-automatico.eml                caso  206  automatico  pedido   66  motivos -  OK
02-remitente-desconocido.eml     caso  207  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  208  revision    pedido    -  motivos R11  OK
Configuración: solo_ia
04-excel-xlsx.eml                caso  209  automatico  pedido   67  motivos -  OK
05-excel-xls.eml                 caso  210  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  211  automatico  pedido   68  motivos -  OK
07-adjunto-sin-adjunto.eml       caso  212  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_ia
08-texto-catalan.eml             caso  213  automatico  pedido   69  motivos -  OK
09-equivalencias.eml             caso  214  automatico  pedido   70  motivos -  OK
10-punto-de-miles.eml            caso  215  automatico  pedido   71  motivos -  OK
11-multiplicacion.eml            caso  216  automatico  pedido   72  motivos -  OK
12-excel-con-precios.eml         caso  217  automatico  pedido   73  motivos -  OK
13-excel-cabeceras-raras.eml     caso  218  automatico  pedido   74  motivos -  OK
14-excel-unidad-en-celda.eml     caso  219  automatico  pedido   75  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  220  automatico  pedido   76  motivos -  OK
16-discrepancia-codigo.eml       caso  221  pedir_datos pedido    -  motivos R08  FALLO: salida pedir_datos, esperada automatico; motivos R08, esperados -
17-solo-descripcion.eml          caso  222  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  223  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  224  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  225  revision    pedido    -  motivos M01  OK
Configuración: hibrido
01-automatico.eml                caso  226  automatico  pedido   77  motivos -  OK
02-remitente-desconocido.eml     caso  227  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  228  revision    pedido    -  motivos R11  OK
Configuración: hibrido
04-excel-xlsx.eml                caso  229  automatico  pedido   78  motivos -  OK
05-excel-xls.eml                 caso  230  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  231  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
07-adjunto-sin-adjunto.eml       caso  232  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: hibrido
08-texto-catalan.eml             caso  233  automatico  pedido   79  motivos -  OK
09-equivalencias.eml             caso  234  automatico  pedido   80  motivos -  OK
10-punto-de-miles.eml            caso  235  automatico  pedido   81  motivos -  OK
11-multiplicacion.eml            caso  236  automatico  pedido   82  motivos -  OK
12-excel-con-precios.eml         caso  237  automatico  pedido   83  motivos -  OK
13-excel-cabeceras-raras.eml     caso  238  automatico  pedido   84  motivos -  OK
14-excel-unidad-en-celda.eml     caso  239  automatico  pedido   85  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  240  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
16-discrepancia-codigo.eml       caso  241  revision    pedido    -  motivos R08, R12  FALLO: salida revision, esperada automatico; motivos R08, R12, esperados -
17-solo-descripcion.eml          caso  242  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  243  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  244  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  245  revision    pedido    -  motivos M01  OK
```

</details>
