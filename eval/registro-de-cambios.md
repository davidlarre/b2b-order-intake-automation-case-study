# Registro de cambios del sistema

Cada cambio en lo que lee o decide el sistema (prompt y ejemplos, esquema, preprocesado, extractor determinista, mapeo de cabeceras, parámetros, reglas y datos maestros) se anota aquí ([05, sección 8](../docs/05-synthetic-data-and-evaluation-set.md)).

- **Construir:** el código pasa a cumplir la especificación. Criterio: el test se puede escribir con la especificación en la mano. Cita la especificación.
- **Ajuste:** cambia el comportamiento o la especificación a partir de lo visto en un correo. Solo puede salir del conjunto de desarrollo, y cita el caso que lo motivó.
- Después de ejecutar la prueba, todo cambio es "prueba tras corrección".

| Fecha | Qué cambia | Versión | Tipo | Por qué (especificación o caso de desarrollo) |
|---|---|---|---|---|
| 19-11-2026 | Extractor determinista: una multiplicación ("2x500", "3 × 100", "4*25") no es una cantidad | `orvalle-extractor` 0.1.1 | Construir | D19 y 04, sección 6.3: solo "cantidad numérica limpia". Test escribible sin mirar ningún correo |
| 19-11-2026 | R12 también marca la omisión de la IA (una línea que lee el determinista y la IA no) | Migración `20261120000006` | Cambio de especificación, en la dirección segura | Declarado en 04, sección 3.2: sin él, un pedido saldría en automático con una línea de menos |
| 19-11-2026 | Prompt de extracción: la lista de líneas puede estar vacía (sin `minItems: 1`) y la regla 7 dice que, sin líneas, devuelva `lineas` vacío. Un caso sin líneas va a revisión con M01 en las tres configuraciones | Prompt `extraccion` v2; migración `20261120000008` | Construir | D22 (sin líneas no hay pedido) y la regla 7 del prompt ("no inventes nada"). Con `minItems: 1`, la salida estructurada obligaba a Gemini a inventarse una línea. M01 y no "pedir datos" mientras no haya clasificación: declarado en 04, sección 6.3 |
