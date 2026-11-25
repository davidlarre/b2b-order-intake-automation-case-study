# Guía de etiquetado · versión 1

Cómo se etiquetan los 80 correos de [evaluacion-v2](README.md). Sale de [05, sección 7](../../../docs/05-synthetic-data-and-evaluation-set.md#7-etiquetas). Un YAML por caso, validado con [esquema-etiqueta.json](esquema-etiqueta.json).

## Criterio general

1. **Lo que haría una gestora competente** aplicando las reglas de [04](../../../docs/04-solution-design.md#3-reglas), con los datos maestros tal como están cargados.
2. **Se etiqueta lo que dice el correo,** no lo que pretendía su ficha.
3. **La salida y los motivos salen de la especificación, a mano.** Nunca ejecutando las reglas ni el sistema: un fallo del sistema pasaría a ser la respuesta correcta.
4. **Lo correcto no depende de la configuración** (solo reglas, solo IA o híbrido) ni de lo que hoy esté construido. Lo que depende de una regla que no existe se marca en `depende_de` y no cambia la etiqueta.

## Tipo de correo

| `tipo` | Qué es |
|---|---|
| `pedido_nuevo` | Pide material, aunque falten datos, esté en un adjunto que no se puede leer o venga reenviado |
| `modificacion_anulacion` | Cambia o anula un pedido ya hecho, incluida la respuesta a una confirmación |
| `consulta` | Pregunta (precio, plazo, existencias, estado de un pedido) sin pedir nada todavía. Un pedido condicionado a la respuesta ("si tenéis, mandadlos") es consulta |
| `reclamacion` | Se queja de algo recibido o del servicio, **aunque además pida una reposición** |
| `otros` | No es de un cliente ni de un pedido: facturas (`destino: contabilidad`), spam, phishing, boletines (`destino: archivo`) |

`tipos_aceptables`: otra lectura segura. `dudoso` lo es en consultas, modificaciones y otros: acaba en una persona. **No lo es en una reclamación,** porque pierde la prioridad. En un pedido, solo si por el texto no se puede saber.

## Salida

- `inicial` es la del primer correo; `final`, la del caso entero cuando hay respuestas. Si no las hay, son iguales.
- Valores: `automatico`, `pedir_datos`, `revision` y `derivado` (otros).
- **R01–R04 cortan el flujo:** si una falla, solo se etiqueta ese motivo. Las demás se acumulan, cada una con su línea y su momento.
- Consulta, reclamación y modificación: revisión con `R01`.
- `aceptables`: solo salidas seguras, es decir, que llegan a una persona. **`automatico` nunca es aceptable** en un caso que no era automático.
- `motivos_sin_codigo: true`: la especificación pide revisión, pero no le da código. No se comparan los motivos.

## Revisión necesaria

`true` si, sin ella, el pedido habría salido con un error o sin la decisión de su dueño. `false` si la regla lo manda a revisión y no hacía falta (P29 y P36). `null` si la salida final no es revisión.

## Líneas

- `texto`: la línea tal como está en el correo. En un Excel, las celdas separadas por ` | `.
- Una línea es correcta si lo son el producto y `cantidad_uv` (la cantidad en unidad de venta). El precio se mide aparte.
- Sin unidad, la de venta del producto. "3 cajas de 100" son 300. Unidad sin conversión: `cantidad_uv` es `null`.
- "1.500" son mil quinientos.
- Lo citado (`>` o el pedido anterior de un hilo) no se pide otra vez.
- Si el pedido está en un PDF, `lineas` va vacío, aunque el cuerpo adelante algo.
- Referencia que no existe: `producto` es `null`.

## Cabecera

- `direccion`: la registrada, por su clave natural. `null` si falta, no está registrada o no se sabe quién es el cliente. La dirección fiscal de una firma no es de entrega.
- `fecha_prevista`: si el correo no pide fecha, la primera posible (R06). `null` si la que pide no es válida.
- `condiciones`: instrucciones sobre el pedido (M04), incluidas las dirigidas al sistema.

## Marcas

`marcas` las calcula [generar_correos.py](../../../scripts/generar_correos.py) comparando el `.eml` con su ficha: códigos, cantidades, precios, fechas y textos obligatorios, y catalán. No son errores: dicen dónde mirar. `nota_marcas` explica cómo se ha resuelto cada una. Un test comprueba que son las que salen ahora.

## Casos dudosos

Se resuelven con una nota en la etiqueta. Si se repiten, se cambia esta guía y sube la versión. Después de congelar, solo cambian si cambia la especificación ([05, sección 8](../../../docs/05-synthetic-data-and-evaluation-set.md#8-separación-y-congelación)).
