#!/usr/bin/env bash
# Run Alembic migrations against Supabase (production).
#
# Usage:
#   export SUPABASE_DATABASE_URL="postgresql+psycopg2://..."
#   ./scripts/migrate_supabase.sh
#
# The script stamps the DB at the baseline revision (safe if tables already
# exist from pre-Alembic deploy) then upgrades to head.
# Data in the old `alumnos` table is preserved — the migration copies it to
# `students` before dropping.

set -euo pipefail

if [[ -z "${SUPABASE_DATABASE_URL:-}" ]]; then
  echo "Error: SUPABASE_DATABASE_URL is not set."
  echo "  export SUPABASE_DATABASE_URL='postgresql+psycopg2://user:pass@host:port/db'"
  exit 1
fi

cd "$(dirname "$0")/.."

echo "==> Checking current Alembic state on Supabase..."
DATABASE_URL="$SUPABASE_DATABASE_URL" uv run alembic current 2>&1 || true

echo ""
echo "==> Stamping at add_descripciones_fundadas (all migrations already applied on Supabase via create_all)..."
DATABASE_URL="$SUPABASE_DATABASE_URL" uv run alembic stamp add_descripciones_fundadas

echo ""
echo "==> Done. Final state:"
DATABASE_URL="$SUPABASE_DATABASE_URL" uv run alembic current
