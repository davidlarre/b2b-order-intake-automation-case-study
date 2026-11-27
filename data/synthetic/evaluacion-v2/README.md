# Evaluación v2: 80 correos

20 de desarrollo y 60 de prueba, con la mezcla de [D23](../../../docs/01-reframe-decisions.md#d23--conjuntos-de-datos) y el diseño de [05](../../../docs/05-synthetic-data-and-evaluation-set.md). En total, 86 `.eml`: cinco casos de la prueba (P14–P18) llevan respuestas del cliente.

**Todo es sintético y todos los dominios son `.example`.**

| Carpeta o fichero | Qué es |
|---|---|
| `desarrollo/`, `prueba/` | Un conjunto cada una |
| `…/fichas/` | Lo que pretendía cada correo, con el texto que escribiría una persona |
| `…/correos/` | Los `.eml`, montados por [generar_correos.py](../../../scripts/generar_correos.py) |
| `…/etiquetas/` | Lo correcto, según la [guía](guia-etiquetado.md) |
| [manifiesto-prueba.json](manifiesto-prueba.json) | SHA-256 de la prueba congelada (tag `prueba-v2.1`; `prueba-v2` antes de la fe de erratas) |
| [Alcance](../../../eval/alcance-prueba-v2.md) | Qué casos de la prueba cuentan hoy, fijado antes de congelar |

## La prueba se ejecuta una sola vez

Solo desde [ejecutar_prueba.py](../../../scripts/ejecutar_prueba.py), una pasada por configuración, que comprueba el manifiesto antes de enviar nada; `enviar_eml.py` se niega a enviar nada de `prueba/`. Solo reglas y el híbrido se ejecutaron el 26-11-2026; solo IA, el 27-11-2026, por la cuota de Gemini. Resultados: [06 · Informe de evaluación](../../../docs/06-evaluation-report.md).

## Cómo se generaron

- **Quién escribe:** Claude Code (`claude-opus-5-5`, 25-11-2026), los 80. Cuerpo, firma y celdas están en las fichas tal como salieron: son la respuesta en bruto. No se regeneró ninguno. La extracción y la clasificación usan Gemini, otra familia ([ADR 0005](../../../docs/decisions/0005-modelo-de-ia.md)).
- **Quién etiqueta:** Claude Code. El borrador sale de la ficha y del `.eml`; la salida, los motivos y la cabecera, de la especificación. **Sin revisión humana.**
- **Revisión de etiquetas, antes de ejecutar:** otra instancia de Claude leyó las etiquetas de los 38 casos en alcance ([revisión](../../../eval/revision-etiquetas-v2.md)). Una corrección, en la cabecera de P23 (`observaciones_entrega`), hecha como fe de erratas: el manifiesto pasa al tag `prueba-v2.1` y anota el cambio; `prueba-v2` se conserva.
- **Diferencias con 05:** estaba previsto que David escribiera unos 15 (incluidos los de catalán) y etiquetara todos. No se ha hecho. El catalán es de un modelo: más correcto que el de un cliente real. Si se hace después, es una prueba nueva, con otro manifiesto y otro tag.
- **El autor conocía el sistema y la prueba.** Quien escribió los correos había leído el código, y después construyó la clasificación. El prompt solo se ajusta con desarrollo, pero no se puede decir que sea ciego.
- **Contrastes hechos sin ejecutar el sistema:** esquema; líneas literales en el correo; y R02, R04, R09, R10, R11, R13 y R14 recalculadas en Python desde 04 ([tests](../../../tests/test_evaluacion_v2.py)). La comparación con las reglas SQL que pide 05 se ha hecho solo con desarrollo.
