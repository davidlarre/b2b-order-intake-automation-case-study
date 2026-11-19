#!/usr/bin/env bash
# Exporta un flujo de n8n a n8n/flujos/<fichero>.json, sin datos de esta instalación.
# Uso: scripts/exportar-flujo.sh <id del flujo> <fichero>
#   (los ids: docker compose --env-file .env -f n8n/docker-compose.yml exec -T n8n n8n list:workflow)
# Las credenciales nunca se exportan: el flujo solo guarda su nombre y su id.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ $# -eq 2 ]] || { echo "Uso: scripts/exportar-flujo.sh <id> <fichero>" >&2; exit 1; }
destino="n8n/flujos/$2.json"
mkdir -p n8n/flujos

docker compose --env-file .env -f n8n/docker-compose.yml exec -T n8n \
  sh -c "n8n export:workflow --id='$1' --output=/tmp/flujo.json >/dev/null && cat /tmp/flujo.json && rm /tmp/flujo.json" \
  | uv run python -I -c '
import json, sys
flujos = json.load(sys.stdin)
flujo = flujos[0] if isinstance(flujos, list) else flujos
# shared lleva el nombre y el email del propietario; el resto son datos de esta instalación.
for campo in ("shared", "createdAt", "updatedAt", "versionId", "activeVersionId", "versionCounter",
              "versionMetadata", "triggerCount", "isArchived"):
    flujo.pop(campo, None)
if flujo.get("pinData"):
    sys.exit("El flujo tiene datos fijados: quítalos en n8n antes de exportar.")
json.dump(flujo, sys.stdout, ensure_ascii=False, indent=2)
print()
' > "$destino"

if grep -q -E '@[A-Za-z0-9.-]+\.[a-z]{2,}' "$destino" && grep -o -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' "$destino" | grep -v -q '\.example$'; then
  echo "Aviso: hay emails que no son .example en $destino. Revísalo antes de commitear." >&2
fi
echo "Exportado: $destino"
