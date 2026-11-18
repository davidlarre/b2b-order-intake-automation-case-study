# 05 · Datos sintéticos y conjunto de evaluación

Fase 3 del [plan](00-project-plan.md). Resume lo decidido sobre los datos de la Parte A y el conjunto de evaluación. El detalle (catálogo completo, fichas de los correos, etiquetas) vive en el código y en los datos cuando se generen. **Todos los datos son sintéticos.**

**Orden de trabajo.** La fase 4 empieza con un corte vertical mínimo y datos pequeños y limpios. El catálogo completo de errores y el conjunto de evaluación se generan cuando el flujo funcione. Consecuencia declarada: la prueba se congela después de construir el corte vertical, no antes de empezar a construir; el registro de cambios (sección 8) es lo que protege su integridad.

## 1. Método y oráculo

- Un script de Python con semilla fija y un plan de errores explícito genera los ficheros de la Parte A y el informe esperado (oráculo).
- Las listas de partida (descripciones, nombres de empresa, notas en celdas de precio, texto de las chuletas) las genera Claude una vez; se revisan y se guardan fijas en el repositorio.
- Un lote ensuciado a ciegas, etiquetado a mano, se congela con la prueba y se ejecuta una sola vez.
- Uno de los 5 Excels de comerciales lo hace David a mano, con formato con significado (tachados, rojo = "ya no vale"). Se etiqueta a mano.

## 2. Catálogo de errores (D10, D11)

- Tres tipos de fila: **errores**, **anclas** de la Parte B (email compartido, descatalogado con y sin sustituto, nave distinta, varias direcciones) y **controles**: filas raras pero válidas que miden los falsos positivos.
- 39 tipos (E01–E39) por fuente, con un mínimo de 3 de cada uno. Densidad realista: ~2 % en las exportaciones del ERP y 10–15 % en Excels y chuletas.
- Coincidencia por nombre: solo la exacta tras normalizar se carga sola; la aproximada va a revisión con sugerencia.
- Una equivalencia que apunta a un descatalogado se carga con aviso: de eso se ocupa R09.
- Vigencia ausente: se carga hasta la fecha de la migración + 90 días, con aviso y una lista por comercial.
- **Tarifa con nota en la celda del precio: se carga como `pendiente`, y R11 no la usa hasta que se resuelve.** Corrige D11.
- Una fila cuyo padre no se carga va al informe con "padre no cargado".
- Un fichero fijo de decisiones de revisión hace de ADV, y es el estado de arranque de la Parte B. Algunas revisiones se dejan abiertas a propósito.

## 3. Fuentes de la Parte A

- ERP: CSV con `;`, latin-1 y coma decimal, cabeceras crípticas y un fichero de mapeo por fuente. El domicilio va en una sola cadena.
- CRM: CSV con `,` y UTF-8 con BOM; la empresa en texto libre, sin código ni CIF.
- Excel de direcciones de ADV, con título y fila en blanco antes de la cabecera.
- 4 Excels de comerciales generados (tabla plana, una pestaña por cliente, matriz, varias tablas en una hoja) y el de David.
- 3 chuletas en Word: dos estructuradas y una en prosa. Lo que no se interpreta va al informe como "línea no interpretada" y se transcribe a mano. Sigue sin IA (D12).
- Claves naturales para repetir la carga sin duplicar: producto, cliente, dirección (cliente + código postal + calle + número + nave), contacto (cliente + email), tarifa (cliente + producto + desde) y equivalencia (cliente + referencia del cliente).

## 4. Histórico

- Del 01-05-2026 al 30-10-2026. **La fecha de la migración (T = 30-10-2026) es un parámetro fijo**, no la del día de la ejecución.
- ~1.400 pedidos y ~5.800 líneas, generados con un modelo de comportamiento: segmentos de frecuencia, cesta habitual por cliente, calendario (lunes y días después de festivos al doble, agosto a la baja) y ~3 % de ruido natural.
- Precios reales del oráculo, incluidos los pactados por teléfono. Da la consulta SQL "líneas facturadas a un precio que no está en ninguna tarifa cargada".
- Anclas para R14, R07 (incluido un cliente con numeración cíclica), "repite el pedido X", "la de siempre", modificaciones, descatalogados y bloqueados.

## 5. Conjunto de evaluación (D23)

- 60 de prueba y 20 de desarrollo, con la mezcla de D23. Correos de prueba entre el 02-11 y el 20-11-2026, más 2–3 en enero de 2027 para la tarifa que caduca a los 90 días.
- Se combinan trampas en el mismo correo cuando es natural, nunca con motivos que cortan el flujo. Las de menos prioridad pasan a desarrollo.
- Atributos de cabecera superpuestos: `dmarc=none` en un tercio, remitente con gmail y "URGENTE".
- Cuatro tipos de trampa solo en la prueba: dominio parecido, numeración cíclica, instrucciones en el cuerpo y reclamación con pedido.
- Una respuesta del cliente es un caso con varios `.eml`. Una respuesta automática de fuera de oficina va en el hilo de una petición pendiente y se espera que se ignore. En total, 66 `.eml`.

## 6. Generación de los correos

- Claude escribe solo lo que escribiría una persona: cuerpo, firma y celdas. El script monta cabeceras, MIME, adjuntos, hilos, reenvíos y fechas.
- Una ficha por correo, de la que sale el borrador de la etiqueta. Un manifiesto guarda el modelo, la fecha, el prompt y las respuestas en bruto.
- Dominios de empresa en `.example` y dominios públicos reales con usuarios inventados. La demo en directo usa alias de David.
- Trampas de forma: firma con la dirección fiscal, hilo citado, correos solo en HTML, tres estilos de reenvío, plantillas de Excel de cliente y catalán.
- David escribe ~15: 12 con ficha (incluidos los de catalán y mezcla de idiomas) y 3 libres.
- Si un correo no cumple su ficha, se regenera hasta 2 veces; si no, se edita a mano y se marca como `editado_a_mano`.

## 7. Etiquetas

- Un YAML por caso, validado con un esquema: tipo, salida inicial y final, salidas aceptables, `revision_necesaria`, motivos por línea, petición de datos con sus opciones, cabecera y líneas.
- La salida y los motivos esperados se sacan a mano de la especificación de 04, nunca ejecutando las reglas. Después se comparan con las reglas SQL, y cada diferencia se investiga.
- Etiqueta David. Claude hace una segunda lectura de ~15 casos de la prueba sin ver la ficha. **Gemini no etiqueta**, porque es quien extrae.
- Una línea es correcta si el producto y la cantidad en unidad de venta son correctos. El precio se mide aparte.
- Las etiquetas de la Parte A usan el formato del informe de la migración, más el código `OTRO`.
- Esfuerzo estimado: **8–10 h en varias sesiones**.

## 8. Separación y congelación

- **Ajustar** es cambiar el comportamiento o la especificación: el prompt y sus ejemplos, el preprocesado del Excel, las expresiones regulares, el mapeo de cabeceras, los parámetros y los datos maestros. Solo puede salir de desarrollo, y cada cambio cita el caso que lo motivó.
- **Construir** es corregir el código para que cumpla la especificación. Criterio: si el test se puede escribir con la especificación en la mano, es construir; si solo se puede escribir mirando un correo, es ajustar. Después de ejecutar la prueba, todo cambio es "prueba tras corrección".
- Los casos de desarrollo añadidos después de congelar la prueba llevan fecha y motivo, se cuentan en el informe y no pueden reproducir los cuatro tipos reservados a la prueba.
- Se congela con un manifiesto SHA-256 y un tag de git (`prueba-v1`). El script de evaluación comprueba el hash.
- Etiquetas: antes de ejecutar la prueba, solo cambian si cambia la especificación. Después, las correcciones van a una fe de erratas, y las métricas se publican con las dos versiones de las etiquetas y la dirección de cada corrección.
- "Una sola vez" son las 7 pasadas. Una pasada solo se repite por un fallo de infraestructura, y se declara.

## 9. Resultados guardados (D34)

- Por ejecución: un manifiesto, resultados por caso en JSONL por pasada, y las respuestas del modelo en bruto.
- La clave del modo reproducción es el hash de la entrada exacta + prompt + modelo + repetición. Si cambia el preprocesado, la reproducción falla en voz alta en lugar de devolver una respuesta antigua.
- Se guardan todas las pasadas de la prueba, incluidas las fallidas, y las ejecuciones de desarrollo con las que se eligió el modelo.
- Guardar las respuestas en bruto en un repositorio público solo es aceptable porque los datos son sintéticos. En producción contendrían texto de correos reales y tendrían el plazo de conservación de la [sección 8 de 04](04-solution-design.md#8-gobierno-y-protección-de-datos).

## 10. Limitaciones

- Los correos los escribe una IA, salvo ~15. Un solo etiquetador, con segunda lectura de una muestra.
- El autor ha visto la prueba, y la prueba se congela después del corte vertical.
- 20 casos de desarrollo son pocos para ajustar.
- La migración no lee el formato con significado (colores, tachados).
- La evaluación usa Gemini Flash-Lite por la cuota gratuita ([ADR 0005](decisions/0005-modelo-de-ia.md)).
