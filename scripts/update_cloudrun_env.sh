#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Actualiza env vars de Cloud Run desde .env
# Uso: bash scripts/update_cloudrun_env.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env no encontrado en $ROOT_DIR"
  exit 1
fi

# Cargar .env
set -o allexport
source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
set +o allexport

SERVICE_NAME="facilitador-api"
REGION="us-central1"
PROJECT="facilitador-docente"

# ============================================================
# Construir env vars — omitir vacías
# ============================================================
ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=1"
ENV_VARS+=",GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-facilitador-docente}"
ENV_VARS+=",GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-us-central1}"
[ -n "${INTERNAL_API_KEY:-}" ]       && ENV_VARS+=",INTERNAL_API_KEY=${INTERNAL_API_KEY}"
[ -n "${INTERNAL_API_URL:-}" ]       && ENV_VARS+=",INTERNAL_API_URL=${INTERNAL_API_URL}"
[ -n "${FRONTEND_DOMAIN:-}" ]        && ENV_VARS+=",FRONTEND_DOMAIN=${FRONTEND_DOMAIN}"
[ -n "${CLERK_JWKS_URL:-}" ]         && ENV_VARS+=",CLERK_JWKS_URL=${CLERK_JWKS_URL}"
[ -n "${DATABASE_URL:-}" ]           && ENV_VARS+=",DATABASE_URL=${DATABASE_URL}"
[ -n "${OPEN_NOTEBOOK_URL:-}" ]      && ENV_VARS+=",OPEN_NOTEBOOK_URL=${OPEN_NOTEBOOK_URL}"
[ -n "${OPEN_NOTEBOOK_API_KEY:-}" ]  && ENV_VARS+=",OPEN_NOTEBOOK_API_KEY=${OPEN_NOTEBOOK_API_KEY}"
[ -n "${OPEN_NOTEBOOK_NOTEBOOK_ID:-}" ] && ENV_VARS+=",OPEN_NOTEBOOK_NOTEBOOK_ID=${OPEN_NOTEBOOK_NOTEBOOK_ID}"
[ -n "${OPEN_NOTEBOOK_MODEL:-}" ]    && ENV_VARS+=",OPEN_NOTEBOOK_MODEL=${OPEN_NOTEBOOK_MODEL}"
[ -n "${AGENT_ENGINE_RESOURCE_NAME:-}" ] && ENV_VARS+=",AGENT_ENGINE_RESOURCE_NAME=${AGENT_ENGINE_RESOURCE_NAME}"

echo "Actualizando env vars en $SERVICE_NAME..."
gcloud run services update "$SERVICE_NAME" \
  --region "$REGION" \
  --project "$PROJECT" \
  --update-env-vars "$ENV_VARS"

echo ""
echo "Env vars actualizadas."

echo ""
echo "Verificando servicio..."
curl -sf "$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" --project "$PROJECT" \
  --format='value(status.url)')/health" && echo " → /health OK" || echo " → /health aún no accesible (revisar auth)"
