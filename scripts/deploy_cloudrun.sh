#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Deploy FastAPI a Cloud Run
# Uso: bash scripts/deploy_cloudrun.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env no encontrado en $ROOT_DIR"
  exit 1
fi

# Cargar .env (ignorar comentarios y líneas vacías)
set -o allexport
# shellcheck disable=SC1090
source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
set +o allexport

INTERNAL_API_URL="${INTERNAL_API_URL:-http://localhost:8000}"  # se actualiza post-deploy

SERVICE_NAME="facilitador-api"
REGION="us-central1"
PROJECT="facilitador-docente"

echo "Deploying $SERVICE_NAME to Cloud Run ($REGION)..."

# Construir lista de env vars — omitir las vacías para no sobreescribir defaults
ENV_VARS="APP_MODULE=api.main:app"
ENV_VARS+=",GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}"
ENV_VARS+=",INTERNAL_API_KEY=${INTERNAL_API_KEY}"
ENV_VARS+=",FRONTEND_DOMAIN=${FRONTEND_DOMAIN}"
[ -n "${CLERK_JWKS_URL:-}" ]               && ENV_VARS+=",CLERK_JWKS_URL=${CLERK_JWKS_URL}"
[ -n "${DATABASE_URL:-}" ]                 && ENV_VARS+=",DATABASE_URL=${DATABASE_URL}"
[ -n "${AGENT_ENGINE_RESOURCE_NAME:-}" ]   && ENV_VARS+=",AGENT_ENGINE_RESOURCE_NAME=${AGENT_ENGINE_RESOURCE_NAME}"
[ -n "${AI_STUDIO_API_KEY:-}" ]            && ENV_VARS+=",AI_STUDIO_API_KEY=${AI_STUDIO_API_KEY}"
[ -n "${GOOGLE_CLOUD_LOCATION:-}" ]        && ENV_VARS+=",GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}"
[ -n "${GOOGLE_GENAI_USE_VERTEXAI:-}" ]    && ENV_VARS+=",GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI}"
[ -n "${FRONT_URL:-}" ]                    && ENV_VARS+=",FRONT_URL=${FRONT_URL}"
[ -n "${MP_ACCESS_TOKEN:-}" ]              && ENV_VARS+=",MP_ACCESS_TOKEN=${MP_ACCESS_TOKEN}"
[ -n "${MP_WEBHOOK_SECRET:-}" ]            && ENV_VARS+=",MP_WEBHOOK_SECRET=${MP_WEBHOOK_SECRET}"
[ -n "${GCS_BUCKET_NAME:-}" ]              && ENV_VARS+=",GCS_BUCKET_NAME=${GCS_BUCKET_NAME}"
[ -n "${GCS_SERVICE_ACCOUNT_EMAIL:-}" ]    && ENV_VARS+=",GCS_SERVICE_ACCOUNT_EMAIL=${GCS_SERVICE_ACCOUNT_EMAIL}"
[ -n "${OPEN_NOTEBOOK_URL:-}" ]            && ENV_VARS+=",OPEN_NOTEBOOK_URL=${OPEN_NOTEBOOK_URL}"
[ -n "${OPEN_NOTEBOOK_API_KEY:-}" ]        && ENV_VARS+=",OPEN_NOTEBOOK_API_KEY=${OPEN_NOTEBOOK_API_KEY}"
[ -n "${OPEN_NOTEBOOK_NOTEBOOK_ID:-}" ]    && ENV_VARS+=",OPEN_NOTEBOOK_NOTEBOOK_ID=${OPEN_NOTEBOOK_NOTEBOOK_ID}"
[ -n "${OPEN_NOTEBOOK_MODEL:-}" ]          && ENV_VARS+=",OPEN_NOTEBOOK_MODEL=${OPEN_NOTEBOOK_MODEL}"

gcloud run deploy "$SERVICE_NAME" \
  --source "$ROOT_DIR" \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated \
  --update-env-vars "$ENV_VARS"

echo ""
echo "Deploy completado."
echo "Copiá la URL del servicio y actualizá INTERNAL_API_URL en Cloud Run:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --update-env-vars INTERNAL_API_URL=<URL>"
