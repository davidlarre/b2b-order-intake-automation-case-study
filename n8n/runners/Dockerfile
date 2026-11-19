# Task runner de n8n con las librerías del nodo Code (04, sección 12).
# Todo lo que usa el nodo Code está en n8n/modulos/extractor: mailparser, read-excel-file y el código propio
# (preprocesado de adjuntos y extractor determinista). Se instala con su pnpm-lock.yaml y --frozen-lockfile:
# si el lock no cuadra con package.json, la construcción falla, y reconstruir la imagen nunca cambia versiones.
# La versión del runner tiene que ser la misma que la de n8n (docker-compose.yml).
# Se construye con el contexto n8n/, para que se vea modulos/.
FROM n8nio/runners:2.48.5

USER root
COPY modulos/extractor /opt/modulos/extractor
RUN cd /opt/modulos/extractor \
 && rm -rf node_modules test \
 && pnpm install --frozen-lockfile --prod \
 && ln -s /opt/modulos/extractor /opt/runners/task-runner-javascript/node_modules/orvalle-extractor \
 && ln -s /opt/modulos/extractor/node_modules/mailparser /opt/runners/task-runner-javascript/node_modules/mailparser
# Permite esos dos módulos en el nodo Code. Es la configuración por defecto de la imagen con un solo
# cambio: NODE_FUNCTION_ALLOW_EXTERNAL pasa de "moment" a "mailparser,orvalle-extractor".
COPY runners/n8n-task-runners.json /etc/n8n-task-runners.json
USER runner
