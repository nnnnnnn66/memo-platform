#!/usr/bin/env bash
# Lance le SITE de la plateforme (serveur FastAPI dédié, port 9000).
#
# ATTENTION AU PORT : les agents occupent 8010 à 8130 (voir config/settings-orchestrateur.yaml) et
# l'orchestrateur 8000. Le site est donc placé HORS de cette plage — ne pas le remettre à 8090,
# qui appartient à l'agent 9 (méthodologie).
#
# Le site ne parle qu'à l'orchestrateur (par défaut http://127.0.0.1:8000) : il ne connaît ni les
# agents, ni leurs adresses, ni l'emplacement des dossiers.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="src:${PYTHONPATH:-}"
# Écoute sur la BOUCLE LOCALE : c'est la passerelle HTTPS (Caddy) qui l'expose au monde, et elle
# seule. Pour un premier essai local : ./run-site.sh puis http://127.0.0.1:9000
exec uvicorn site_web.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-9000}"
