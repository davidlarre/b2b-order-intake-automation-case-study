#!/usr/bin/env bash
# n8n y su task runner, siempre con el .env de la raíz (el token del runner sale de ahí).
# Uso: scripts/n8n.sh up | down | ps | logs [servicio] [-f]
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Falta .env en la raíz del repositorio (ver .env.example)." >&2
  exit 1
fi

compose=(docker compose --env-file .env -f n8n/docker-compose.yml)

case "${1:-}" in
  up)   "${compose[@]}" up -d --build ;;
  down) "${compose[@]}" down ;;  # sin -v: el volumen con los flujos y las credenciales se conserva
  ps)   "${compose[@]}" ps ;;
  logs) shift; "${compose[@]}" logs --tail 50 "$@" ;;
  *)    echo "Uso: scripts/n8n.sh up | down | ps | logs [servicio] [-f]" >&2; exit 1 ;;
esac
