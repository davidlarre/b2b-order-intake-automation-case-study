# Guion del vídeo (3 minutos)

Para quien llega desde LinkedIn, sin conocimientos técnicos. Se graba en una sola toma, o en tramos que se montan después. El texto es una base: dilo con tus palabras.

## Antes de grabar

1. **Reinicia la demo el mismo día, por la mañana.** `scripts/preparar_demo.sh` **borra la base local** (pide escribir `si`), procesa los 7 correos en híbrido y les pone la fecha de hoy. Tarda un par de minutos: no se graba entero.
   - Tiene que acabar en 2 pedidos automáticos (01 y 04) y 5 en revisión (02, 03, 05, 06 y 07). Si cambia algo, no grabes todavía: la IA puede variar.
   - Deja esa terminal abierta, con el resultado a la vista y la letra grande.
2. **App:** `cd app && npx pnpm@12.4.2 dev`. Entra con `gestora@orvalle.example` **antes** de grabar, para no teclear la contraseña en pantalla.
3. **n8n:** abre el flujo en http://localhost:5678, encuadrado entero.
4. **Pestañas, en este orden:** README en GitHub · app (cola) · n8n · `eval/resultados-v1.md` · terminal.
5. **Que no se vea:** `.env`, las credenciales de n8n, tu email, notificaciones ni marcadores. Pantalla completa y zoom al 125 %.

## El guion

| Tiempo | En pantalla | Qué se dice |
|---|---|---|
| **0:00–0:20** · El problema | README, arriba | "Un distribuidor recibe 1.800 pedidos al mes por correo: texto, Excel, PDF. Alguien lee cada uno y lo teclea. Es un caso ficticio, hecho con ayuda de IA, pero el problema existe en muchas empresas." |
| **0:20–0:45** · El reparto | README, diagrama de arquitectura | "La idea es repartir el trabajo. La IA lee el correo. Las reglas deciden, con los datos de la empresa. Y lo dudoso lo resuelve una persona. La IA nunca acepta un precio ni decide quién es el cliente." |
| **0:45–1:10** · En marcha | Terminal: el resultado de `scripts/preparar_demo.sh`, señalando `automatico` y `revision` | "Acabo de pasar siete correos de prueba. Dos han salido solos: pedido creado. Los otros cinco no, y eso es lo interesante: el sistema sabe cuándo no sabe." |
| **1:10–1:55** · La cola y un caso dudoso | App: la cola; abre el **pedido 6** (*Pedido obra*); **Ver correo**; vuelve al recuadro | "Cada pedido dice por qué está aquí. Este es mi favorito: el cliente escribe '1000 unidades, perdón, son 1200'. Dos lecturas, una de la IA y otra de reglas. No coinciden, así que no se crea nada. La persona mira el correo y elige." Pulsa **Son 1200: crear el pedido** y enseña la confirmación. |
| **1:55–2:15** · El precio y el remitente | App: abre el **pedido 3** (*Comanda guants*); vuelve; pasa por el **pedido 2** (*Sin confirmar*) | "Aquí el cliente pide a 6,50 y su tarifa es 6,20: lo tiene que aprobar su comercial, y la app no deja saltárselo. Y aquí alguien que no conocemos. Puede ser el cliente, o puede ser un fraude." No pulses nada. |
| **2:15–2:30** · Por dentro | n8n: el flujo entero, de izquierda a derecha | "Por dentro es un flujo de n8n con reglas en la base de datos. La evaluación pasa por este mismo flujo: se mide lo que funciona." |
| **2:30–2:50** · Resultados y límites | `eval/resultados-v1.md`: tabla resumen | "Con 20 correos, el híbrido no creó ningún pedido equivocado. Pero son 20 casos de desarrollo: con cero errores en nueve pedidos automáticos, el error real podría llegar a uno de cada tres. Y la IA sola salió algo mejor: la red de seguridad todavía tiene que demostrar que compensa." |
| **2:50–3:00** · Cierre | README, "Qué viene después" | "Lo siguiente es una prueba seria, con 80 correos y las reglas que faltan. Está todo en el repositorio, fallos incluidos. Gracias." |

## Notas

- **Números de pedido:** 2, 3, 6… valen con la base recién reiniciada. Guíate por el asunto si no coinciden.
- **Si repites la toma del pedido 6,** ya está creado y no sale en la cola: vuelve a ejecutar `scripts/preparar_demo.sh`.
- **No digas** que el sistema está en producción, que ahorra un porcentaje ni que "no falla".
- **Si te pasas de tiempo,** quita el tramo de n8n (2:15–2:30). Los límites no se quitan.
