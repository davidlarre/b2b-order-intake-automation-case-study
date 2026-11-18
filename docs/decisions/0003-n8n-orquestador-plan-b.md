# 0003 · n8n como orquestador, con plan B

Fecha: 2026-11-18 · Estado: aceptado · Confirma: D27 (orquestador), D30 (plan B)

## Contexto

El flujo necesita conectores con Gmail, reintentos, programación y espera de aprobaciones. Además, al entregarlo, alguien de Orvalle tiene que poder mantenerlo. El proyecto pide low-code conectado a las herramientas del cliente. El incremento de n8n es el más arriesgado del proyecto por la curva de aprendizaje, y D30 ya previó un plan B en Python.

## Decisión

**n8n como orquestador**, con cinco subflujos:

| Subflujo | Qué hace |
|---|---|
| Entrada Gmail | Lee pedidos@, guarda el original y crea el caso |
| Entrada de pruebas | Webhook que recibe un `.eml` para la evaluación ([ADR 0002](0002-prompt-y-esquema-fuente-unica.md)) |
| Procesar | Preprocesado, extractor determinista, llamadas a la IA y `evaluar_caso` |
| Actuar | Recoge los envíos pendientes cada minuto y envía los correos; arranca las aprobaciones con "send and wait" |
| Temporizador | Cada 15 min: plazos de 24 h, escalados y reintento en caída general |

**Qué vive dónde:**

- **En n8n:** la orquestación, el preprocesado, el extractor determinista y las llamadas a la IA.
- **En SQL:** las reglas y las escrituras en el ERP ([ADR 0001](0001-reglas-en-sql.md)).
- **En la tabla de versiones:** el prompt y el esquema ([ADR 0002](0002-prompt-y-esquema-fuente-unica.md)).

**Versionado.** Los flujos se exportan en JSON a `n8n/` al cerrar cada incremento. Las credenciales no van en el JSON: se configuran en cada instancia, y `.env.example` dice cuáles hacen falta.

**Plan B**

- **Cuándo se activa:** al acabar la segunda sesión del incremento de n8n, si no se cumple esto:
  - la lectura del `.eml` está resuelta, con `mailparser` o con su alternativa;
  - 5 correos de desarrollo (texto y Excel) pasan de la entrada de pruebas a "Procesar" y quedan con la extracción guardada, su versión y la salida de `evaluar_caso`.
  
  Un fallo parcial no activa el plan B: si solo falla el `.eml`, se usa la alternativa ya decidida. El plan B no se activa por comodidad (D30).
- **Qué cubre:** "Procesar" se reescribe en Python, con el mismo prompt (leído de la tabla) y las mismas reglas SQL. El preprocesado y el extractor determinista también se reescriben; no se rompe D33, porque con el plan B Python es el sistema y n8n deja de existir.
- **Qué se pierde:** sin "send and wait", la aprobación se pide por correo y ADV la registra en la app cuando el comercial contesta. **No es solo una función técnica: se pierde parte de la mejora del proceso**, porque la gestora vuelve a perseguir al comercial, que es uno de los dolores del AS-IS. Por eso el plan B es el último recurso.

## Alternativas descartadas

- **Make o Zapier:** solo en la nube y con coste por operación. No se pueden autoalojar, lo que choca con la lectura del `.eml` y con D34.
- **Power Automate:** Orvalle trabaja con Google Workspace.
- **Solo Python:** da el máximo control, pero solo lo puede mantener un programador, y pierde el low-code y la parte visual de la demo.

## Consecuencias

- Alguien de IT o de operaciones puede ver el flujo, revisar cada ejecución y cambiar un paso sin ser desarrollador. Los conectores, los reintentos y la espera de aprobaciones vienen incluidos.
- Cada pieza queda donde la puede mantener quien la va a mantener: las reglas en SQL y la orquestación en n8n.
- El plan B tiene un criterio medible y un coste declarado.
