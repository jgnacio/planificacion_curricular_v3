#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Deploy Agente a Cloud Run (servicio separado)
# Uso: bash scripts/deploy_agente_cloudrun.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env no encontrado en $ROOT_DIR"
  exit 1
fi

set -o allexport
source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
set +o allexport

SERVICE_NAME="facilitador-agente"
DATA_SERVICE_URL="${INTERNAL_API_URL:-https://facilitador-api-81545989837.us-central1.run.app}"
REGION="us-central1"
PROJECT="facilitador-docente"

echo "Deploying $SERVICE_NAME to Cloud Run ($REGION)..."

ENV_VARS="APP_MODULE=api.main_agent:app"
ENV_VARS+=",GOOGLE_GENAI_USE_VERTEXAI=0"
ENV_VARS+=",GOOGLE_API_KEY=${GOOGLE_API_KEY}"
ENV_VARS+=",INTERNAL_API_KEY=${INTERNAL_API_KEY}"
ENV_VARS+=",INTERNAL_API_URL=${DATA_SERVICE_URL}"
ENV_VARS+=",FRONTEND_DOMAIN=${FRONTEND_DOMAIN}"
[ -n "${CLERK_JWKS_URL:-}" ]        && ENV_VARS+=",CLERK_JWKS_URL=${CLERK_JWKS_URL}"
[ -n "${OPEN_NOTEBOOK_URL:-}" ]     && ENV_VARS+=",OPEN_NOTEBOOK_URL=${OPEN_NOTEBOOK_URL}"
[ -n "${OPEN_NOTEBOOK_API_KEY:-}" ] && ENV_VARS+=",OPEN_NOTEBOOK_API_KEY=${OPEN_NOTEBOOK_API_KEY}"
[ -n "${OPEN_NOTEBOOK_NOTEBOOK_ID:-}" ] && ENV_VARS+=",OPEN_NOTEBOOK_NOTEBOOK_ID=${OPEN_NOTEBOOK_NOTEBOOK_ID}"
[ -n "${OPEN_NOTEBOOK_MODEL:-}" ]   && ENV_VARS+=",OPEN_NOTEBOOK_MODEL=${OPEN_NOTEBOOK_MODEL}"

gcloud run deploy "$SERVICE_NAME" \
  --source "$ROOT_DIR" \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated \
  --set-env-vars "$ENV_VARS"

echo ""
echo "Deploy completado."
echo "Agente URL: $(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT --format='value(status.url)')"
echo "Actualizá NEXT_PUBLIC_AGENT_URL en el frontend con esa URL."
