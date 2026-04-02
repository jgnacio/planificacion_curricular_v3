#!/usr/bin/env bash
# ─────────────────────────────────────────────
# start_adk.sh — ADK agent server (puerto 8000)
# Usado por Flutter y Next.js para el chat con el agente.
# ─────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

source .venv/bin/activate

export APP_ENV=dev

adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --allow_origins "*" \
  --auto_create_session \
  --reload_agents \
  .
