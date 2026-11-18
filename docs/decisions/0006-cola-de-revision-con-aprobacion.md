# 0006 · Cola de revisión con aprobación del dueño de cada decisión

Fecha: 2026-11-18 · Estado: aceptado · Resuelve: "Quién resuelve cada motivo de revisión" (abierto en [03](../03-discovery-workshop.md))

## Contexto

D18 fija quién **confirma** cada regla, pero no quién **resuelve** cada caso. En el taller salieron tres cosas que tiran en direcciones distintas:

- La responsable de ADV quiere revisar antes de que un error de precio llegue al cliente (sesión 2).
- Dirección comercial dice que la revisión de precios sigue siendo de los comerciales, y a los comerciales les preocupa perder el control (sesiones 4 y 7).
- El caso de negocio depende de que la revisión baje de unos 5 minutos por pedido.

## Decisión

**Una sola cola, en ADV, con un paso de aprobación para las decisiones que tienen otro dueño.**

| Motivo | Lo resuelve | Cómo |
|---|---|---|
| R11 · precio distinto | Comercial asignado al cliente | Aprobación por correo |
| R13 · importe > 3.000 € | Dirección comercial | Aprobación por correo |
| R04 · cliente bloqueado | Finanzas | Aviso, sin aprobación: el desbloqueo se hace en el ERP (condición de la sesión 5) y después ADV pulsa "Reevaluar" |
| R09 · descatalogado | ADV, con el cliente | ADV ofrece el sustituto aprobado; solo el cliente sabe si lo acepta |
| El resto | ADV | En la app de revisión |

**Aprobaciones**

- **Canal:** un correo con un formulario (aprobar o rechazar, y comentario opcional), mediante "send and wait" de n8n. Los comerciales están en la calle y no van a entrar en una app. El enlace caduca y solo sirve para ese pedido.
- **Plazo:** si el pedido todavía llega al corte, hasta las 12:30 (en la práctica, hasta las 12:45 por el ciclo del temporizador); si no, 4 h dentro del mismo día laborable.
- **Sin respuesta:** R11 se escala a dirección comercial y se avisa a ADV; R13 solo avisa a ADV. **Nunca se aprueba por silencio:** una aprobación por silencio es justo el error caro que se quiere evitar.
- **R11 y R13 a la vez:** se piden en paralelo y hacen falta las dos.
- **Rechazo:** nunca anula el pedido. Lo devuelve a ADV con el comentario, y ADV decide si pide datos al cliente con la tarifa correcta o lo descarta.
- **Una aprobación vale para lo que se aprobó:** si ADV cambia el precio o la cantidad de una línea aprobada por R11, se pide otra; en R13, vale mientras el total no supere el importe aprobado.
- **Trazabilidad:** cada aprobación o rechazo se escribe en el registro de eventos de Supabase, con quién y cuándo. No basta con que quede en la ejecución de n8n.

**Lo que ADV no puede forzar.** Al crear el pedido desde la revisión se vuelven a pasar todas las reglas. ADV puede forzar sus propios motivos con una razón, pero **R04, R09, R11 y R13 tienen otro dueño y bloquean hasta que se resuelven en su origen**. Lo comprueba la función de la base de datos, no solo la pantalla. Por eso la aprobación no se puede saltar.

**Métricas.** Se miden por separado:

- el **esfuerzo de ADV** (minutos de trabajo por pedido), que es la variable del caso de negocio;
- el **tiempo de ciclo** (espera hasta que el pedido entra en el ERP), que es lo que pone en riesgo el corte de las 13:00.

Una aprobación añade espera, no esfuerzo. Además, hoy la gestora persigue al comercial por teléfono cuando duda de un precio; con la aprobación por correo, ese esfuerzo desaparece.

## Alternativas descartadas

- **ADV lo resuelve todo, con el comercial en copia:** ADV decidiría precios sin tener autoridad para ello. Contradice la sesión 7 y empeora la resistencia de los comerciales.
- **Una cola por dueño:** un pedido con varios motivos se repartiría entre varias colas, y nadie sería responsable del pedido completo.
- **El comercial resuelve sus pedidos con motivo de precio:** se convierte en un cuello de botella, y ADV pierde la visibilidad.
- **Una app para los comerciales:** no la usarían.
- **Aprobación por silencio al cumplirse el plazo:** convierte la falta de respuesta en una decisión comercial.

## Consecuencias

- Cada decisión la toma quien tiene la autoridad, y ADV conserva un único responsable por pedido. Encaja con el mensaje de adopción del taller: la revisión de precios sigue siendo de los comerciales.
- Un pedido puede quedarse esperando al comercial. El plazo y el escalado protegen el corte, y el tiempo de ciclo se mide aparte.
- **Limitación declarada:** el formulario no comprueba quién lo abre; si el correo se reenvía, otra persona podría aprobar. Aceptado para la demo.
- Con el plan B ([ADR 0003](0003-n8n-orquestador-plan-b.md)) se pierde "send and wait", y ADV vuelve a perseguir al comercial.
