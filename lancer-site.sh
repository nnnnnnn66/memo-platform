#!/usr/bin/env bash
# Lance le SITE étudiant de la plateforme (interface web, port 9000).
#
# Même raison d'être que lancer-orchestrateur.sh : sous systemd, on reproduit exactement ce qu'un
# démarrage manuel fait — charger l'environnement, puis remplacer le shell par uvicorn. On ne
# refait PAS `pip install` ici (contrairement à run-site.sh, prévu pour un premier essai à la
# main) : au démarrage du serveur, une installation de dépendances ferait échouer ou ralentirait
# le service. Les dépendances sont figées dans requirements.txt et installées une fois pour toutes.
#
# ATTENTION AU PORT : les agents occupent 8010 à 8130 (voir config/settings-orchestrateur.yaml) et
# l'orchestrateur 8000. Le site est placé HORS de cette plage — ne pas le remettre à 8090, qui
# appartient à l'agent 9 (méthodologie).
#
# Le site n'écoute QUE sur la boucle locale : c'est la passerelle HTTPS (Caddy) qui l'expose au
# monde, et elle seule. Le site ne parle qu'à l'orchestrateur (http://127.0.0.1:8000).
set -euo pipefail
cd "$(dirname "$0")"

set -a
# shellcheck disable=SC1091
. /root/.hermes/.env 2>/dev/null || true
set +a

export PYTHONPATH="src:${PYTHONPATH:-}"
exec .venv/bin/uvicorn site_web.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-9000}" --workers "${WORKERS:-2}"
