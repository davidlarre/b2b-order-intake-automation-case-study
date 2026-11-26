# El caso en una página

**Caso ficticio.** Orvalle Suministros Industriales, sus clientes y sus cifras son inventados. Es un proyecto de portfolio hecho con asistencia de IA ([cómo](../AI_USAGE.md)).

## El problema

Orvalle vende tornillería, guantes y herramienta a talleres y pequeñas fábricas. Recibe unos **1.800 pedidos al mes por correo**, cada uno a su manera: "ponme lo de siempre", un Excel propio, un PDF, medio en catalán.

Cuatro personas leen cada correo, adivinan qué producto es, comprueban el precio que se pactó y lo teclean. Son unos **6 minutos por pedido: 180 horas al mes, el 32 % de las 560 horas efectivas del equipo**. La empresa quiere crecer un 20 % sin contratar, y así no llega. *(Son cifras del escenario, no mediciones.)*

Teclear es lo lento, pero lo caro es **equivocarse**: mandar 1.000 tuercas cuando eran 1.200.

## La decisión clave

La tentación es dárselo todo a una IA. Aquí se reparte el trabajo en tres:

- **La IA lee.** Entiende un correo desordenado y saca de él una lista: qué, cuánto y a qué precio.
- **Las reglas deciden.** Comprueban lo que se puede comprobar: ¿conocemos a quien escribe?, ¿existe ese producto?, ¿es el precio pactado? La IA no acepta precios ni decide quién es el cliente. Tampoco cuenta lo segura que diga estar.
- **Una persona resuelve lo dudoso.** Lo ve en una pantalla, con el motivo en una frase y los botones que tocan.

Además, un segundo lector, más simple y sin IA, lee lo que puede. **Si los dos no coinciden, no se crea el pedido.** Por ejemplo, con "1000 uds (perdón, son 1200)", uno lee 1000 y el otro 1200, y la persona elige.

![Un pedido dudoso en la pantalla de revisión](img/app-discrepancia.png)

## Los resultados

Se probó con **60 correos guardados aparte**, que no se usaron para ajustar el sistema y se pasaron una sola vez (v2). Los escribió una IA que conocía el sistema, así que no es un examen a ciegas. De ellos, 38 son casos que el sistema ya sabe resolver; los otros 22 necesitan reglas que todavía no existen, y se cuentan aparte.

| En los 38 casos | Pedidos creados solos | De ellos, mal |
|---|---|---|
| **Las dos juntas (IA y reglas)** | 10 | **1** |
| Solo reglas | 6 | 1 |
| Solo IA | Pendiente: se pasa otro día | |

- **El que salió mal** fue una pregunta con condición: "¿Tenéis 100 hojas de lija y 3 adhesivos? Si es que sí, mandadlos". El sistema lo tomó por un pedido y lo creó sin comprobar nada. Es justo el tipo de correo que más cuesta distinguir.
- **Distinguir qué es cada correo** (pedido, cambio, consulta, queja, factura) salió bien en 59 de 60.
- **Las reglas que faltan se notan mucho:** con los 22 correos que las necesitan, el sistema crea hoy 12 pedidos que no debería, por ejemplo a un cliente bloqueado o confundiendo cajas con unidades.
- **Si la IA no responde,** el pedido llega a una persona con el motivo. En esta prueba no pasó.

El detalle está en el [informe de evaluación](06-evaluation-report.md). Las versiones anteriores, con 20 correos de desarrollo, en los [resultados v1.1](../eval/resultados-v1-1.md) y [v1](../eval/resultados-v1.md). **El vídeo muestra la v1:** no se ha regrabado.

## Los límites

- **Son pocos casos:** con 1 error en 10 pedidos creados solos, el error real podría llegar a 4 de cada 10. Para confiar harían falta cientos, en un piloto con el equipo y correos de verdad.
- **Los correos y las respuestas correctas los escribió una IA,** y los revisó otra IA. Todavía no los ha revisado una persona. El catálogo de productos también es generado.
- **Faltan piezas:** detectar duplicados y clientes bloqueados, comprobar cajas y unidades, saber a qué dirección enviar, enlazar la respuesta del cliente con su pedido, leer PDF y enviar respuestas.
- **El ahorro no está demostrado.** Depende de cuánto se tarde en revisar cada pedido dudoso, y eso solo lo dice un piloto ([caso de negocio](02-business-case.md)).

**Lo que sí demuestra:** un sistema que sabe cuándo no sabe, y que dice con números hasta dónde llega.
