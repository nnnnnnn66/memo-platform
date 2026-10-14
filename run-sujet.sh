#!/usr/bin/env bash
# Lance l'Agent Sujet V1 (serveur FastAPI dédié, port 8010).
# C'est l'étape 1 du parcours : l'orchestrateur l'appelle en premier.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="src:${PYTHONPATH:-}"
# Boucle locale par défaut : les routes des agents ne portent AUCUNE authentification — les
# exposer sur 0.0.0.0 les rendrait utilisables par n'importe qui. L'orchestrateur est leur unique
# client. Pour exposer volontairement : HOST=0.0.0.0 ./run-sujet.sh
exec uvicorn subject_agent.main:app --workers "${WORKERS:-2}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8010}"
