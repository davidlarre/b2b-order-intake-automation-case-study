# Regresión v2: los 20 correos de la v1.1

Los 7 correos de la demo y los 13 de evaluacion-v1, en las tres configuraciones, comparados uno a uno con lo [publicado en la v1.1](resultados-v1-1.md) (pasada 3): salida, motivos y líneas del pedido. 25-11-2026, con `scripts/regresion_v1_1.py`.

## 1. Con los datos maestros nuevos, antes de la clasificación

De 10 productos y 3 clientes a 498 y 120, con 1.408 pedidos de histórico. **60 resultados de 60 iguales a la v1.1.** Es lo que aísla el efecto de los datos: ni el prompt, ni el flujo, ni las reglas habían cambiado.

| Intento | Qué pasó |
|---|---|
| 1 | Con una versión anterior de los datos maestros. 59 iguales; 1 M03 (503 de Gemini) en solo IA |
| 2 | Con los datos definitivos. 57 iguales; 3 M03 (503): dos en solo IA y uno en el híbrido. Solo reglas, 20 de 20 |
| 3 | Solo IA e híbrido, enteros: **40 de 40 iguales** y ningún M03 |

Solo reglas no llama a la IA: vale su pasada del intento 2. Ningún M03 fue por cuota (429). Un M03 es el servicio caído, no un resultado distinto, y todos llegaron a la cola.

<details>
<summary>Salida del intento 2, solo reglas</summary>

```
Configuración: solo_reglas
01-automatico.eml                caso    1  automatico  pedido 1409  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
02-remitente-desconocido.eml     caso    2  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso    3  automatico  pedido 1410  motivos -  FALLO: salida automatico, esperada revision; motivos -, esperados R11
Configuración: solo_reglas
04-excel-xlsx.eml                caso    4  automatico  pedido 1411  motivos -  OK
05-excel-xls.eml                 caso    5  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso    6  automatico  pedido 1412  motivos -  FALLO: faltan TUE-M8-ZN x1200; sobran TUE-M8-ZN x1000
07-adjunto-sin-adjunto.eml       caso    7  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_reglas
08-texto-catalan.eml             caso    8  automatico  pedido 1413  motivos -  OK
09-equivalencias.eml             caso    9  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
10-punto-de-miles.eml            caso   10  automatico  pedido 1414  motivos -  FALLO: faltan TOR-M8X30-ZN x1000
11-multiplicacion.eml            caso   11  automatico  pedido 1415  motivos -  FALLO: faltan TOR-M10X40-ZN x1000
12-excel-con-precios.eml         caso   12  automatico  pedido 1416  motivos -  OK
13-excel-cabeceras-raras.eml     caso   13  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado automatico)
14-excel-unidad-en-celda.eml     caso   14  automatico  pedido 1417  motivos -  FALLO: faltan TOR-M8X30-ZN x200
15-discrepancia-excel-cuerpo.eml caso   15  automatico  pedido 1418  motivos -  FALLO: faltan TUE-M8-ZN x800; sobran TUE-M8-ZN x500
16-discrepancia-codigo.eml       caso   16  automatico  pedido 1419  motivos -  FALLO: faltan TUE-M10-ZN x400; sobran TUE-M8-ZN x400
17-solo-descripcion.eml          caso   17  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado revision)
18-codigo-inexistente.eml        caso   18  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
19-pdf.eml                       caso   19  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso   20  revision    pedido    -  motivos M01  OK
```

</details>

<details>
<summary>Salida del intento 3, solo IA e híbrido</summary>

```
Configuración: solo_ia
01-automatico.eml                caso  151  automatico  pedido 1464  motivos -  OK
02-remitente-desconocido.eml     caso  152  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  164  revision    pedido    -  motivos R11  OK
Configuración: solo_ia
04-excel-xlsx.eml                caso  165  automatico  pedido 1473  motivos -  OK
05-excel-xls.eml                 caso  166  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  167  automatico  pedido 1474  motivos -  OK
07-adjunto-sin-adjunto.eml       caso  168  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: solo_ia
08-texto-catalan.eml             caso  169  automatico  pedido 1475  motivos -  OK
09-equivalencias.eml             caso  170  automatico  pedido 1476  motivos -  OK
10-punto-de-miles.eml            caso  171  automatico  pedido 1477  motivos -  OK
11-multiplicacion.eml            caso  172  automatico  pedido 1478  motivos -  OK
12-excel-con-precios.eml         caso  173  automatico  pedido 1479  motivos -  OK
13-excel-cabeceras-raras.eml     caso  174  automatico  pedido 1480  motivos -  OK
14-excel-unidad-en-celda.eml     caso  175  automatico  pedido 1481  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  176  automatico  pedido 1482  motivos -  OK
16-discrepancia-codigo.eml       caso  177  automatico  pedido 1483  motivos -  OK
17-solo-descripcion.eml          caso  178  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  179  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  180  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  181  revision    pedido    -  motivos M01  OK

20 resultados comparados, 0 distintos de la v1.1
Configuración: hibrido
01-automatico.eml                caso  182  automatico  pedido 1484  motivos -  OK
02-remitente-desconocido.eml     caso  183  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  184  revision    pedido    -  motivos R11  OK
Configuración: hibrido
04-excel-xlsx.eml                caso  185  automatico  pedido 1485  motivos -  OK
05-excel-xls.eml                 caso  186  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  187  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
07-adjunto-sin-adjunto.eml       caso  188  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: hibrido
08-texto-catalan.eml             caso  189  automatico  pedido 1486  motivos -  OK
09-equivalencias.eml             caso  190  automatico  pedido 1487  motivos -  OK
10-punto-de-miles.eml            caso  191  automatico  pedido 1488  motivos -  OK
11-multiplicacion.eml            caso  192  automatico  pedido 1489  motivos -  OK
12-excel-con-precios.eml         caso  193  automatico  pedido 1490  motivos -  OK
13-excel-cabeceras-raras.eml     caso  194  automatico  pedido 1491  motivos -  OK
14-excel-unidad-en-celda.eml     caso  195  automatico  pedido 1492  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  196  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
16-discrepancia-codigo.eml       caso  197  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
17-solo-descripcion.eml          caso  198  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  199  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  200  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  201  revision    pedido    -  motivos M01  OK

20 resultados comparados, 0 distintos de la v1.1
```

</details>

## 2. Con la clasificación puesta

26-11-2026, solo el híbrido (la clasificación no se usa en solo reglas, y solo IA clasifica igual), con 10 s de pausa: `uv run scripts/regresion_v1_1.py --pausa 10 --configuracion hibrido`. Una pasada entera, **sin ningún M03 ni 429**. Mismos datos maestros, prompt de extracción y reglas que en la sección 1; lo nuevo es la clasificación (prompt v2, `gemini-3.5-flash-lite`).

**17 de 20 iguales; 3 distintos.**

| Correo | v1.1 | Con la clasificación | Qué pasa |
|---|---|---|---|
| 20-consulta-sin-cantidad | revisión M01 · OK | revisión R01 (consulta) | **Esperado.** Misma salida; ahora se sabe por qué. La etiqueta de la v1 dice M01 porque entonces no había clasificación |
| 15-discrepancia-excel-cuerpo | revisión R12 · ACEPTABLE | revisión R01 (modificacion_anulacion) | **Error de clasificación.** Es un pedido nuevo en el que el cliente corrige una cantidad del Excel en el cuerpo |
| 16-discrepancia-codigo | revisión R12 · ACEPTABLE | revisión R01 (modificacion_anulacion) | **Error de clasificación.** Pedido nuevo que corrige un código en el propio correo ("perdón, es…") |

- **15 y 16 no crean nada indebido:** van a revisión, como ya iban, pero sin líneas leídas y con un motivo que dice "cambia un pedido ya hecho". La gestora tiene que teclearlos a mano. Son pedidos, y la etiqueta sigue diciendo automático: cuentan como revisiones innecesarias, ahora peor explicadas.
- **Es un patrón, no ruido:** una corrección dentro del propio pedido se lee como una modificación. En desarrollo v2 no hay ningún caso así, y ninguno de los 20 de desarrollo se clasificó mal ([desarrollo](desarrollo-v2.md)).
- **No se ha ajustado nada.** Cambiar el prompt de clasificación a partir de estos dos correos es un ajuste ([registro de cambios](registro-de-cambios.md)): queda como decisión pendiente, antes de ejecutar la prueba.

<details>
<summary>Salida completa</summary>

```
Configuración: hibrido
01-automatico.eml                caso  433  automatico  pedido 1525  motivos -  OK
02-remitente-desconocido.eml     caso  434  revision    pedido    -  motivos R02  OK
03-precio-distinto.eml           caso  435  revision    pedido    -  motivos R11  OK
Configuración: hibrido
04-excel-xlsx.eml                caso  436  automatico  pedido 1526  motivos -  OK
05-excel-xls.eml                 caso  437  revision    pedido    -  motivos M02  OK
06-discrepancia.eml              caso  438  revision    pedido    -  motivos R12  ACEPTABLE (salida segura; esperado automatico)
07-adjunto-sin-adjunto.eml       caso  439  revision    pedido    -  motivos M01  ACEPTABLE (salida segura; esperado pedir_datos)
Configuración: hibrido
08-texto-catalan.eml             caso  440  automatico  pedido 1527  motivos -  OK
09-equivalencias.eml             caso  441  automatico  pedido 1528  motivos -  OK
10-punto-de-miles.eml            caso  442  automatico  pedido 1529  motivos -  OK
11-multiplicacion.eml            caso  443  automatico  pedido 1530  motivos -  OK
12-excel-con-precios.eml         caso  444  automatico  pedido 1531  motivos -  OK
13-excel-cabeceras-raras.eml     caso  445  automatico  pedido 1532  motivos -  OK
14-excel-unidad-en-celda.eml     caso  446  automatico  pedido 1533  motivos -  OK
15-discrepancia-excel-cuerpo.eml caso  447  revision    pedido    -  motivos R01  FALLO: salida revision, esperada automatico; motivos R01, esperados -
16-discrepancia-codigo.eml       caso  448  revision    pedido    -  motivos R01  FALLO: salida revision, esperada automatico; motivos R01, esperados -
17-solo-descripcion.eml          caso  449  revision    pedido    -  motivos R08  OK
18-codigo-inexistente.eml        caso  450  pedir_datos pedido    -  motivos R08  OK
19-pdf.eml                       caso  451  revision    pedido    -  motivos M02  OK
20-consulta-sin-cantidad.eml     caso  452  revision    pedido    -  motivos R01  FALLO: motivos R01, esperados M01

20 resultados comparados, 3 distintos de la v1.1
  hibrido      15-discrepancia-excel-cuerpo.eml   ('revision', 'R12', 'ACEPTABLE (salida segura; esperado automatico)')  ->  ('revision', 'R01', 'FALLO: salida revision, esperada automatico; motivos R01, esperados -')
  hibrido      16-discrepancia-codigo.eml         ('revision', 'R12', 'ACEPTABLE (salida segura; esperado automatico)')  ->  ('revision', 'R01', 'FALLO: salida revision, esperada automatico; motivos R01, esperados -')
  hibrido      20-consulta-sin-cantidad.eml       ('revision', 'M01', 'OK')  ->  ('revision', 'R01', 'FALLO: motivos R01, esperados M01')
```

</details>
