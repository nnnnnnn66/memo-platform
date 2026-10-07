# Plateforme d'accompagnement méthodologique du mémoire (Master)

## Nature du projet
Plateforme web d'accompagnement méthodologique pour étudiants de Master réalisant un
mémoire de recherche. Elle n'écrit pas le mémoire à la place de l'étudiant : elle
accompagne son raisonnement, questionne, structure, détecte les manques et les
incohérences, et aide à améliorer progressivement.

## Architecture cible (rappel)
Étudiant → Plateforme web → Backend/API → Orchestrateur → Agent spécialisé →
Agent vérificateur → Résultat validé → Étape suivante → Vérification globale finale.

Hermes = environnement de construction / test / orchestration technique uniquement.
L'étudiant n'a jamais affaire à Hermes, au terminal, à Docker ou au serveur.

## Parcours méthodologique (13 étapes)
1. Sujet
2. Problème de recherche
3. Revue de littérature
4. Problématique
5. Question de recherche
6. Objectifs
7. Hypothèses (si pertinent)
8. Orientation méthodologique
9. Méthodologie
10. Résultats
11. Analyse / Discussion
12. Conclusion
13. Vérification globale de la cohérence

Règle absolue : **Problématique et Question de recherche restent deux éléments
distincts**, jamais fusionnés automatiquement.

## Stack retenue
Python + FastAPI. Emplacement du code : ce dossier.

## Méthode de construction (un agent à la fois)
Pour chaque agent, dans cet ordre :
1. définir sa mission ;
2. définir ses entrées ;
3. définir son processus de travail ;
4. définir ses sorties ;
5. définir ses contraintes ;
6. définir son vérificateur ;
7. créer l'architecture technique minimale ;
8. tester l'agent ;
9. corriger les problèmes ;
10. valider l'agent avant de passer au suivant.

Ne jamais construire toute la plateforme d'un coup. Un seul agent à la fois.

## État d'avancement
- [x] Cadrage général validé (ce document)
- [x] SPEC définitive Agent Sujet V1 reçue → `docs/spec-agent-sujet-v1.md` (référentiel canonique)
- [x] Architecture V1 de l'Agent Sujet (15 points, §42) → `docs/architecture-v1.md` (validée)
- [x] **Agent Sujet V1 implémenté et validé** (`src/subject_agent/`, API `/subject/analyze`,
      vérificateur indépendant, 13 tests, test réel sur modèle OK)
- [x] SPEC Agent Problème de recherche reçue → `docs/spec-agent-02-probleme.md`
- [x] Architecture Agent Problème V1 (15 points, §42) → `docs/architecture-agent-02-probleme-v1.md`
- [x] **Agent Problème V1 implémenté et validé** (`src/research_problem_agent/`,
      API `/problem/analyze`, étage de recherche documentaire, vérificateur indépendant,
      75 tests, test réel sur modèle OK) — paquet autonome, Agent Sujet non modifié
- [x] SPEC + architecture Agent Revue de littérature & Diagnostic épistémologique →
      `docs/spec-agent-03-revue-litterature.md`, `docs/architecture-agent-03-revue-litterature-v1.md`
- [x] **Agent Revue de littérature V1 implémenté et VALIDÉ** (`src/literature_review_agent/`,
      API `/literature/review`, deux étages déterministes — recherche documentaire multi-fournisseurs
      et acquisition/lecture du texte intégral des PDF d'accès ouvert —, ancrage verbatim des
      citations, sélection du corpus fondée sur la pertinence, vérificateur indépendant,
      80 tests hors réseau, campagne réelle réseau + modèle + PDF allant jusqu'au verdict du
      vérificateur : `validation.verified = true`, verdict `verified`) — paquet autonome,
      agents 1 et 2 non modifiés
- [x] SPEC & architecture Agent Problématique & Construction Théorique (étape 4) reçues →
      `docs/spec-agent-04-problematique.md`, `docs/architecture-agent-04-problematique-v1.md`,
      `docs/elements-agent-04-problematique.md` + profil Hermes `agent-problematique`
- [x] **Agent 4 — Problématique : implémenté et VALIDÉ en exécution réelle**
      (`src/problematization_agent/`, API `/problematization/analyze`, ancrage verbatim
      déterministe, gap check réseau borné, amorce d'alignement déterministe, bibliographie
      APA7, vérificateur indépendant) — campagne réelle réseau + modèle allant jusqu'au verdict :
      `validation.verified = true`, verdict `verified`, 12/12 contrôles OK, 26/26 affirmations
      ancrées. 36 tests hors réseau. Paquet autonome, agents 1-3 non modifiés.
      *(Architecture contresignée par le porteur de projet le 2026-10-07.)*
- [x] **Gap check (agent 4) rendu résilient — contresigné par le porteur le 2026-10-07** : OpenAlex
      renvoie `429` depuis ce serveur (quota gratuit *partagé par l'adresse IP*, réinitialisation à
      minuit UTC) → la vérification du gap interroge 8 fournisseurs gratuits sans clé (Crossref,
      HAL, theses.fr, OpenAIRE, DataCite, DOAJ, Europe PMC en plus d'OpenAlex), avec requêtes en
      mots-clés `OR` et pertinence déterministe. Vérifié en exécution réelle : 7 fournisseurs
      répondent malgré le 429 d'OpenAlex, échec déclaré, 5 publications proches trouvées.
- [x] **Support de la clé OpenAlex étendu à l'Agent 3 (revue de littérature)** — l'adaptateur
      OpenAlex de l'agent 3 lisait aucune clé et subissait donc le `429` partagé par IP. Il lit
      désormais `OPENALEX_API_KEY` comme l'agent 4 et la transmet en en-tête `Authorization`
      (jamais dans l'URL ni dans les journaux). Le transport (`sources/http.py`) accepte des
      en-têtes optionnels. 3 tests de non-régression. Agents 1, 2 et 4 non modifiés.
- [ ] **Clé OpenAlex gratuite (facultatif, 0 €)** : lève la limite partagée (budget 10×). À créer
      par le porteur depuis SON navigateur (openalex.org → compte → Settings → API key) : le site
      OpenAlex bloque la création de compte depuis l'IP de ce serveur. Une seule clé suffit pour
      **les agents 3 et 4** : une fois obtenue,
      `echo 'OPENALEX_API_KEY=<clé>' >> ~/.hermes/.env` — le code la lit automatiquement et l'envoie
      en en-tête `Authorization` (jamais dans l'URL ni dans les journaux),
      `src/{literature_review,problematization}_agent/sources/adapters/openalex.py`.
      Rien d'autre à modifier, aucun redémarrage nécessaire.
- [ ] Agent suivant (à définir) — un seul agent à la fois

