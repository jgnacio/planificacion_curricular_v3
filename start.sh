#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if ! command -v uv &>/dev/null; then
  echo -e "${RED}ERROR: uv no está instalado — https://docs.astral.sh/uv/${NC}"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo -e "${RED}ERROR: .env no encontrado${NC}"
  exit 1
fi

set -a; source .env; set +a

if [ -z "${GOOGLE_API_KEY:-}" ]; then
  echo -e "${RED}ERROR: GOOGLE_API_KEY no está en .env${NC}"
  exit 1
fi

export APP_ENV=dev

cleanup() {
  echo -e "\n${YELLOW}Deteniendo...${NC}"
  kill "${API_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo -e "${GREEN}Iniciando FastAPI en puerto 8001...${NC}"
uv run uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload &
API_PID=$!

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} API → http://localhost:8001${NC}"
echo -e "${GREEN} Docs → http://localhost:8001/docs${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " ${YELLOW}Ctrl+C${NC} para detener."

wait
