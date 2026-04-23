#!/usr/bin/env bash
# ─────────────────────────────────────────────
# start_all.sh — Levanta el backend
#
# Servicios:
#   Puerto 8001 → FastAPI REST (agente + planificaciones + alumnos + curriculum)
#
# Prerequisitos:
#   - Open Notebook corriendo (docker compose up -d)
#   - .env con GOOGLE_API_KEY
#
# Uso:
#   ./start_all.sh          → inicia
#   Ctrl+C                  → detiene
# ─────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

# ── Colores ───────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Verificaciones previas ────────────────────
echo -e "${YELLOW}Verificando prerequisitos...${NC}"

if ! command -v uv &>/dev/null; then
  echo -e "${RED}ERROR: uv no está instalado — https://docs.astral.sh/uv/getting-started/installation/${NC}"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo -e "${RED}ERROR: No existe .env${NC}"
  exit 1
fi

set -a; source .env; set +a

if [ -z "${GOOGLE_API_KEY:-}" ]; then
  echo -e "${RED}ERROR: GOOGLE_API_KEY no está en .env${NC}"
  exit 1
fi

if [ -z "${GOOGLE_GENAI_USE_VERTEXAI:-}" ]; then
  echo -e "${YELLOW}AVISO: GOOGLE_GENAI_USE_VERTEXAI no está en .env — el agente usará Gemini API free tier${NC}"
fi

echo -e "${GREEN}OK — .env y uv listos${NC}"
echo ""

export APP_ENV=dev

# ── Cleanup al salir ──────────────────────────
cleanup() {
  echo -e "\n${YELLOW}Deteniendo servidor...${NC}"
  kill "${API_PID:-}" 2>/dev/null || true
  echo -e "${GREEN}Listo.${NC}"
}
trap cleanup EXIT INT TERM

# ── FastAPI — puerto 8001 ─────────────────────
echo -e "${GREEN}[API]${NC} Iniciando FastAPI en puerto 8001..."
uv run uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload &
API_PID=$!

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} FastAPI REST  →  http://0.0.0.0:8001${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " Presioná ${YELLOW}Ctrl+C${NC} para detener."
echo ""

wait
