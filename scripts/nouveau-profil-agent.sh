#!/usr/bin/env bash
# Crée le cadre complet d'un nouvel agent : profil Hermes + squelette de ses 19 éléments.
#
# Usage : scripts/nouveau-profil-agent.sh <nom-profil> "<description>" "<chemin-derive-paquet>"
# Exemple : scripts/nouveau-profil-agent.sh agent-revue-litterature \
#             "Agent Revue de littérature — étape 3 (memo-platform)" src/literature_review_agent
#
# Ce script ne modifie aucun agent existant et n'installe rien : il ne fait que
#  1) enregistrer le profil Hermes (hermes profile create — obligatoire, sinon le profil n'existe pas) ;
#  2) écrire le squelette de ses éléments propres dans ~/.hermes/profiles/<nom>/.
# Les fichiers créés portent des « À COMPLÉTER » : ils sont à renseigner depuis la SPEC de l'agent.
set -euo pipefail

PROFILE="${1:?nom de profil requis (minuscules, tirets)}"
DESCRIPTION="${2:?description requise}"
PACKAGE="${3:?chemin du paquet requis, ex. src/literature_review_agent}"
REPO="/root/memo-platform"
PROFILE_DIR="$HOME/.hermes/profiles/$PROFILE"
AGENT_ID="$(basename "$PACKAGE")"

command -v hermes >/dev/null || { echo "hermes introuvable dans le PATH" >&2; exit 1; }

echo "== 1/2 Enregistrement du profil Hermes « $PROFILE » =="
hermes profile create "$PROFILE" --description "$DESCRIPTION"

echo "== 2/2 Squelette des éléments =="
mkdir -p "$PROFILE_DIR/memories" "$PROFILE_DIR/knowledge" "$PROFILE_DIR/skills/$PROFILE"

if [ ! -s "$PROFILE_DIR/SOUL.md" ] || ! grep -q "IDENTITÉ (Purpose)" "$PROFILE_DIR/SOUL.md"; then
  cat > "$PROFILE_DIR/SOUL.md" <<EOF
Tu es l'**$PROFILE** — agent de la plateforme d'accompagnement méthodologique du mémoire de
Master (projet \`memo-platform\`). Ce profil Hermes est ton cadre propre : identité, méthode,
connaissance, mémoire et traces de cet agent uniquement.

# STYLE
Sois direct. La longueur de la réponse suit le poids de la demande. Des faits plutôt que des
adjectifs ; en cas de doute, dis-le simplement. Langue : français.

# IDENTITÉ (Purpose)
À COMPLÉTER : rôle exact de l'agent, ce qu'il produit, ce qu'il ne produit jamais.

# MISSION
À COMPLÉTER (depuis la SPEC de l'agent, section MISSION).

# GOAL
À COMPLÉTER (critères de succès + grille de statut).

# DISTINCTIONS ABSOLUES
Sujet ≠ Problème ≠ Problématique ≠ Question de recherche : ne jamais les fusionner.
Cet agent produit uniquement : À COMPLÉTER.

# INTERDICTIONS DURES
- Ne rien inventer : information ni fournie ni vérifiée = inconnue.
- Ne jamais produire le travail de l'étudiant ni celui de l'étape suivante.
- Ne jamais s'auto-attribuer \`verified\` (réservé au vérificateur indépendant).
- À COMPLÉTER : interdits propres à cette étape.

# OÙ VIT TON TRAVAIL
- Spécification (ta loi) : $REPO/docs/spec-agent-XX-<nom>.md        # À COMPLÉTER
- Architecture validée  : $REPO/docs/architecture-agent-XX-<nom>-v1.md  # À COMPLÉTER
- Fiche des éléments    : $REPO/docs/elements-agent-XX-<nom>.md     # À COMPLÉTER
- Code                  : $REPO/$PACKAGE
- Configuration         : $REPO/config/settings-<agent>.yaml        # À COMPLÉTER
- Prompts               : $REPO/$PACKAGE/llm/prompts/
- Tests                 : $REPO/tests/<agent>/                      # À COMPLÉTER
- Traces                : $REPO/workspace/audit-<agent>.db          # À COMPLÉTER

# FRONTIÈRE
Le runtime vu par l'étudiant n'est pas Hermes : c'est le service Python/FastAPI de l'agent.
Ce profil est le cadre de conception et de travail. Cadre autonome : aucun code partagé avec
les autres agents, aucun agent existant modifié.

# MÉTHODE
1. Lire la SPEC et l'architecture avant toute modification.
2. Un seul agent à la fois ; portillon §42 (15 points) puis validation humaine avant d'implémenter.
3. Ordre imposé : mission → entrées → processus → sorties → contraintes → vérificateur → archi
   minimale → test → correction → validation.
4. Toujours terminer par un test sur modèle réel.
5. Budget 0 € ; OWASP LLM01–10 ; secrets uniquement dans ~/.hermes/.env.
6. Ne jamais éditer ~/.hermes/config.yaml à la main (utiliser \`hermes config set\`).
EOF
fi

cat > "$PROFILE_DIR/.hermes.md" <<EOF
# Contexte de projet — $PROFILE

Profil Hermes \`$PROFILE\`. Règles de projet complètes : \`$REPO/AGENTS.md\` (cwd-only : travailler
depuis \`$REPO\`).

## Maillon couvert
À COMPLÉTER : étape du parcours (1 Sujet, 2 Problème, 3 Revue de littérature, …).

## Références canoniques
- \`docs/spec-agent-XX-<nom>.md\` — SPEC reçue (à déposer).
- \`docs/architecture-agent-XX-<nom>-v1.md\` — architecture 15 points validée.
- \`docs/elements-agent-XX-<nom>.md\` — fiche des 19 éléments.
- \`docs/elements-agent-z.md\` — grille commune des éléments.

## Contraintes dures
Un seul agent à la fois ; budget 0 € ; OWASP LLM01–10 ; aucune sortie LLM exécutée ;
isolation par student_id/session_id (read session_only, write workspace_only,
delete/deploy/send false) ; secrets uniquement dans \`~/.hermes/.env\` ; ne rien inventer.

## Liaison avec les autres étapes
À COMPLÉTER : entrée amont acceptée (et à quelle condition de vérification), sortie consommable
par l'étape suivante.
EOF

cat > "$PROFILE_DIR/memories/MEMORY.md" <<EOF
# Mémoire de $PROFILE

Faits durables propres à cet agent (écriture déclarative, une ligne par fait).

- À COMPLÉTER : identité technique, étape, paquet, port de service.
- À COMPLÉTER : chemins (config, prompts, tests, traces).
- À COMPLÉTER : bornes en vigueur.
- À COMPLÉTER : invariants et pièges vérifiés.
EOF

cat > "$PROFILE_DIR/knowledge/README.md" <<EOF
# Knowledge — $PROFILE

| Objet | Chemin | Rôle |
|---|---|---|
| SPEC de l'agent | \`docs/spec-agent-XX-<nom>.md\` | À COMPLÉTER |
| Architecture | \`docs/architecture-agent-XX-<nom>-v1.md\` | À COMPLÉTER |
| Fiche d'éléments | \`docs/elements-agent-XX-<nom>.md\` | À COMPLÉTER |
| Prompts | \`$PACKAGE/llm/prompts/\` | À COMPLÉTER |

## Retrieval (élément « RAG »)
À COMPLÉTER : aucune base vectorielle par défaut ; si l'agent a besoin de sources, utiliser un
étage déterministe (API officielles gratuites, hôtes en liste blanche, cache), jamais des URL
arbitraires.
EOF

cat > "$PROFILE_DIR/skills/$PROFILE/SKILL.md" <<EOF
---
name: $PROFILE
description: "Use when working on the $PROFILE agent of /root/memo-platform."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [memo-platform, $PROFILE]
    related_skills: [memo-platform]
---

# $PROFILE — méthode de travail propre à cet agent

## Quand l'utiliser
Dès qu'une tâche concerne cet agent de \`/root/memo-platform\` (conception, implémentation, test,
revue, correction). Travailler depuis \`/root/memo-platform\` (règles projet cwd-only).

## Mission
À COMPLÉTER.

## Chemins
Paquet : \`$PACKAGE\` · Config : \`config/settings-<agent>.yaml\` · Tests : \`tests/<agent>/\` ·
Traces : \`workspace/audit-<agent>.db\`.

## Procédure
1. Relire la SPEC puis l'architecture ; portillon §42 avant d'implémenter.
2. Toute sortie LLM traverse Parser → Schema → Business → Security.
3. Tests hors réseau, puis test sur modèle réel.
4. À COMPLÉTER : étapes propres à l'agent.

## Invariants
Anti-fusion des étapes méthodologiques ; aucune invention ; bornes appliquées ; budget 0 € ;
isolation par étudiant ; aucun agent existant modifié.
EOF

echo
echo "Cadre créé pour « $PROFILE » :"
echo "  $PROFILE_DIR/{SOUL.md,.hermes.md,memories/,knowledge/,skills/$PROFILE/}"
echo
echo "À faire ensuite (portillon §42) :"
echo "  1. déposer la SPEC         → $REPO/docs/spec-agent-XX-<nom>.md"
echo "  2. présenter l'architecture 15 points, ATTENDRE la validation humaine"
echo "  3. remplir les 'À COMPLÉTER' ci-dessus + docs/elements-agent-XX-<nom>.md"
echo "  4. créer le paquet $PACKAGE, config/settings-<agent>.yaml, tests/<agent>/, run-<agent>.sh"
echo "  5. vérifier : hermes profile show $PROFILE"
