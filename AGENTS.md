# Projet — Plateforme d'accompagnement méthodologique du mémoire (Master)

Règles de travail pour tout agent (Hermes, Claude Code, Codex…) intervenant dans ce dépôt.
Fichier de contexte projet (découverte : cwd uniquement — doit être lancé depuis ce dossier).

## Référence canonique (à lire avant d'agir)
- `docs/spec-agent-sujet-v1.md` — SPEC DÉFINITIVE de l'Agent Sujet V1 (référentiel).
- `docs/architecture-v1.md` — architecture V1 (les 15 points du §42).
- `README.md` — cadrage, stack, méthode, état d'avancement.

## Méthode de construction (non négociable)
- **Un seul agent à la fois.** Ne jamais construire les autres agents, les autres
  vérificateurs, l'interface finale, ni l'orchestrateur complet (SPEC §4, §41, §44).
- **Portillon §42 :** avant toute implémentation importante, présenter l'architecture
  (les 15 points) et **attendre la validation humaine** avant de continuer.
- Ne jamais passer à l'étape suivante sans validation explicite de l'agent courant.
- Pour chaque agent, dans l'ordre : mission → entrées → processus → sorties →
  contraintes → vérificateur → archi minimale → test → correction → validation.

## Contraintes techniques
- Stack : **Python + FastAPI**. Emplacement : ce dossier.
- **Budget 0 €.** Ordre de préférence : ressource déjà disponible → solution gratuite →
  open source → local → service payant uniquement sur validation humaine (SPEC §16–20, §40).
  Ne jamais activer un abonnement, une carte ou le pay-as-you-go automatiquement.
- Dépendances **figées et documentées** ; aucune installation automatique.
- **Sécurité (OWASP LLM01–10) :** aucune sortie LLM utilisée sans passer par
  `Parser → Schema validation → Business validation → Security validation`.
  Moindre privilège : `read: session_only`, `write: workspace_only`,
  `delete/deploy/send: false`. Isolation par `student_id`/`session_id`.
- **Secrets uniquement** dans `~/.hermes/.env`. Jamais dans le code, la config ou les logs.
- Ne jamais éditer `~/.hermes/config.yaml` à la main (utiliser `hermes config set`).

## Rappels méthodologiques (cœur du produit)
- Sujet ≠ Problème ≠ Problématique ≠ Question de recherche : **ne jamais les fusionner**.
- **Ne rien inventer.** Information non fournie et non vérifiée = inconnue →
  questionner l'étudiant, ou marquer `verification_status = "not_verified"`.
- L'agent produit → le vérificateur (indépendant) contrôle → l'agent corrige → validation.
  L'agent ne s'auto-attribue jamais `verified`.
- Hermes n'est **pas** l'interface étudiante (SPEC §3) : l'étudiant ne voit ni terminal,
  ni Docker, ni serveur, ni fichiers internes.

## Langue
Français pour la documentation et les livrables du projet.
