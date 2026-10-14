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
- Pour chaque agent, dans l'ordre : mission → entrées → processus → sorties →
  contraintes → vérificateur → archi minimale → test → correction → validation.

## Direction du produit — CONSIGNE DU PORTEUR (2026-10-14), PRIORITAIRE

> « l'étudiant vient parce qu'il ne sait rien sur son sujet, il ne sait pas comment il va élaborer
> son travail, donc ils sont là pour l'aider, pas pour lui poser des questions, eux agents doivent
> aller chercher les informations pour l'aider […] les informations sont versées partout, ils
> doivent aller chercher et livrer, et qu'elles soient vraies, comme la méthode de travail de
> Perplexity et d'Elicit. »

- **L'agent VA CHERCHER et LIVRE, avec ses sources.** Il ne rend plus de questionnaire à
  l'étudiant. Cela **remplace** le principe antérieur « l'agent questionne, détecte les manques »
  et « ne rien inventer : questionner plutôt que combler » (cf. SPEC §8/§44) — écart assumé et
  validé par le porteur.
- **Seule exception, stricte : les informations de TERRAIN** (le terrain de l'étudiant, sa
  population, son échantillon, ses propres données, ses contraintes d'accès). Lui seul les détient :
  c'est le **seul** objet de `questions_for_student`.
- **Ne jamais écrire « je n'ai pas trouvé »** : ce qui manque se déclare comme **constat de
  recherche** (`identified_limits`), jamais comme question rendue à l'étudiant.
- **La garantie anti-invention est CONSERVÉE** : une source citée doit avoir été **réellement
  récupérée** par la recherche (garde dans l'orchestrateur, comme pour un chiffre). C'est ce qui
  rend la règle précédente tenable : l'agent cherche pour de vrai.
- **Avancement** : porté sur l'Agent Sujet (étape 1). Les étapes 2 à 8 disposent déjà de la couche
  `sources/` ; restent leurs prompts et leurs vérificateurs à porter.

## Fonctionnement en ligne (consigne du porteur, 2026-10-13)
> « je ne veux pas qu'il attende ma validation, ils seront en ligne, donc ils doivent être
> indépendants […] qu'ils soient rapides et autonomes. »

- **Le parcours N'ATTEND PLUS de décision humaine pour avancer.** En mode `automatique`
  (`config/settings-orchestrateur.yaml`, section `parcours`), une étape produite **et vérifiée par
  son propre vérificateur** ouvre la suivante immédiatement.
- **Conséquence à ne jamais oublier :** le verdict du vérificateur INDÉPENDANT devient la seule
  barrière de qualité. Le statut « validée » ne signifie plus « approuvée par l'étudiant » mais
  « produite et vérifiée ». La décision humaine reste **possible** ; elle n'est plus **obligatoire**.
- **On n'avance JAMAIS sur une production non vérifiée** : les étapes suivantes refuseraient de
  s'appuyer dessus. Non vérifiée = on s'arrête là et on le DIT.
- **La plateforme doit se relever seule** : services systemd `memo-agents` et
  `memo-orchestrateur` (activés au démarrage). Ne pas compter sur un démarrage manuel.
- **Aucun agent n'écrit qu'une étape amont est « validée »** sans décision humaine : on écrit
  « vérifiée par son vérificateur ». Confondre les deux produit une incohérence que la vérification
  globale relève — et elle a raison de la relever.

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

## Deux consignes du porteur à appliquer partout (2026-10-14)
1. **L'agent FAIT le travail.** Il arrête lui-même l'objet précis, la période, les acteurs et la
   discipline, les justifie par les références réelles récupérées, et présente une PROPOSITION prête
   à travailler. Interdit de renvoyer à l'étudiant ce que la recherche peut établir, ou de terminer
   par un questionnaire. Seule exception stricte : le TERRAIN (accès, personnes joignables,
   autorisations, délais, moyens).
2. **L'agent répond comme un expert PRAGMATIQUE.** Réponse dès la première phrase, dense, avec
   chiffres, ordres de grandeur, seuils, formules, outils, étapes numérotées — le savoir de métier
   est un DROIT ET UN DEVOIR, présenté comme repère de pratique. Interdit de commencer par « votre
   dossier ne contient pas… » ou « je ne peux pas vous donner… ». Aucun fait inventé sur le travail
   de l'étudiant (donnée, chiffre de ses données, source non récupérée).

**Question libre** : les 12 agents exposent `POST /<prefixe>/question` (perimetre propre à chacun).
L'orchestrateur désigne l'étape (routage déterministe), appelle son agent, et RELAIE une fois si
l'agent répond que la question relève d'une autre étape (`POST /dossiers/{e}/{s}/interroger`).
`route_question` est déclarée par étape dans `config/settings-orchestrateur.yaml` (12/12).
