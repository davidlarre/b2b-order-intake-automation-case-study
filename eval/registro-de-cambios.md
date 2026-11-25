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
| 25-11-2026 | Prompt de extracción: regla 8, "Si el cliente corrige un dato, devuelve solo el corregido" | Prompt `extraccion` v3, hash `ea73c9fd7c063862ef6cedeafe410cc68df4ff8c1832a7f5131705a1171990e4` | Ajuste | Caso de desarrollo 16 (`16-discrepancia-codigo`) de la evaluación v1. [Resultados v1.1](resultados-v1-1.md) |
| 25-11-2026 | Si Gemini falla (error HTTP, tiempo agotado o respuesta no válida), el caso va a revisión con M03 en lugar de parar el flujo | Flujo `corte-vertical-pedido-desde-eml` | Construir, con una simplificación declarada | 04, sección 2.6. En una caída general también va a M03: el reintento posterior no está hecho |
| 25-11-2026 | Datos maestros: de 3 clientes y 10 productos a 120 y 498, con histórico, conversiones y festivos (estado correcto, semilla fija) | Migración `20261125000001`; `supabase/seeds/maestros.sql` | Construir | 05, secciones 1–4, y decisión 1B. [Regresión](regresion-v2.md): 60 de 60 iguales |
| 25-11-2026 | Clasificación del correo con Gemini antes de la extracción, y R01. Entrada: cuerpo, Excel, asunto y nombre de los adjuntos. Un fallo va a M03 | Prompt `clasificacion` v1, hash `c761b231b9f4…`; migración `20261125000002`; flujo `corte-vertical-pedido-desde-eml` | Construir | 04, secciones 2.2, 3.1 y 6.1. Escrito desde la especificación; sin ajustes de desarrollo |
| 25-11-2026 | Modelo de la clasificación: de `gemini-3.1-flash-lite` a `gemini-3.5-flash-lite`. Mismo texto | Prompt `clasificacion` v2, hash `be628fae8dfdfef0d0a6a60770b847b6eeb1df9c3b59cb9571cb29800fd0c315` | Cambio de especificación (ADR 0005) | Disponibilidad: 503 continuado en el 3.1. No lo motivó ningún resultado |
| 25-11-2026 | Un pedido sin líneas sigue yendo a M01, aunque ya hay clasificación | — | Aplazamiento declarado | 04, sección 6.3: sin envíos ni plazo de 24 h, saldría de la cola y nadie lo vería |
