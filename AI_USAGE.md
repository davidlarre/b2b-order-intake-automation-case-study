# Uso de IA en este proyecto

Este caso de estudio se hace con asistencia de IA. Este documento explica para qué se ha usado, qué es mío y qué no se debe interpretar a partir del resultado.

## Cómo se ha usado

- **Decisiones de diseño, en conversación con Claude (Opus).** El enfoque, el caso, el escenario, las reglas, la evaluación y el plan se han debatido con opciones, alternativas descartadas y recomendaciones. Quedan registradas en [01-reframe-decisions.md](docs/01-reframe-decisions.md).
- **Redacción, commits y revisión de coherencia, con Claude Code (Sonnet y Opus).** Redacta los documentos a partir de lo decidido, mantiene los enlaces entre documentos y hace los commits que le pido.
- **Revisión cruzada entre ambos.** Lo que sale de una conversación se contrasta con lo que ya está en el repositorio antes de escribirlo. Algunos ejemplos:
  - Claude Code detectó que una decisión nombraba una empresa real, en contra de lo que esa misma decisión pedía.
  - Antes de redactar el taller de discovery, señaló los puntos en los que contradecía el caso de negocio y las decisiones previas: el número de fuentes de equivalencias, una sesión que faltaba con dirección comercial y un criterio de paso imposible de cumplir. Cada choque se resolvió por decisión mía antes de escribir.
- **Datos sintéticos, con Claude Code.** Los 13 correos nuevos de la evaluación v1 y sus etiquetas los escribió Claude Code, que conocía el código del sistema. Se commitearon antes de ejecutar nada ([resultados](eval/resultados-v1.md)). Después, una segunda instancia de Claude que no las escribió [revisó](eval/revision-etiquetas-v1.md) las 13 etiquetas, contrastándolas con los correos y el catálogo, sin cambios. Todavía no hay revisión humana. En la v2, Claude Code ha escrito las listas de partida, los 80 correos (también los de catalán) y todas las etiquetas ([detalle](data/synthetic/evaluacion-v2/README.md)). Estaba previsto que yo escribiera unos 15 y etiquetara todos: no se ha hecho, y las etiquetas no tienen todavía revisión humana.
- **Código, con Claude Code.** Las reglas en SQL, el extractor, los scripts, los tests y la app de revisión se han hecho con Claude Code. También los documentos de la v1 (README, caso y guion).
- **Vídeo de demo, con Claude Code.** El vídeo de demo lo grabó y montó Claude Code de forma automática; sin voz. La pantalla de terminal es la salida real de scripts/preparar_demo.sh, reproducida con formato, no una captura.
- **IA dentro de la solución: Gemini**, en el nivel gratuito de Google AI Studio, para clasificar los correos y extraer los pedidos. Es otra familia de modelos que la que genera los datos, para que no compartan los mismos sesgos. Por el mismo motivo, Gemini no genera ni etiqueta nada del conjunto de evaluación ([ADR 0005](docs/decisions/0005-modelo-de-ia.md)).

## Qué es mío

- Las decisiones finales: en cada punto con opciones, elijo, corrijo o descarto la propuesta.
- El escenario y los hallazgos del taller, propuestos con Claude y aprobados por mí.

## Qué no se presenta

- No es experiencia de ingeniería en producción. Es una demo con datos sintéticos y una empresa ficticia.
- Las cifras del escenario son supuestos y el taller de discovery es simulado: muestran un método, no evidencia.
- El código está asistido por IA. El objetivo es entender y poder explicar cada pieza, no presentarla como escrita sin ayuda.

El historial de commits refleja la asistencia: los commits hechos con Claude Code llevan la línea `Co-Authored-By`.
