#!/usr/bin/env bash
# Lance l'Orchestrateur de la plateforme (serveur FastAPI dédié, port 8000).
# C'est lui qui fait circuler les sorties RÉELLES d'une étape vers la suivante et qui applique
# le portillon humain et le quota.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="src:${PYTHONPATH:-}"
# Écoute par défaut sur la BOUCLE LOCALE : l'orchestrateur est le SEUL client des agents, et il
# n'est lui-même appelé que par la plateforme. Pour l'exposer (derrière la passerelle HTTPS) :
# HOST=0.0.0.0 ./run-orchestrateur.sh — à réserver à un accès maîtrisé et authentifié.
exec uvicorn orchestrator.main:app --workers "${WORKERS:-2}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
