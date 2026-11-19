#!/usr/bin/env bash
# Prepara la demo: base de datos limpia y los 7 correos de prueba procesados una sola vez, en híbrido y con la
# fecha de hoy. Deja una cola de revisión pequeña y realista para enseñar la app.
#
# BORRA TODOS LOS DATOS de la base local (supabase db reset): casos, pedidos y usuarios de la app.
# Después vuelve a cargar el prompt activo y los usuarios de ADV (con las contraseñas de .env).
#
# Necesita: Supabase local en marcha, y n8n en marcha con el flujo publicado (scripts/n8n.sh up).
# Uso: scripts/preparar_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

URL="http://localhost:5678/webhook/pruebas/eml"

echo "Esto BORRA todos los datos de la base de datos local (casos, pedidos y usuarios) y carga la demo."
read -r -p "¿Seguir? Escribe 'si' para continuar: " respuesta
[[ "$respuesta" == "si" ]] || { echo "Cancelado."; exit 1; }

# n8n tiene que estar en marcha y el flujo publicado: sin token, la entrada responde 403; si da 404, no está activo.
codigo=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL" || true)
case "$codigo" in
  403) ;;
  404) echo "El flujo de n8n no está publicado (la entrada de pruebas da 404)."; exit 1 ;;
  000) echo "n8n no responde en localhost:5678 (scripts/n8n.sh up)."; exit 1 ;;
  *)   echo "Respuesta inesperada de la entrada de pruebas: HTTP $codigo"; exit 1 ;;
esac

echo "== Base de datos limpia"
supabase db reset

# Tras el reset, Supabase reinicia sus servicios: la API y Auth tardan unos segundos en responder.
# Sin esta espera, el paso siguiente falla y el script se para con la base de datos vacía.
API_URL=$(supabase status -o env | sed -n 's/^API_URL=//p' | tr -d '"')
CLAVE=$(supabase status -o env | sed -n 's/^PUBLISHABLE_KEY=//p' | tr -d '"')
esperar() {
  local nombre="$1" url="$2"
  for _ in $(seq 1 45); do
    [[ "$(curl -s -o /dev/null -w "%{http_code}" -H "apikey: $CLAVE" "$url" || true)" == "200" ]] && return 0
    sleep 2
  done
  echo "$nombre no responde tras el reset ($url)."; exit 1
}
echo "== Esperando a que Supabase responda"
esperar "La API" "$API_URL/rest/v1/"
esperar "Auth" "$API_URL/auth/v1/health"

echo "== Prompt activo"
uv run scripts/cargar_prompts.py --activar

echo "== Usuarios de ADV"
uv run scripts/crear_usuarios_adv.py

echo "== Los 7 correos, en híbrido y con la fecha de hoy"
uv run scripts/enviar_eml.py data/synthetic/corte-vertical --configuracion hibrido --hoy
uv run scripts/enviar_eml.py data/synthetic/extraccion --configuracion hibrido --hoy

echo
echo "Listo. La app: cd app && npx pnpm@12.4.2 dev  →  http://127.0.0.1:5173"
