# 0002 · Prompt y esquema como fuente única; la evaluación pasa por el flujo

Fecha: 2026-11-18 · Estado: aceptado · Confirma con cambios: D33 (extracción), D34

## Contexto

D33 dejó abierto dónde vive el prompt y cómo lo lee n8n. Si lo que corre en n8n no es exactamente lo que se evalúa, las métricas no valen nada. El riesgo no está solo en el prompt: antes de llegar al modelo, el Excel se pasa a texto, y si n8n y un script de Python lo hicieran cada uno a su manera, el modelo recibiría entradas distintas sin que nadie se diera cuenta.

## Decisión

**Fuente única del prompt y del esquema**

- La fuente es `extraction/` en el repositorio: los tres prompts (clasificación, extracción y respuesta del cliente), el esquema JSON y los ejemplos.
- Un script los carga en `intake.prompt_versiones` con su versión, su hash y cuál está activa. n8n lee la versión activa, y cada extracción guarda con qué versión se hizo.
- El script de evaluación compara el hash del archivo con el de la versión activa y se para si no coinciden.
- Los ejemplos forman parte de la versión: cambiar uno cambia la versión.
- **Tres prompts separados**, no uno: el tipo y las líneas se miden por separado, y cada prompt es más sencillo. El coste de la segunda llamada es pequeño.

**La evaluación pasa por el propio flujo**

- n8n tiene una segunda entrada, un webhook de pruebas que recibe un `.eml` y ejecuta el mismo subflujo "Procesar" que la entrada de Gmail: preprocesado, extractor determinista, prompts y `evaluar_caso`.
- El script de evaluación no reimplementa nada: envía los `.eml`, recoge los resultados y calcula las métricas.
- La configuración (solo reglas, solo IA o híbrido) se elige con un parámetro. Son dos interruptores sobre las mismas piezas: el extractor determinista y la IA.
- Los casos de la entrada de pruebas dejan sus envíos como `simulado`, que nunca se envían.
- Cada pasada empieza con la base de datos limpia, y los `.eml` se envían por orden de su cabecera `Date`.
- **Reproducción en dos niveles** (D34): las métricas se recalculan desde los resultados guardados sin n8n ni clave; opcionalmente, un modo de reproducción lee las respuestas del modelo guardadas en lugar de llamarlo. La clave de la respuesta guardada es el hash de la entrada exacta al modelo, del prompt, del modelo y de la repetición, no el identificador del caso ([05](../05-synthetic-data-and-evaluation-set.md)).

**Validación del esquema en dos capas:** la salida estructurada del proveedor y `pg_jsonschema` en la base de datos ([ADR 0001](0001-reglas-en-sql.md)).

## Alternativas descartadas

- **n8n lee el archivo del repositorio por URL:** depende de GitHub y de que el repositorio sea público, y un push cambia la producción al momento, sin paso de activación ni forma de volver atrás.
- **n8n lee el archivo desde una carpeta montada:** solo funciona con n8n en local y ata esta decisión al [ADR 0004](0004-n8n-local-o-nube.md).
- **Prompt copiado en n8n:** descartada en D33.
- **Script de evaluación independiente con un test de paridad del preprocesado:** funciona, pero mantiene dos implementaciones y solo detecta las diferencias que aparezcan en los Excel de desarrollo.

## Consecuencias

- Lo que se mide es lo que funciona, por construcción. Cada resultado se puede atribuir a una versión del prompt. Si se cambia algo después de ejecutar la prueba, la versión deja constancia (D23).
- Para evaluar, n8n tiene que estar en marcha. Una evaluación completa son 420 ejecuciones (60 correos × 7 pasadas) y se estima en 1–2 h.
- El extractor determinista vive en un nodo Code de n8n, en JavaScript. No se recorta: el híbrido lo necesita. Se acota a Excel por nombre de columna y a expresiones regulares para códigos exactos y su cantidad.
- Con el plan B, la evaluación llama al flujo de Python, que pasa a ser el sistema.
