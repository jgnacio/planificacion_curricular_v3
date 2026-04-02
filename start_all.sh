#!/usr/bin/env bash
# ─────────────────────────────────────────────
# start_all.sh — Levanta todo el backend en paralelo
#
# Servicios:
#   Puerto 8000 → ADK agent server  (chat conversacional)
#   Puerto 8001 → FastAPI REST      (planificaciones, alumnos, curriculum)
#
# Prerequisitos:
#   - Open Notebook corriendo (docker compose up -d)
#   - .env con GOOGLE_API_KEY y GOOGLE_GENAI_USE_VERTEXAI=1
#
# Uso:
#   ./start_all.sh          → inicia todo
#   Ctrl+C                  → detiene ambos servidores
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

if [ ! -f ".venv/bin/activate" ]; then
  echo -e "${RED}ERROR: No existe .venv — ejecutá: python -m venv .venv && pip install -r requirements.txt${NC}"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo -e "${RED}ERROR: No existe .env${NC}"
  exit 1
fi

source .venv/bin/activate
source .env 2>/dev/null || true

if [ -z "${GOOGLE_API_KEY:-}" ]; then
  echo -e "${RED}ERROR: GOOGLE_API_KEY no está en .env${NC}"
  exit 1
fi

if [ -z "${GOOGLE_GENAI_USE_VERTEXAI:-}" ]; then
  echo -e "${YELLOW}AVISO: GOOGLE_GENAI_USE_VERTEXAI no está en .env — el agente usará Gemini API free tier${NC}"
fi

echo -e "${GREEN}OK — .env y .venv listos${NC}"
echo ""

export APP_ENV=dev

# ── Cleanup al salir ──────────────────────────
cleanup() {
  echo -e "\n${YELLOW}Deteniendo servidores...${NC}"
  kill "${ADK_PID:-}" "${API_PID:-}" 2>/dev/null || true
  echo -e "${GREEN}Listo.${NC}"
}
trap cleanup EXIT INT TERM

# ── ADK server — puerto 8000 ──────────────────
echo -e "${GREEN}[ADK]${NC} Iniciando agent server en puerto 8000..."
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --allow_origins "*" \
  --auto_create_session \
  --reload_agents \
  . &
ADK_PID=$!

# ── FastAPI — puerto 8001 ─────────────────────
echo -e "${GREEN}[API]${NC} Iniciando FastAPI en puerto 8001..."
uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload &
API_PID=$!

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} ADK agent server  →  http://0.0.0.0:8000${NC}"
echo -e "${GREEN} FastAPI REST       →  http://0.0.0.0:8001${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " Presioná ${YELLOW}Ctrl+C${NC} para detener todo."
echo ""

wait
