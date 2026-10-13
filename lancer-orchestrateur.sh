#!/usr/bin/env bash
# Lance l'orchestrateur — point d'entrée unique du site.
#
# Ce fichier existe pour une raison précise : sous systemd, charger les secrets par
# `EnvironmentFile=` est fragile (une ligne inattendue dans un fichier de 26 Ko et le service ne
# démarre plus). On reproduit donc exactement ce qu'un démarrage manuel fait : charger l'environnement,
# puis remplacer le shell par uvicorn.
set -euo pipefail
cd "$(dirname "$0")"

set -a
# shellcheck disable=SC1091
. /root/.hermes/.env 2>/dev/null || true
set +a

export PYTHONPATH="src:${PYTHONPATH:-}"
exec .venv/bin/uvicorn orchestrator.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
