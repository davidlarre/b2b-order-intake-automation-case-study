# Task runner de n8n con mailparser, para leer el .eml en el nodo Code (04, sección 12).
# La versión del runner tiene que ser la misma que la de n8n (docker-compose.yml).
FROM n8nio/runners:2.48.5

USER root
RUN cd /opt/runners/task-runner-javascript && pnpm add mailparser@3.14.1
# Permite mailparser en el nodo Code. Es la configuración por defecto de la imagen con un solo cambio:
# NODE_FUNCTION_ALLOW_EXTERNAL pasa de "moment" a "mailparser".
COPY n8n-task-runners.json /etc/n8n-task-runners.json
USER runner
