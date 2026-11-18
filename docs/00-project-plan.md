# 00 · Plan del proyecto

## Qué es

Caso de estudio educativo y de portfolio sobre la entrada automatizada de pedidos B2B por email, de punta a punta: discovery, diseño, construcción, evaluación, adopción y portfolio. La empresa (Orvalle Suministros Industriales), sus datos y sus cifras son ficticios y sintéticos.

Es un único caso integrado. La IA forma parte de la solución desde el diseño, combinada con reglas, revisión humana y evaluación:

- **Parte A, datos maestros:** migración de lo que vive fuera del ERP (direcciones, contactos, tarifas pactadas y equivalencias de referencias) con mapeo, validación, informe de errores y carga repetible. Sin IA.
- **Parte B, flujo de pedidos:** cada correo que llega a pedidos@ termina como pedido validado en el ERP con confirmación al cliente, como petición concreta de datos al cliente o como excepción para una persona.

Las decisiones de partida están en [decisions/0001-reframe.md](decisions/0001-reframe.md).

## Principios

1. **Honestidad.** Se distinguen siempre escenario, supuestos, medición y proyección.
2. **Hecho con IA, y se dice.** En `AI_USAGE.md`.
3. **Entenderlo todo.** El porqué de cada decisión y preguntas de comprensión. Ante una pregunta, razonar siempre en voz alta.
4. **IA donde aporta.** Las reglas son la línea base y el control; las decisiones de negocio nunca las toma solo la IA.
5. **Realismo.**
6. **Una cosa cada vez.**

## Fases

Sin calendario fijo: se planifica fase a fase.

| # | Fase | Sale | Modelo |
|---|---|---|---|
| 0 | Reencuadre | Decisiones (0001), plan y repositorio limpios | Opus (decisiones), Sonnet (redacción) |
| 1 | Discovery | AS-IS, mapa del proceso, oportunidades priorizadas, business case con supuestos | Opus (decisiones), Sonnet (redacción) |
| 2 | Diseño | TO-BE, reglas, datos mínimos, criterios de aceptación, stack (ADR). Los requisitos van integrados aquí | Opus |
| 3 | Datos y evaluación | Datos sintéticos y casos etiquetados, antes de construir | Opus (método), Sonnet (generación) |
| 4 | Construcción | Ver orden más abajo | Sonnet; Opus en diseño de módulos y depuración difícil |
| 5 | Evaluación | Comparación de configuraciones, cronómetro, coste por caso | Opus (método), Sonnet (ejecución) |
| 6 | Adopción y gobierno | Guía, formación, permisos, AI Act | Sonnet |
| 7 | Portfolio | README, página del caso, vídeo de 3 min | Sonnet |

**Orden de construcción:**

1. Supabase y la carga de datos maestros.
2. n8n: de Gmail a la extracción con IA en JSON.
3. Reglas y creación del pedido.
4. Respuestas automáticas y excepciones.
5. App de revisión.
6. Consultas SQL.
7. Evaluación.

Cada incremento se cierra con su check y un commit. La demo debe poder enseñarse en directo en 3 minutos.

**Recortes si falta tiempo, en este orden:** PDF → panel → modificaciones de pedido → correos con varios pedidos → app de revisión (se sustituye por la vista de Supabase). No se recorta la evaluación.

**Plan B del incremento de n8n:** si tras 2 sesiones no funciona, el flujo corre como script de Python con los mismos pasos, las mismas reglas y la misma extracción, y el motivo se documenta en un ADR. n8n es la pieza principal del portfolio.

## Método por fase

1. Se explican los conceptos y por qué importan.
2. David decide entre 2–4 opciones con una recomendación.
3. Se redacta el borrador o el código.
4. David revisa y reescribe el resumen con sus palabras. El código se explica archivo a archivo.
5. Control de comprensión: 3 preguntas.
6. Commit.

Una fase no está cerrada hasta que se pueda explicar en 2 minutos sin mirar.

## Estructura del repositorio

Provisional; la ubicación de reglas, prompt y esquema se confirma en la fase de diseño (D33).

```
├── README.md
├── AI_USAGE.md
├── .env.example
├── docs/            documentos numerados por fase y decisions/ (ADR)
├── data/synthetic/  exportaciones y Excels de la Parte A, correos .eml y casos etiquetados
├── supabase/        esquema, funciones SQL de las reglas y datos de arranque (Supabase local)
├── extraction/      prompt y esquema JSON, únicos para n8n y para el script
├── n8n/             flujos exportados
├── src/             migración (Parte A) y script local de procesado
├── eval/            evaluación, respuestas de la IA guardadas y resultados
└── tests/
```

**Reproducible con tus propias claves:** Supabase local (CLI + Docker), `.env.example` y la clave de IA de cada uno. Las respuestas de la IA para el conjunto de prueba se guardan en el repositorio, así que la evaluación se reproduce sin clave ni coste (D34).

## Decisiones abiertas

- Stack definitivo, n8n autoalojado o en la nube, y modelo de IA: fase 2 (D27).
- Reglas como funciones SQL y una sola fuente para el prompt y el esquema: se confirma en la fase 2 (D33).
- Modelo que genera los correos sintéticos, distinto del que extrae: con la elección del modelo (D24).
- Idioma público (README y página del caso): fase 7.
