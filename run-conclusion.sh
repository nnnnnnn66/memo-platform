#!/usr/bin/env bash
# Lance l'Agent Conclusion V1 (serveur FastAPI dédié, port 8110). Étape 11, dernier agent du parcours.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="src:${PYTHONPATH:-}"
# Écoute par défaut sur la BOUCLE LOCALE (127.0.0.1) : les routes des agents ne portent AUCUNE
# authentification — une exposition sur 0.0.0.0 les rendrait utilisables par n'importe qui
# (consommation de la clé LLM, lecture/écriture des espaces de session). Pour exposer
# volontairement : HOST=0.0.0.0 ./run-conclusion.sh (à réserver à un accès maîtrisé).
exec uvicorn research_conclusion_agent.main:app --workers "${WORKERS:-2}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8110}"
