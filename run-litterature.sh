#!/usr/bin/env bash
# Lance l'Agent Revue de littérature V1 (serveur FastAPI dédié, port 8030).
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="src:${PYTHONPATH:-}"
exec uvicorn literature_review_agent.main:app --host 0.0.0.0 --port "${PORT:-8030}"
