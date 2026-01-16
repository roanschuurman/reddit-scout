#!/bin/bash
# Simple local development script
# Uses remote dev database on Coolify

set -e

echo "==> Running migrations..."
uv run alembic upgrade head

echo "==> Starting dev server..."
uv run uvicorn reddit_scout.api.main:app --reload --port 8000
