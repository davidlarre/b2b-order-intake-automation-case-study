# Resultados de la evaluación v1.1

**Los mismos 20 correos que en la [v1](resultados-v1.md), con las mismas etiquetas.** Siguen siendo casos de desarrollo: sirven para ver qué hace el sistema y dónde falla, no para estimar su tasa de error. 25-11-2026.

## Qué cambió

1. **Prompt de extracción v3:** una regla nueva, "Si el cliente corrige un dato, devuelve solo el corregido". La motivó el [caso 16](resultados-v1.md#los-fallos-uno-a-uno).
2. **Si falla la IA, el caso va a la cola con M03** (fallo técnico), en lugar de parar el flujo.

## Resumen

Pasada 2, completa. Es la que se publica como v1.1 (ver [las dos pasadas](#las-dos-pasadas)).

| Configuración | OK | ACEPTABLE | FALLO | De ellos, M03 | Pedidos automáticos | Automáticos erróneos o indebidos |
|---|---|---|---|---|---|---|
| Solo reglas | 7 | 5 | 8 | 0 | 11 | **8** |
| Solo IA | 15 | 1 | 4 | 4 | 9 | **0** |
| Híbrido | 15 | 4 | 1 | 1 | 8 | **0** |

En la v1:

| Configuración | OK | ACEPTABLE | FALLO | De ellos, M03 | Pedidos automáticos | Automáticos erróneos o indebidos |
|---|---|---|---|---|---|---|
| Solo reglas | 7 | 5 | 8 | 0 | 11 | **8** |
| Solo IA | 18 | 1 | 1 | 0 | 11 | **0** |
| Híbrido | 16 | 3 | 1 | 0 | 9 | **0** |

OK, ACEPTABLE y FALLO significan lo mismo que en la [v1](resultados-v1.md#resumen). Un M03 cuenta como FALLO aunque el caso llegue a una persona: las etiquetas no lo preveían y no se han cambiado.

## Qué se puede concluir

1. **El caso 16 ya no falla.** Con solo IA crea el pedido correcto (TUE-M10-ZN × 400). En el híbrido va a revisión solo con R12, porque el determinista sigue leyendo el código sin corregir: es ACEPTABLE. Ha salido igual en las dos pasadas.
2. **Los 5 FALLO con IA son M03:** Gemini respondió "503, alta demanda" y se agotaron los reintentos (4 en solo IA y 1 en el híbrido). Antes, esos correos habrían parado el flujo; ahora los cinco están en la cola.
3. **En las 31 llamadas que Gemini contestó, de 36, no hay ningún FALLO.**
4. **Los totales no son directamente comparables con la v1:** entonces Gemini no falló en esa pasada. La peor cifra de OK de la v1.1 (solo IA, 15 frente a 18) sale de los 503; el caso 16, en cambio, mejora. Por eso se compara caso a caso.
5. **Solo reglas no cambia:** no usa la IA, y los 20 casos salen igual.

## Comparación con la v1, caso a caso

v1 → v1.1 (pasada 2). "Igual" quiere decir misma nota, misma salida y mismos motivos.

| Correo | Solo reglas | Solo IA | Híbrido |
|---|---|---|---|
| 01-automatico | igual: **FALLO** · automático | igual: OK · automático | igual: OK · automático |
| 02-remitente-desconocido | igual: OK · revisión R02 | igual: OK · revisión R02 | igual: OK · revisión R02 |
| 03-precio-distinto | igual: **FALLO** · automático | OK · revisión R11 → **FALLO** · revisión M03 | igual: OK · revisión R11 |
| 04-excel-xlsx | igual: OK · automático | igual: OK · automático | igual: OK · automático |
| 05-excel-xls | igual: OK · revisión M02 | igual: OK · revisión M02 | igual: OK · revisión M02 |
| 06-discrepancia | igual: **FALLO** · automático | igual: OK · automático | igual: ACEPTABLE · revisión R12 |
| 07-adjunto-sin-adjunto | igual: ACEPTABLE · revisión M01 | igual: ACEPTABLE · revisión M01 | igual: ACEPTABLE · revisión M01 |
| 08-texto-catalan | igual: OK · automático | OK · automático → **FALLO** · revisión M03 | igual: OK · automático |
| 09-equivalencias | igual: ACEPTABLE · revisión M01 | OK · automático → **FALLO** · revisión M03 | igual: OK · automático |
| 10-punto-de-miles | igual: **FALLO** · automático | igual: OK · automático | igual: OK · automático |
| 11-multiplicacion | igual: **FALLO** · automático | igual: OK · automático | igual: OK · automático |
| 12-excel-con-precios | igual: OK · automático | OK · automático → **FALLO** · revisión M03 | OK · automático → **FALLO** · revisión M03 |
| 13-excel-cabeceras-raras | igual: ACEPTABLE · revisión M01 | igual: OK · automático | igual: OK · automático |
| 14-excel-unidad-en-celda | igual: **FALLO** · automático | igual: OK · automático | igual: OK · automático |
| 15-discrepancia-excel-cuerpo | igual: **FALLO** · automático | igual: OK · automático | igual: ACEPTABLE · revisión R12 |
| 16-discrepancia-codigo | igual: **FALLO** · automático | **FALLO** · pedir datos R08 → OK · automático | **FALLO** · revisión R08, R12 → ACEPTABLE · revisión R12 |
| 17-solo-descripcion | igual: ACEPTABLE · revisión M01 | igual: OK · revisión R08 | igual: OK · revisión R08 |
| 18-codigo-inexistente | igual: ACEPTABLE · revisión M01 | igual: OK · pedir datos R08 | igual: OK · pedir datos R08 |
| 19-pdf | igual: OK · revisión M02 | igual: OK · revisión M02 | igual: OK · revisión M02 |
| 20-consulta-sin-cantidad | igual: OK · revisión M01 | igual: OK · revisión M01 | igual: OK · revisión M01 |

## Las dos pasadas

**Pasada 1.** Gemini estaba saturado: 10 casos acabaron en M03, todos por 503. Además, `enviar_eml.py` esperaba 120 s y el flujo puede tardar unos 190 s en agotar los tres intentos: en el caso 07 del híbrido el script se cortó y su resultado (M03) se ha leído de la base de datos. El resto de los casos se ejecutó.

| Configuración | OK | ACEPTABLE | FALLO | De ellos, M03 | Pedidos automáticos | Automáticos erróneos o indebidos |
|---|---|---|---|---|---|---|
| Solo reglas | 7 | 5 | 8 | 0 | 11 | **8** |
| Solo IA | 17 | 1 | 2 | 2 | 10 | **0** |
| Híbrido | 10 | 2 | 8 | 8 | 5 | **0** |

**Pasada 2.** Solo cambia la espera del script, a 240 s. La decisión de publicar la segunda como cabecera, saliera lo que saliera, se tomó con la primera a medias (vista solo IA entera y el híbrido hasta el caso 07, con 4 M03) y antes de empezar la segunda. No hubo una tercera.

| Correo (pasada 1) | Solo IA | Híbrido |
|---|---|---|
| 01-automatico | OK · automático | OK · automático |
| 02-remitente-desconocido | OK · revisión R02 | OK · revisión R02 |
| 03-precio-distinto | OK · revisión R11 | **FALLO** · revisión M03 |
| 04-excel-xlsx | **FALLO** · revisión M03 | OK · automático |
| 05-excel-xls | OK · revisión M02 | OK · revisión M02 |
| 06-discrepancia | OK · automático | ACEPTABLE · revisión R12 |
| 07-adjunto-sin-adjunto | ACEPTABLE · revisión M01 | **FALLO** · revisión M03 |
| 08-texto-catalan | OK · automático | **FALLO** · revisión M03 |
| 09-equivalencias | OK · automático | OK · automático |
| 10-punto-de-miles | OK · automático | **FALLO** · revisión M03 |
| 11-multiplicacion | **FALLO** · revisión M03 | OK · automático |
| 12-excel-con-precios | OK · automático | **FALLO** · revisión M03 |
| 13-excel-cabeceras-raras | OK · automático | OK · automático |
| 14-excel-unidad-en-celda | OK · automático | **FALLO** · revisión M03 |
| 15-discrepancia-excel-cuerpo | OK · automático | **FALLO** · revisión M03 |
| 16-discrepancia-codigo | OK · automático | ACEPTABLE · revisión R12 |
| 17-solo-descripcion | OK · revisión R08 | **FALLO** · revisión M03 |
| 18-codigo-inexistente | OK · pedir datos R08 | OK · pedir datos R08 |
| 19-pdf | OK · revisión M02 | OK · revisión M02 |
| 20-consulta-sin-cantidad | OK · revisión M01 | OK · revisión M01 |

## Prueba de M03

Con el correo 01 y un fallo forzado cada vez. Los siete casos quedaron en `en_revision` con M03 abierto, y la cola de la app los devuelve.

| Fallo | Cómo se forzó | Configuración |
|---|---|---|
| Modelo inexistente (404 real de Gemini) | Versión de prompt temporal, ya borrada | Solo IA e híbrido |
| Error HTTP 500 | Servidor local en lugar de Gemini | Híbrido |
| Tiempo agotado | Igual, con un límite de 3 s | Híbrido |
| Respuesta sin `model_output` | Igual | Híbrido |
| `model_output` que no es JSON | Igual | Híbrido |
| JSON que no cumple el esquema | Igual | Solo IA |

Con el modelo inexistente, solo reglas siguió creando su pedido: no llama a la IA.

## Limitaciones

Las de la [v1](resultados-v1.md#limitaciones), y además:

- **La regla nueva salió de un caso de este mismo conjunto.** Que el 16 mejore es lo esperable, no una prueba de que generalice.
- **Con 0 errores, la regla del 3 da** 3/9 ≈ 33 % en solo IA y 3/8 ≈ 38 % en el híbrido.
- **M03 no distingue una caída general de un caso raro.** El diseño ([04, sección 2.6](../docs/04-solution-design.md#26-fallos-técnicos-caída-general-y-modo-manual)) reintenta más tarde en una caída general; la v1.1 manda el caso a una persona. Una respuesta no válida no se reintenta.

## Cómo se ejecutó

- **Sistema:** modelo `gemini-3.5-flash-lite`; prompt `extraccion` con hash `ea73c9fd7c06…`; extractor determinista 0.1.1. El prompt, el flujo y las reglas no cambiaron entre las dos pasadas.
- **Versión del prompt:** "v3" es su tercera versión en la historia del repo. En la base local, reiniciada para la demo, es la 2: lo que identifica a un prompt es su hash.
- **Comando:** el de la [v1](resultados-v1.md#cómo-se-ejecutó), sin reiniciar la base, con `--nuevos`.

<details>
<summary>Salida de <code>scripts/enviar_eml.py</code>, pasada 2</summary>

```
Configuración: solo_reglas
01-automatico.eml                caso  349  automatico  pedido  113  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
02-remitente-desconocido.eml     caso  350  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  351  automatico  pedido  114  motivos -  FALLO: salida automatico, esperada revision; motivos -, esperados R11
Configuración: solo_reglas
04-excel-xlsx.eml                caso  352  automatico  pedido  115  motivos -  OK
05-excel-xls.eml                 caso  353  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  354  automatico  pedido  116  motivos -  FALLO: faltan TUE-M8-ZN x1200; sobran TUE-M8-ZN x1000
07-adjunto-sin-adjunto.eml       caso  355  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_reglas
08-texto-catalan.eml             caso  356  automatico  pedido  117  motivos -  OK
09-equivalencias.eml             caso  357  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
10-punto-de-miles.eml            caso  358  automatico  pedido  118  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
11-multiplicacion.eml            caso  359  automatico  pedido  119  motivos -  FALLO: faltan TOR-M10X40-ZN x1000
12-excel-con-precios.eml         caso  360  automatico  pedido  120  motivos -  OK
13-excel-cabeceras-raras.eml     caso  361  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
14-excel-unidad-en-celda.eml     caso  362  automatico  pedido  121  motivos -  FALLO: faltan TOR-M8X30-ZN x200
15-discrepancia-excel-cuerpo.eml caso  363  automatico  pedido  122  motivos -  FALLO: faltan TUE-M8-ZN x800; sobran TUE-M8-ZN x500
16-discrepancia-codigo.eml       caso  364  automatico  pedido  123  motivos -  FALLO: faltan TUE-M10-ZN x400; sobran TUE-M8-ZN x400
17-solo-descripcion.eml          caso  365  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado revision)
18-codigo-inexistente.eml        caso  366  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
19-pdf.eml                       caso  367  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  368  revision    pedido    -  motivos M01  OK
Configuración: solo_ia
01-automatico.eml                caso  369  automatico  pedido  124  motivos -  OK
02-remitente-desconocido.eml     caso  370  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  371  revision    pedido    -  motivos M03  FALLO: motivos M03, esperados R11
Configuración: solo_ia
04-excel-xlsx.eml                caso  372  automatico  pedido  125  motivos -  OK
05-excel-xls.eml                 caso  373  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  374  automatico  pedido  126  motivos -  OK
07-adjunto-sin-adjunto.eml       caso  375  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_ia
08-texto-catalan.eml             caso  376  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
09-equivalencias.eml             caso  377  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
10-punto-de-miles.eml            caso  378  automatico  pedido  127  motivos -  OK
11-multiplicacion.eml            caso  379  automatico  pedido  128  motivos -  OK
12-excel-con-precios.eml         caso  380  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
13-excel-cabeceras-raras.eml     caso  381  automatico  pedido  129  motivos -  OK
14-excel-unidad-en-celda.eml     caso  382  automatico  pedido  130  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  383  automatico  pedido  131  motivos -  OK
16-discrepancia-codigo.eml       caso  384  automatico  pedido  132  motivos -  OK
17-solo-descripcion.eml          caso  385  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  386  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  387  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  388  revision    pedido    -  motivos M01  OK
Configuración: hibrido
01-automatico.eml                caso  389  automatico  pedido  133  motivos -  OK
02-remitente-desconocido.eml     caso  390  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  391  revision    pedido    -  motivos R11  OK
Configuración: hibrido
04-excel-xlsx.eml                caso  392  automatico  pedido  134  motivos -  OK
05-excel-xls.eml                 caso  393  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  394  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
07-adjunto-sin-adjunto.eml       caso  395  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: hibrido
08-texto-catalan.eml             caso  396  automatico  pedido  135  motivos -  OK
09-equivalencias.eml             caso  397  automatico  pedido  136  motivos -  OK
10-punto-de-miles.eml            caso  398  automatico  pedido  137  motivos -  OK
11-multiplicacion.eml            caso  399  automatico  pedido  138  motivos -  OK
12-excel-con-precios.eml         caso  400  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
13-excel-cabeceras-raras.eml     caso  401  automatico  pedido  139  motivos -  OK
14-excel-unidad-en-celda.eml     caso  402  automatico  pedido  140  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  403  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
16-discrepancia-codigo.eml       caso  404  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
17-solo-descripcion.eml          caso  405  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  406  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  407  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  408  revision    pedido    -  motivos M01  OK
```

</details>

<details>
<summary>Salida de <code>scripts/enviar_eml.py</code>, pasada 1</summary>

```
Configuración: solo_reglas
01-automatico.eml                caso  199  automatico  pedido   61  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
02-remitente-desconocido.eml     caso  200  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  201  automatico  pedido   62  motivos -  FALLO: salida automatico, esperada revision; motivos -, esperados R11
Configuración: solo_reglas
04-excel-xlsx.eml                caso  202  automatico  pedido   63  motivos -  OK
05-excel-xls.eml                 caso  203  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  204  automatico  pedido   64  motivos -  FALLO: faltan TUE-M8-ZN x1200; sobran TUE-M8-ZN x1000
07-adjunto-sin-adjunto.eml       caso  205  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_reglas
08-texto-catalan.eml             caso  206  automatico  pedido   65  motivos -  OK
09-equivalencias.eml             caso  207  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
10-punto-de-miles.eml            caso  208  automatico  pedido   66  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
11-multiplicacion.eml            caso  209  automatico  pedido   67  motivos -  FALLO: faltan TOR-M10X40-ZN x1000
12-excel-con-precios.eml         caso  210  automatico  pedido   68  motivos -  OK
13-excel-cabeceras-raras.eml     caso  211  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
14-excel-unidad-en-celda.eml     caso  212  automatico  pedido   69  motivos -  FALLO: faltan TOR-M8X30-ZN x200
15-discrepancia-excel-cuerpo.eml caso  213  automatico  pedido   70  motivos -  FALLO: faltan TUE-M8-ZN x800; sobran TUE-M8-ZN x500
16-discrepancia-codigo.eml       caso  214  automatico  pedido   71  motivos -  FALLO: faltan TUE-M10-ZN x400; sobran TUE-M8-ZN x400
17-solo-descripcion.eml          caso  215  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado revision)
18-codigo-inexistente.eml        caso  216  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
19-pdf.eml                       caso  217  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  218  revision    pedido    -  motivos M01  OK
Configuración: solo_ia
01-automatico.eml                caso  219  automatico  pedido   72  motivos -  OK
02-remitente-desconocido.eml     caso  220  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  221  revision    pedido    -  motivos R11  OK
Configuración: solo_ia
04-excel-xlsx.eml                caso  222  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
05-excel-xls.eml                 caso  223  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  224  automatico  pedido   73  motivos -  OK
07-adjunto-sin-adjunto.eml       caso  225  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_ia
08-texto-catalan.eml             caso  226  automatico  pedido   74  motivos -  OK
09-equivalencias.eml             caso  227  automatico  pedido   75  motivos -  OK
10-punto-de-miles.eml            caso  228  automatico  pedido   76  motivos -  OK
11-multiplicacion.eml            caso  229  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
12-excel-con-precios.eml         caso  230  automatico  pedido   77  motivos -  OK
13-excel-cabeceras-raras.eml     caso  231  automatico  pedido   78  motivos -  OK
14-excel-unidad-en-celda.eml     caso  232  automatico  pedido   79  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  233  automatico  pedido   80  motivos -  OK
16-discrepancia-codigo.eml       caso  234  automatico  pedido   81  motivos -  OK
17-solo-descripcion.eml          caso  235  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  236  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  237  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  238  revision    pedido    -  motivos M01  OK
Configuración: hibrido
01-automatico.eml                caso  239  automatico  pedido   82  motivos -  OK
02-remitente-desconocido.eml     caso  240  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  241  revision    pedido    -  motivos M03  FALLO: motivos M03, esperados R11
Configuración: hibrido
04-excel-xlsx.eml                caso  242  automatico  pedido   83  motivos -  OK
05-excel-xls.eml                 caso  243  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  244  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
TimeoutError: timed out
Configuración: hibrido
08-texto-catalan.eml             caso  246  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
09-equivalencias.eml             caso  247  automatico  pedido   84  motivos -  OK
10-punto-de-miles.eml            caso  248  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
11-multiplicacion.eml            caso  249  automatico  pedido  111  motivos -  OK
12-excel-con-precios.eml         caso  340  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
13-excel-cabeceras-raras.eml     caso  341  automatico  pedido  112  motivos -  OK
14-excel-unidad-en-celda.eml     caso  342  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
15-discrepancia-excel-cuerpo.eml caso  343  revision    pedido    -  motivos M03  FALLO: salida revision, esperada automatico; motivos M03, esperados -
16-discrepancia-codigo.eml       caso  344  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
17-solo-descripcion.eml          caso  345  revision    pedido    -  motivos M03  FALLO: motivos M03, esperados R08
18-codigo-inexistente.eml        caso  346  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  347  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  348  revision    pedido    -  motivos M01  OK
```

</details>
