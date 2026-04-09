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

# Overrides para producción
GOOGLE_GENAI_USE_VERTEXAI=1
INTERNAL_API_URL="${INTERNAL_API_URL:-http://localhost:8000}"  # se actualiza post-deploy

SERVICE_NAME="facilitador-api"
REGION="us-central1"
PROJECT="facilitador-docente"

echo "Deploying $SERVICE_NAME to Cloud Run ($REGION)..."

# Construir lista de env vars — omitir las vacías para no sobreescribir defaults
ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI}"
ENV_VARS+=",GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}"
ENV_VARS+=",GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-us-central1}"
ENV_VARS+=",INTERNAL_API_KEY=${INTERNAL_API_KEY}"
ENV_VARS+=",INTERNAL_API_URL=${INTERNAL_API_URL}"
ENV_VARS+=",FRONTEND_DOMAIN=${FRONTEND_DOMAIN}"
ENV_VARS+=",OPEN_NOTEBOOK_NOTEBOOK_ID=${OPEN_NOTEBOOK_NOTEBOOK_ID:-notebook:plf3f24qx6nui9zmn3vl}"
ENV_VARS+=",OPEN_NOTEBOOK_MODEL=${OPEN_NOTEBOOK_MODEL:-model:fi2x3hf9fvjdxl25ljwt}"
[ -n "${CLERK_JWKS_URL:-}" ]       && ENV_VARS+=",CLERK_JWKS_URL=${CLERK_JWKS_URL}"
[ -n "${DATABASE_URL:-}" ]         && ENV_VARS+=",DATABASE_URL=${DATABASE_URL}"
[ -n "${OPEN_NOTEBOOK_URL:-}" ]    && ENV_VARS+=",OPEN_NOTEBOOK_URL=${OPEN_NOTEBOOK_URL}"
[ -n "${OPEN_NOTEBOOK_API_KEY:-}" ] && ENV_VARS+=",OPEN_NOTEBOOK_API_KEY=${OPEN_NOTEBOOK_API_KEY}"

gcloud run deploy "$SERVICE_NAME" \
  --source "$ROOT_DIR" \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated \
  --set-env-vars "$ENV_VARS"

echo ""
echo "Deploy completado."
echo "Copiá la URL del servicio y actualizá INTERNAL_API_URL en Cloud Run:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --update-env-vars INTERNAL_API_URL=<URL>"
