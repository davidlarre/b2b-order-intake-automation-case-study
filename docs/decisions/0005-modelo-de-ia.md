# 0005 · Proveedor y modelo de IA

Fecha: 2026-11-18 · Revisado: 2026-11-19 · Estado: aceptado · Cierra: D27 (modelo de IA), D24 (generador)

## Contexto

IT exige que el proveedor de IA firme un contrato de tratamiento de datos y que ningún dato se use para entrenar modelos (sesión 6). El diseño necesita salida estructurada con esquema ([ADR 0002](0002-prompt-y-esquema-fuente-unica.md)). D27 dice que el coste no condiciona el diseño, pero sí entra en la proyección (SN09). D24 pide que los correos sintéticos los genere un modelo distinto del que extrae.

**Revisión del 19-11-2026: requisito nuevo, todo el proyecto tiene que ser gratuito.** La versión anterior elegía la API de Anthropic, que es de pago. Se separan dos preguntas que antes iban juntas: con qué corre la demo y con qué correría Orvalle. Los criterios de IT y la minimización de datos no cambian.

## Decisión

### Demo: Gemini por Google AI Studio, nivel gratuito

Comprobado el 19-11-2026:

| Criterio | Resultado | Fuente |
|---|---|---|
| Disponible en España | Sí | [Available regions](https://aistudio.google.com/docs/available-regions) |
| Uso de los datos | En el nivel gratuito, Google usa el contenido para mejorar sus productos y puede haber revisión humana. **Pero en el EEE, Suiza y el Reino Unido se aplican las condiciones de uso de datos de pago también al uso gratuito**, así que desde España no se usa para entrenar | [Gemini API Additional Terms](https://aistudio.google.com/docs/terms), en vigor desde el 23-03-2026 |
| Uso con usuarios del EEE | "You may use only Paid Services when making API Clients available to users in the European Economic Area". La demo no se pone a disposición de usuarios: solo la usa el autor, con datos sintéticos | Ídem |
| Salida estructurada con esquema | Sí, con un subconjunto de JSON Schema (`properties`, `required`, `enum`, `items`, `minItems`/`maxItems`…). `minLength`, `maxLength` o `uniqueItems` no se aplican y se quitan sin error; un esquema demasiado complejo da `400`. La segunda capa con `pg_jsonschema` ([ADR 0001](0001-reglas-en-sql.md)) cubre lo que no se aplica | [Structured output](https://aistudio.google.com/docs/structured-output) |
| Modelos con nivel gratuito | Sí: `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, entre otros. Los modelos 2.5 están obsoletos y se redirigen el 01-12-2026 | [Pricing](https://aistudio.google.com/docs/pricing) |
| Límites del nivel gratuito | **Google no los publica por modelo en su documentación**: remite a la página de cuota de AI Studio y dice que "no están garantizados". Los RPD se reinician a medianoche, hora del Pacífico. Fuentes secundarias, no oficiales, dan ~20 peticiones al día para `gemini-3.8-flash` y ~500 para los Flash-Lite, con 5–10 por minuto | [Rate limits](https://aistudio.google.com/docs/rate-limits); [ScriptByAI](https://www.scriptbyai.com/gemini-api-free-tier-limits/) |

**Los datos que se envían siguen siendo sintéticos**, y la minimización de la [sección 6.2 de 04](../04-solution-design.md#62-qué-se-envía-al-modelo) no cambia.

**Modelo para cada prompt**

| Prompt | Modelo | Criterio |
|---|---|---|
| Clasificación | `gemini-3.1-flash-lite` | Un error es barato: si duda, el correo va a revisión |
| Extracción y respuesta del cliente | `gemini-3.5-flash-lite` | El límite diario de `gemini-3.8-flash` (~20 al día) no da para la evaluación: una evaluación completa necesita unas 300 extracciones |

**Cambio del 25-11-2026:** la clasificación usa `gemini-3.5-flash-lite`, porque el 3.1 respondía 503 de forma continuada al construirla ([desarrollo v2](../../eval/desarrollo-v2.md)). Los dos prompts comparten ahora las 500 peticiones diarias que Gemini declara en el 429. Volver al 3.1 es cambiar `extraction/clasificacion/config.json`.

Cada prompt usa un modelo distinto también por la cuota: los límites van por modelo, así que repartir la clasificación y la extracción en dos modelos permite que la evaluación quepa en un día (sección 7 de 04).

**Esto invierte el criterio de la versión anterior**, que usaba el modelo más capaz por defecto y solo bajaba si el pequeño era igual. Ahora el modelo lo condiciona la cuota gratuita, no la calidad, y se declara. `gemini-3.8-flash` se compara en el conjunto de desarrollo (unas 20 extracciones, que caben en su cuota). Si es claramente mejor, se decide entonces si la evaluación se reparte en varias semanas o se reducen las repeticiones, y se declara. El modelo se elige solo con el conjunto de desarrollo; la prueba se ejecuta con el modelo ya elegido (D23).

**No se crean varios proyectos para multiplicar la cuota.** Sería saltarse los límites del proveedor.

### Orvalle: un proveedor de pago que cumpla los criterios de IT

- **Opción recomendada: Gemini de pago en Google Cloud (Vertex AI) con el endpoint multirregión `eu`.** El procesamiento se queda en estados miembros de la UE, y los modelos de la demo (`gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`) lo admiten ([Data residency](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency)). **Resuelve la limitación de la versión anterior**: con Anthropic por la API directa no se podía procesar en la UE. Los endpoints globales no garantizan la región y no se usan. En el servicio de pago, Google no usa los prompts ni las respuestas para mejorar sus productos ([Terms](https://aistudio.google.com/docs/terms)). Queda por verificar el contrato de tratamiento de datos de Google Cloud y sus garantías de transferencia ([sección 14 de 04](../04-solution-design.md#14-verificaciones-con-fuente)).
- **Alternativa: otro proveedor que cumpla los criterios.** Anthropic los cumplía todos menos la región UE (comprobado el 18-11-2026: no entrena con los datos, contrato de tratamiento incorporado a los términos, cláusulas contractuales tipo, salida estructurada).
- En los dos casos cambian el nodo y las credenciales de n8n. El prompt, el esquema, las reglas y la evaluación no dependen del proveedor, y **la elección se valida con la misma evaluación** antes de pasar a producción: la demo mide Gemini Flash-Lite, no el modelo de producción.

### Generador de datos sintéticos: Claude, con Claude Code

Claude Code, con la suscripción del autor, genera los correos y las listas sintéticas. **Es otra familia de modelos que la extracción** (Gemini), que es lo que pide D24. No hay datos reales y lo generado se guarda en el repositorio: nadie necesita repetir la generación para reproducir nada. Claude hace también la segunda lectura de etiquetas, en una sesión que nunca ve la ficha del correo ([05](../05-synthetic-data-and-evaluation-set.md)). **Gemini no etiqueta**, por el mismo motivo por el que no genera.

## Alternativas descartadas

- **API de Anthropic en la demo:** cumple los criterios, pero es de pago. Queda como alternativa para Orvalle.
- **OpenAI en la demo:** la API también es de pago, aparte de la suscripción de ChatGPT.
- **Un modelo abierto en local (Ollama):** gratis y ningún dato sale del Mac, pero extrae peor de Excels desordenados e hilos reenviados, depende del hardware de cada uno y complica D34.
- **`gemini-3.8-flash` para la extracción en la demo:** con ~20 peticiones al día, una evaluación completa llevaría unas dos semanas.

## Consecuencias

- La demo cuesta cero, y cualquiera la reproduce con una clave gratuita de AI Studio.
- **Limitaciones declaradas:**
  - el modelo de la demo lo elige la cuota, no la calidad;
  - los límites no están garantizados y pueden cambiar sin aviso; el manifiesto de cada ejecución guarda el modelo exacto y la fecha;
  - las métricas de la demo valen para Flash-Lite; en producción, con otro modelo, se repite la evaluación.
- Para Orvalle, Vertex AI con el endpoint `eu` resuelve el procesamiento en la UE.
- SN09 se recalcula con los precios de Gemini de pago en la [sección 10 de 04](../04-solution-design.md#10-contraste-de-sn08-y-sn09).
- Los precios, los límites y los términos pueden cambiar: se vuelven a comprobar antes de comprometer cifras en el portfolio.
