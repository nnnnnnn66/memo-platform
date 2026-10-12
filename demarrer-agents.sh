#!/usr/bin/env bash
# Démarre (ou arrête) les DOUZE agents de la plateforme — un par un, en arrière-plan.
#
# Pourquoi ce script existe : chaque agent a son `run-*.sh`, mais rien ne les démarrait ENSEMBLE.
# Or l'orchestrateur appelle les agents comme des services : un agent éteint fait échouer l'étape
# qu'il sert, avec une erreur d'indisponibilité — pas une erreur de méthode.
#
# Usage :  ./demarrer-agents.sh            (démarre ce qui n'écoute pas encore, puis vérifie)
#          ./demarrer-agents.sh --etat     (qui écoute, qui est éteint ?)
#          ./demarrer-agents.sh --arreter  (arrête tous les agents)
#
# Deux leçons de la première utilisation, et c'est pour elles que ce script est écrit ainsi :
#   1. trois `run-*.sh` n'avaient pas le droit d'exécution — d'où le lancement via `bash` ;
#   2. la première version annonçait « démarré » sans vérifier, donc annonçait des agents qui
#      n'existaient pas. Un lanceur qui affirme sans constater ment.
set -u
cd "$(dirname "$0")"

# Les agents lisent leurs secrets dans ~/.hermes/.env — on ne les affiche JAMAIS.
set -a
# shellcheck disable=SC1091
. /root/.hermes/.env 2>/dev/null
set +a

# L'ordre suit le parcours : plus facile à lire dans les journaux.
SCRIPTS=(
  run-sujet.sh run-probleme.sh run-litterature.sh run-problematique.sh run-question.sh
  run-objectifs.sh run-hypotheses.sh run-methodologie.sh run-protocole.sh run-resultats.sh
  run-coherence.sh run-conclusion.sh
)

port_de() { grep -oE 'PORT:-[0-9]+' "$1" 2>/dev/null | grep -oE '[0-9]+' | head -1; }
ecoute()  { ss -ltn 2>/dev/null | grep -q ":$1 "; }

case "${1:-}" in
  --etat)
    for script in "${SCRIPTS[@]}"; do
      port="$(port_de "$script")"
      if ecoute "$port"; then printf "  %-22s au travail (port %s)\n" "$script" "$port"
      else                     printf "  %-22s éteint\n" "$script"; fi
    done
    exit 0
    ;;
  --arreter)
    for script in "${SCRIPTS[@]}"; do
      port="$(port_de "$script")"
      pids="$(ss -ltnp 2>/dev/null | grep ":$port " | grep -oE 'pid=[0-9]+' | grep -oE '[0-9]+')"
      for pid in $pids; do kill "$pid" 2>/dev/null && printf "  %-22s arrêté\n" "$script"; done
    done
    exit 0
    ;;
esac

echo "Démarrage des agents…"
lances=()
for script in "${SCRIPTS[@]}"; do
  port="$(port_de "$script")"
  if ecoute "$port"; then
    printf "  %-22s déjà au travail (port %s)\n" "$script" "$port"
    continue
  fi
  # `bash ./script` et non `./script` : trois run-*.sh n'avaient pas le droit d'exécution, et
  # `nohup ./script` échouait sur « Permission denied ». Ce droit ne doit pas décider si un agent
  # démarre.
  nohup bash "./$script" >"/tmp/agent-${port}.log" 2>&1 &
  lances+=("${script}:${port}")
  printf "  %-22s lancement en cours (port %s)\n" "$script" "$port"
done

if [ "${#lances[@]}" -eq 0 ]; then
  echo
  echo "Les douze agents étaient déjà au travail."
  exit 0
fi

# On CONSTATE, on ne suppose pas : la première version annonçait « démarré » sans vérifier, et
# annonçait donc des agents qui n'existaient pas. Chaque `run-*.sh` installe ses dépendances avant
# d'écouter — d'où l'attente.
echo
echo "Vérification (chaque agent s'installe avant d'écouter)…"
for _ in $(seq 1 36); do
  reste=0
  for item in "${lances[@]}"; do ecoute "${item##*:}" || reste=1; done
  [ "$reste" -eq 0 ] && break
  sleep 5
done

echo
for item in "${lances[@]}"; do
  script="${item%%:*}"; port="${item##*:}"
  if ecoute "$port"; then
    printf "  ✅ %-22s au travail (port %s)\n" "$script" "$port"
  else
    printf "  ❌ %-22s N'A PAS DÉMARRÉ. Dernières lignes de son journal :\n" "$script"
    tail -4 "/tmp/agent-${port}.log" 2>/dev/null | sed 's/^/       /'
  fi
done
