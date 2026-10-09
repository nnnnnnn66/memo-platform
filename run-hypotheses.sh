#!/usr/bin/env bash
# Lance l'Agent Hypothèses de recherche V1 (serveur FastAPI dédié, port 8070).
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="src:${PYTHONPATH:-}"
exec uvicorn research_hypotheses_agent.main:app --host 0.0.0.0 --port "${PORT:-8070}"
