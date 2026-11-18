# 0004 · n8n en local o en la nube

Fecha: 2026-11-18 · Estado: aceptado · Cierra: D27 (n8n autoalojado o en la nube)

## Contexto

Dos decisiones anteriores condicionan esta:

- La lectura del `.eml` puede necesitar una librería npm (`mailparser`). Según la [documentación de n8n](https://docs.n8n.io/code/code-node/), los módulos externos en el nodo Code solo se pueden usar en n8n autoalojado; en n8n Cloud no se pueden importar.
- Las aprobaciones con "send and wait" necesitan una URL pública, porque el comercial abre el enlace desde el móvil.

Además, el repositorio tiene que ser reproducible con las propias claves (D34). Hay dos preguntas que se suelen mezclar: dónde corre la demo y dónde correría en Orvalle.

## Decisión

**Demo: n8n en Docker en el Mac, con un túnel de Cloudflare.**

- `docker compose` en el repositorio: se levanta con un comando, junto a Supabase local.
- **El túnel solo expone las rutas de reanudación** de "send and wait" (`/webhook-waiting/*` y las que use el formulario, posiblemente `/form-waiting/*`; se comprueba al construir y se expone exactamente lo que use). El editor de n8n y la entrada de pruebas no se publican.
- **Túnel con nombre propio**, no un túnel rápido: un túnel rápido cambia de URL al reiniciarse y los enlaces de aprobación ya enviados dejarían de funcionar. El dominio va en `.env`, nunca en el repositorio.
- **Sin dominio propio en Cloudflare** (revisión del 19-11-2026, todo gratuito): las aprobaciones se prueban desde el propio Mac, y para la grabación del vídeo se usa un túnel rápido. Es una limitación declarada: con un túnel rápido, los enlaces de aprobación dejan de funcionar si el túnel se reinicia.
- **`WEBHOOK_URL` apunta al túnel**, para que n8n no genere los enlaces con `localhost`.
- n8n llega a Supabase local por `host.docker.internal`.

**Orvalle: n8n autoalojado en una máquina virtual en la UE**, gestionada por IT o por el partner, con copias de seguridad, actualizaciones, monitorización y el editor accesible solo desde la red interna. El esquema `intake` necesita su propia base de datos, porque el ERP real no es Supabase: Postgres en la misma máquina virtual o Supabase en la nube. El coste está en la [sección 10 de 04](../04-solution-design.md#10-contraste-de-sn08-y-sn09).

## Alternativas descartadas

- **n8n Cloud.** El motivo decisivo es técnico: no permite módulos npm externos. El coste es secundario y depende de nuestro diseño: el consumidor de envíos, que mira la tabla cada minuto, genera unas 43.000 ejecuciones al mes, más de lo que incluye el plan de 50 €/mes (10.000). Con un disparador por evento serían muchas menos, pero la consulta cada minuto se mantiene como red de seguridad del outbox.
- **Docker en un VPS para la demo:** siempre encendido, pero hay que ocuparse de TLS, actualizaciones y copias de seguridad, y cuesta cada mes. Para una demo es trabajo de operaciones que no aporta al portfolio.

## Consecuencias

- La demo es gratuita y reproducible, y solo expone a internet lo imprescindible.
- **Limitación declarada:** sin dominio propio, las aprobaciones desde el móvil solo funcionan mientras dure el túnel rápido.
- **Limitación declarada:** el Mac tiene que estar encendido durante la demo y mientras haya aprobaciones pendientes. Si se apaga, los enlaces no responden hasta que vuelve. Que las ejecuciones en espera sobrevivan a un reinicio se comprueba al construir.
- El ADR deja claro qué atajos valen en una demo y cuáles no en producción.
