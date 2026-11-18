# 00 · Plan del proyecto

## Qué es

Caso de estudio educativo y de portfolio sobre la entrada automatizada de pedidos B2B por email, de punta a punta: discovery, diseño, construcción, evaluación, adopción y portfolio. La empresa (Orvalle Suministros Industriales), sus datos y sus cifras son ficticios y sintéticos.

Es un único caso integrado. La IA forma parte de la solución desde el diseño, combinada con reglas, revisión humana y evaluación:

- **Parte A, datos maestros:** migración de lo que vive fuera del ERP (direcciones, contactos, tarifas pactadas y equivalencias de referencias) con mapeo, validación, informe de errores y carga repetible. Sin IA.
- **Parte B, flujo de pedidos:** cada correo que llega a pedidos@ termina como pedido validado en el ERP con confirmación al cliente, como petición concreta de datos al cliente o como excepción para una persona.

Las decisiones de partida están en [01-reframe-decisions.md](01-reframe-decisions.md).

## Principios

1. **Honestidad.** Se distinguen siempre escenario, supuestos, medición y proyección.
2. **Hecho con IA, y se dice.** En `AI_USAGE.md`.
3. **Entenderlo todo.** El porqué de cada decisión y preguntas de comprensión. Ante una pregunta, razonar siempre en voz alta.
4. **IA donde aporta.** Las reglas son la línea base y el control; las decisiones de negocio nunca las toma solo la IA.
5. **Realismo.**
6. **Una cosa cada vez.**

## Fases

Sin calendario fijo: se planifica fase a fase.

Los documentos se numeran por orden de lectura, no por fase (p. ej., la fase 2, diseño, produce 04-solution-design.md).

| # | Fase | Sale | Modelo |
|---|---|---|---|
| 0 | Reencuadre | Decisiones del reencuadre (01), plan y repositorio limpios | Opus (decisiones), Sonnet (redacción) |
| 1 | Discovery | AS-IS, mapa del proceso, oportunidades priorizadas, business case con supuestos | Opus (decisiones), Sonnet (redacción) |
| 2 | Diseño | TO-BE, reglas, datos mínimos, criterios de aceptación, stack (ADR). Los requisitos van integrados aquí | Opus |
| 3 | Datos y evaluación | Datos sintéticos y casos etiquetados, antes de construir | Opus (método), Sonnet (generación) |
| 4 | Construcción | Ver orden más abajo | Sonnet; Opus en diseño de módulos y depuración difícil |
| 5 | Evaluación | Comparación de configuraciones, cronómetro, coste por caso | Opus (método), Sonnet (ejecución) |
| 6 | Adopción y gobierno | Guía, formación, permisos, AI Act | Sonnet |
| 7 | Portfolio | README, página del caso, vídeo de 3 min | Sonnet |

**Orden de construcción:**

1. Supabase y la carga de datos maestros, con el histórico de pedidos.
2. n8n: de Gmail a la extracción con IA en JSON. Empieza por la prueba de lectura del `.eml` ([04, sección 12](04-solution-design.md#12-notas-para-la-construcción)).
3. Reglas y creación del pedido.
4. Respuestas automáticas y excepciones.
5. App de revisión.
6. Consultas SQL.
7. Evaluación.

Cada incremento se cierra con su check y un commit. La demo debe poder enseñarse en directo en 3 minutos.

**Recortes si falta tiempo, en este orden:** PDF → panel → modificaciones de pedido → correos con varios pedidos → app de revisión (se sustituye por la vista de Supabase). No se recorta la evaluación.

**Plan B del incremento de n8n:** si tras 2 sesiones no funciona, el flujo corre como script de Python con los mismos pasos, las mismas reglas y la misma extracción, y el motivo se documenta en un ADR. n8n es la pieza principal del portfolio. El criterio concreto de "no funciona" está en el [ADR 0003](decisions/0003-n8n-orquestador-plan-b.md).

## Método por fase

1. Se explican los conceptos y por qué importan.
2. David decide entre 2–4 opciones con una recomendación.
3. Se redacta el borrador o el código.
4. David revisa y reescribe el resumen con sus palabras. El código se explica archivo a archivo.
5. Control de comprensión: 3 preguntas.
6. Commit.

Una fase no está cerrada hasta que se pueda explicar en 2 minutos sin mirar.

## Estructura del repositorio

Confirmada en la fase de diseño ([04](04-solution-design.md) y ADR 0001–0004).

```
├── README.md
├── AI_USAGE.md
├── .env.example
├── docs/            documentos numerados y decisions/ (ADR)
├── data/synthetic/  exportaciones y Excels de la Parte A, histórico, correos .eml y casos etiquetados
├── supabase/        esquemas erp e intake, funciones SQL de las reglas y datos de arranque (Supabase local)
├── extraction/      prompts, esquema JSON y ejemplos; se cargan en una tabla de versiones
├── n8n/             flujos exportados y docker-compose de n8n
├── src/             migración (Parte A), carga de versiones de prompt y flujo de Python del plan B
├── eval/            script de evaluación, resultados guardados y respuestas de la IA
└── tests/           pytest: reglas por función y de punta a punta
```

**Reproducible con tus propias claves:** Supabase local (CLI + Docker), `.env.example` y la clave de IA de cada uno. Las respuestas de la IA para el conjunto de prueba se guardan en el repositorio, así que la evaluación se reproduce sin clave ni coste (D34).

## Decisiones abiertas

- Idioma público (README y página del caso): fase 7.

Cerradas en la fase 2: stack, n8n autoalojado y modelo de IA (D27), reglas en SQL y fuente única del prompt (D33) y generador de correos (D24). Ver los ADR 0001–0005.

**Para la fase 4:** cuando el repositorio tenga remoto, una rama por incremento con su pull request, que describe qué se ha construido y cómo se ha probado, y se revisa antes del merge. Se decide al empezar la fase, no a mitad.
