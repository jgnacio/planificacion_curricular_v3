#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Facilitador Docente — Deploy unificado
# Uso: bash scripts/deploy.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

PROJECT="facilitador-docente"
REGION="us-central1"
API_SERVICE="facilitador-api"

# ── Colores ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}▶ $*${NC}"; }
success() { echo -e "${GREEN}✓ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $*${NC}"; }
error()   { echo -e "${RED}✗ $*${NC}"; }
step()    { echo -e "\n${CYAN}${BOLD}── $* ──${NC}"; }

# ── Cargar .env ────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  error ".env no encontrado en $ROOT_DIR"
  exit 1
fi
set -o allexport
# shellcheck disable=SC1090
source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
set +o allexport

# Variable global — step_agente la rellena; step_api la usa en deploy completo
DEPLOYED_RESOURCE_NAME="${AGENT_ENGINE_RESOURCE_NAME:-}"

# ── Env vars para Cloud Run API ────────────────────────────
_build_api_env_vars() {
  local resource_name="${1:-$DEPLOYED_RESOURCE_NAME}"
  local vars="APP_MODULE=api.main:app"
  vars+=",GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-facilitador-docente}"
  vars+=",GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-us-central1}"
  vars+=",GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI:-1}"
  vars+=",INTERNAL_API_KEY=${INTERNAL_API_KEY}"
  [ -n "${INTERNAL_API_URL:-}" ]          && vars+=",INTERNAL_API_URL=${INTERNAL_API_URL}"
  [ -n "${FRONTEND_DOMAIN:-}" ]           && vars+=",FRONTEND_DOMAIN=${FRONTEND_DOMAIN}"
  [ -n "${FRONT_URL:-}" ]                 && vars+=",FRONT_URL=${FRONT_URL}"
  [ -n "${CLERK_JWKS_URL:-}" ]            && vars+=",CLERK_JWKS_URL=${CLERK_JWKS_URL}"
  [ -n "${DATABASE_URL:-}" ]              && vars+=",DATABASE_URL=${DATABASE_URL}"
  [ -n "${MP_ACCESS_TOKEN:-}" ]           && vars+=",MP_ACCESS_TOKEN=${MP_ACCESS_TOKEN}"
  [ -n "${MP_WEBHOOK_SECRET:-}" ]         && vars+=",MP_WEBHOOK_SECRET=${MP_WEBHOOK_SECRET}"
  [ -n "${GCS_BUCKET_NAME:-}" ]           && vars+=",GCS_BUCKET_NAME=${GCS_BUCKET_NAME}"
  [ -n "${GCS_SERVICE_ACCOUNT_EMAIL:-}" ] && vars+=",GCS_SERVICE_ACCOUNT_EMAIL=${GCS_SERVICE_ACCOUNT_EMAIL}"
  [ -n "${TAVILY_API_KEY:-}" ]            && vars+=",TAVILY_API_KEY=${TAVILY_API_KEY}"
  [ -n "${DISCOVERY_ENGINE_DATA_STORE_ID:-}" ] && vars+=",DISCOVERY_ENGINE_DATA_STORE_ID=${DISCOVERY_ENGINE_DATA_STORE_ID}"
  [ -n "$resource_name" ]                 && vars+=",AGENT_ENGINE_RESOURCE_NAME=$resource_name"
  echo "$vars"
}

# ============================================================
# PASO 1 — Deploy agente a Vertex AI Agent Platform
# ============================================================
step_agente() {
  step "Deploy agente → Vertex AI Agent Platform"

  info "Ejecutando deploy_agent.py..."
  AGENT_OUTPUT=$(cd "$ROOT_DIR" && uv run python deploy_agent.py 2>&1) || {
    echo "$AGENT_OUTPUT"
    error "deploy_agent.py falló."
    return 1
  }
  echo "$AGENT_OUTPUT"

  # Extraer resource name del output
  RESOURCE_NAME=$(echo "$AGENT_OUTPUT" | grep -oE 'projects/[0-9]+/locations/[^/]+/reasoningEngines/[0-9]+' | tail -1)
  if [ -z "$RESOURCE_NAME" ]; then
    error "No se pudo extraer el resource name del output."
    return 1
  fi

  DEPLOYED_RESOURCE_NAME="$RESOURCE_NAME"
  success "Agente listo: $RESOURCE_NAME"

  step "Actualizando AGENT_ENGINE_RESOURCE_NAME en $API_SERVICE"
  info "gcloud run services update $API_SERVICE --update-env-vars ..."
  gcloud run services update "$API_SERVICE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --update-env-vars "AGENT_ENGINE_RESOURCE_NAME=$RESOURCE_NAME" \
    --quiet
  success "Variable actualizada en Cloud Run."
}

# ============================================================
# PASO 2 — Deploy facilitador-api a Cloud Run
# ============================================================
step_api() {
  step "Deploy $API_SERVICE → Cloud Run"

  ENV_VARS=$(_build_api_env_vars)

  info "Construyendo y desplegando (sin enrutar tráfico aún)..."
  gcloud run deploy "$API_SERVICE" \
    --source "$ROOT_DIR" \
    --region "$REGION" \
    --project "$PROJECT" \
    --allow-unauthenticated \
    --no-traffic \
    --set-env-vars "$ENV_VARS" \
    --min-instances=1 \
    --cpu-boost \
    --no-cpu-throttling \
    --quiet

  # Revisión recién desplegada
  NEW_REVISION=$(gcloud run revisions list \
    --service "$API_SERVICE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --format "value(name)" \
    --sort-by "~createTime" \
    --limit 1)

  SERVICE_URL=$(gcloud run services describe "$API_SERVICE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --format "value(status.url)")

  echo ""
  success "Nueva revisión desplegada: ${BOLD}$NEW_REVISION${NC}"
  echo -e "  URL del servicio: ${CYAN}$SERVICE_URL${NC}"
  echo -e "  Health check:     ${CYAN}$SERVICE_URL/health${NC}"
  echo ""
  warn "El tráfico sigue apuntando a la revisión anterior."
  echo ""

  read -rp "$(echo -e "${BOLD}¿Enviar 100% del tráfico a $NEW_REVISION? [s/N]: ${NC}")" CONFIRM
  if [[ "$CONFIRM" =~ ^[sS]$ ]]; then
    info "Enrutando tráfico..."
    gcloud run services update-traffic "$API_SERVICE" \
      --to-latest \
      --region "$REGION" \
      --project "$PROJECT" \
      --quiet
    success "100% del tráfico → $NEW_REVISION"
    echo -e "  ${CYAN}$SERVICE_URL${NC}"
  else
    warn "Tráfico no modificado. La revisión anterior sigue activa."
    echo "  Para enrutar manualmente:"
    echo "    gcloud run services update-traffic $API_SERVICE --to-latest --region $REGION"
  fi
}

# ============================================================
# Menú
# ============================================================
echo ""
echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║      Facilitador Docente — Deploy            ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  1) Agente        (Vertex AI Agent Platform) ║"
echo "║  2) API           (Cloud Run)                ║"
echo "║  3) Completo      (agente → API)             ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

read -rp "$(echo -e "${BOLD}Opción [1/2/3]: ${NC}")" OPTION

case "$OPTION" in
  1)
    step_agente
    ;;
  2)
    step_api
    ;;
  3)
    step_agente || {
      error "Deploy del agente falló. Abortando — la API no fue modificada."
      exit 1
    }
    step_api
    ;;
  *)
    error "Opción inválida: $OPTION"
    exit 1
    ;;
esac

echo ""
success "Deploy completado."
