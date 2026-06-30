#!/usr/bin/env bash
set -euo pipefail

HOST="${HTTP_HOST:-127.0.0.1}"
PORT="${HTTP_PORT:-8000}"

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt

echo "Checking Python syntax..."
.venv/bin/python -B -m compileall -q src config log scripts tests

echo "Checking datastore boundaries..."
.venv/bin/python -B scripts/check_datastores.py || true

echo "Starting PortfolioRiskAgent at http://${HOST}:${PORT}/app"
exec .venv/bin/python -m uvicorn src.__main__:app --host "${HOST}" --port "${PORT}"
