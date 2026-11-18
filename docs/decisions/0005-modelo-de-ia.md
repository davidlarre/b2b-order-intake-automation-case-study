# 0005 · Proveedor y modelo de IA

Fecha: 2026-11-18 · Estado: aceptado · Cierra: D27 (modelo de IA), D24 (generador)

## Contexto

IT exige que el proveedor de IA firme un contrato de tratamiento de datos y que ningún dato se use para entrenar modelos (sesión 6). El diseño necesita salida estructurada con esquema ([ADR 0002](0002-prompt-y-esquema-fuente-unica.md)). D27 dice que el coste no condiciona el diseño, pero sí entra en la proyección (SN09). D24 pide que los correos sintéticos los genere un modelo distinto del que extrae.

Esta recomendación la ha preparado Claude, que es un modelo de Anthropic. Por eso el proveedor se justifica con criterios objetivos y con fuente, y si Anthropic no cumpliera alguno y otro proveedor sí, la elección cambiaría.

## Decisión

**Proveedor: Anthropic, por la API directa.** Criterios comprobados el 18-11-2026:

| Criterio | Resultado | Fuente |
|---|---|---|
| No entrenar con los datos | "Anthropic may not train models on Customer Content from Services" | [Commercial Terms](https://www.anthropic.com/legal/commercial-terms), sección B |
| Contrato de tratamiento de datos | Incorporado a los términos por referencia | [Commercial Terms](https://www.anthropic.com/legal/commercial-terms), sección C |
| Transferencias internacionales | Cláusulas contractuales tipo de la UE (módulos 2 y 3), ley de Irlanda | [Data Processing Addendum](https://www.anthropic.com/legal/data-processing-addendum) |
| Salida estructurada con esquema | Sí (`output_config.format`) | Documentación de la API |
| Nodo en n8n | Sí, nodo de Anthropic | — |
| Procesamiento en la UE | **No**: `inference_geo` solo admite `global` o `us`, y el almacenamiento es en EE. UU. | [Data residency](https://platform.claude.com/docs/en/manage-claude/data-residency) |

IT no pidió procesar en la UE, y el RGPD no lo exige si la transferencia tiene garantías. **Si IT lo exigiera**, se usaría Claude a través de Amazon Bedrock o de Vertex AI en una región europea. Antes habría que verificar que los modelos elegidos están en esa región y admiten salida estructurada. Previsiblemente solo cambian el nodo y las credenciales de n8n; el prompt, el esquema, las reglas y la evaluación no dependen del proveedor.

**Modelo para cada prompt**

| Prompt | Modelo | Criterio |
|---|---|---|
| Clasificación | Haiku 5.5 | Un error es barato: si duda, el correo va a revisión |
| Extracción y respuesta del cliente | Sonnet 5.5 por defecto | Solo pasaría a Haiku si en el conjunto de desarrollo fuera **claramente igual en todas las métricas**, no solo en la crítica: con 20 correos, "cero errores" en los dos no distingue cuál es más fiable |
| — | Opus 5.5 | Solo si fallan los otros dos |

El modelo se elige solo con el conjunto de desarrollo; la prueba se ejecuta con el modelo ya elegido (D23).

Precios por millón de tokens, de entrada y de salida ([Pricing](https://platform.claude.com/docs/en/about-claude/pricing)):

| Modelo | Entrada | Salida |
|---|---|---|
| Haiku 5.5 (prompts de hasta 100.000 tokens) | 0,10 $ | 0,50 $ |
| Sonnet 5.5 | 2 $ | 10 $ |
| Opus 5.5 | 4 $ | 20 $ |

Con Sonnet para todo y sin caché, el caso peor ronda los 50–70 $/mes para ~2.250 correos. La diferencia con Haiku es irrelevante frente al coste de un solo pedido mal servido.

**Datos que se envían al modelo:** solo el cuerpo del correo y el contenido del adjunto pasado a texto; en un reenvío, solo el mensaje original. No se envían el remitente, las cabeceras de autenticación, las direcciones en copia ni el resto del hilo.

**Generador de correos sintéticos: otro proveedor** (por ejemplo, OpenAI o Google). Dos modelos de la misma familia comparten más sesgos. No hay datos reales, así que no hace falta contrato de tratamiento de datos, y los correos generados se guardan en el repositorio: nadie necesita esa segunda clave para reproducir nada.

## Alternativas descartadas

- **OpenAI o Google para la extracción:** capacidad comparable y salida estructurada, pero ninguna ventaja decisiva para este caso. Serían la opción si cumplieran un criterio que Anthropic no cumple, como el procesamiento en la UE si IT lo exigiera.
- **Un modelo abierto en local (Ollama):** ningún dato sale de la empresa, pero extrae peor de Excels desordenados e hilos reenviados, depende del hardware de cada uno y complica D34.
- **Usar siempre el modelo más potente:** "más potente" no es automáticamente "más fiable" para extraer datos; eso se mide. Y la métrica crítica la protegen sobre todo las reglas, no solo el modelo.

## Consecuencias

- Se cumplen los requisitos de IT, con fuente. La falta de región europea queda escrita, con su salida.
- El modelo es un parámetro por prompt, no una decisión fija.
- SN09 se contrasta en la [sección 10 de 04](../04-solution-design.md#10-contraste-de-sn08-y-sn09).
- Los precios y los términos pueden cambiar: se vuelven a comprobar antes de comprometer cifras en el portfolio.
