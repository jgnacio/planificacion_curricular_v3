#!/usr/bin/env bash
# ─────────────────────────────────────────────
# start_api.sh — FastAPI REST server (puerto 8001)
# Maneja: planificaciones, alumnos, curriculum (Neo4j), documentos.
# ─────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

source .venv/bin/activate

export APP_ENV=dev

uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload
