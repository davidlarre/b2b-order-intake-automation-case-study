# Revisión de las etiquetas de la evaluación v1

Segunda lectura de las 13 etiquetas nuevas (casos 08–20), hecha el 25-11-2026 por una instancia de Claude distinta de la que las escribió, en una conversación aparte. Se leyó cada .eml (cuerpo y adjuntos), su entrada de esperado.json, el catálogo de supabase/seed.sql y, para el caso 20, la sección de clasificación de 04. **No es una revisión humana.**

Resultado: ninguna etiqueta cambia. No se ha vuelto a ejecutar nada.

| Caso | Comprobación | Veredicto |
|---|---|---|
| 08 | Dos líneas en catalán; DIS-COR-125 ×25 y BRO-HSS-8 ×20 coinciden con el texto | Correcta |
| 09 | "torn 8x30" y "arand 8" son equivalencias del cliente: TOR-M8X30-ZN ×500 y ARA-M8-ZN ×2000 | Correcta |
| 10 | "1.000" son mil unidades | Correcta |
| 11 | "Dos bolsas de 500", y el producto se vende por unidades ('ud'): 2x500 = 1000 | Correcta |
| 12 | Excel con precios pactados y fila de total, que no es una línea | Correcta |
| 13 | Excel con cabeceras fuera del mapeo; GUA-NIT-L se vende por cajas: 12 cajas | Correcta |
| 14 | "200 uds" en la celda son 200 | Correcta |
| 15 | El cuerpo dice explícitamente qué línea corrige ("en el Excel pone 500 […] necesito 800 de TUE-M8-ZN") y que el resto está bien: manda el cuerpo | Correcta |
| 16 | "(perdón, es TUE-M10-ZN)" corrige el código sin ambigüedad. Revisión por R08 + R12 no estaba prevista: se mantiene como FALLO, sin cambiar la etiqueta después de ver el resultado | Correcta |
| 17 | Solo descripción, "10 cajas" de guantes de nitrilo L: revisión R08 | Correcta |
| 18 | XK-4471 no existe en el catálogo: pedir datos R08 | Correcta |
| 19 | Adjunto PDF: revisión M02 | Correcta |
| 20 | Pide precio y plazo "para preparar un presupuesto": es una consulta. Según 04, una consulta va a ADV (revisión). Sin clasificación, M01 | Correcta |
