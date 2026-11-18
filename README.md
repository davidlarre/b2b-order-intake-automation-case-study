# B2B Order Intake Automation: Case Study

Caso de estudio educativo y de portfolio sobre cómo se aborda un problema de automatización de punta a punta: discovery, diseño, construcción, evaluación, adopción y documentación.

**Caso ficticio.** Orvalle Suministros Industriales, sus clientes, sistemas, datos y cifras son inventados y sintéticos. No es un cliente real ni un proyecto profesional ya realizado. Las cifras del escenario son supuestos, no mediciones.

**Hecho con IA, y se dice.** El proyecto se desarrolla con asistencia de IA, con el objetivo de entender cada decisión y poder explicarla. Detalle en `AI_USAGE.md` (pendiente).

## El caso

Orvalle, un distribuidor de suministros industriales, recibe unos 1.800 pedidos al mes por email, en texto libre, Excel o PDF. Cada correo debe acabar como pedido validado en el ERP con confirmación al cliente, como petición concreta de datos al cliente o como excepción para una persona.

- **Parte A, datos maestros:** migración de tarifas pactadas, equivalencias de referencias, contactos y direcciones que viven fuera del ERP, con validación e informe de errores.
- **Parte B, flujo de pedidos:** extracción con IA, reglas contra los datos maestros y revisión humana de lo que no está claro.

La calidad se mide sobre un conjunto de correos etiquetados, comparando solo reglas, solo IA e híbrido.

## Reproducible con tus propias claves

Cuando haya código, el repositorio se podrá ejecutar en local con Supabase local, un `.env.example` y tu propia clave de IA. Las respuestas de la IA para el conjunto de prueba se guardan en el repositorio, así que la evaluación se puede reproducir sin clave ni coste.

## Estado

Fase 1 completada: discovery y caso de negocio revisado. Siguiente: diseño. Plan completo en [docs/00-project-plan.md](docs/00-project-plan.md).

## Documentación

| Documento | Estado |
|---|---|
| [00 Plan del proyecto](docs/00-project-plan.md) | Hecho |
| [01 Decisiones del reencuadre](docs/01-reframe-decisions.md) | Hecho |
| [02 Caso de negocio](docs/02-business-case.md) | Hecho; revisado tras discovery |
| [03 Taller de discovery](docs/03-discovery-workshop.md) | Hecho |
| 04 Diseño de la solución | Pendiente |
| 05 Informe de evaluación | Pendiente |
