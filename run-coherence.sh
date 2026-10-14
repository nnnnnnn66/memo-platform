#!/usr/bin/env bash
# Lance l'Agent 13 — Vérificateur global de cohérence (serveur FastAPI dédié, port 8130).
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
# volontairement : HOST=0.0.0.0 ./run-coherence.sh (à réserver à un accès maîtrisé).
exec uvicorn research_coherence_verifier.main:app --workers "${WORKERS:-2}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8130}"
