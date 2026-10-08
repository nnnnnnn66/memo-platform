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
- [x] **Bug de chaîne corrigé (passation 3 → 4)** : la sortie réelle de l'Agent 3 place ses
      documents sous `corpus.documents`, alors que l'entrée de l'Agent 4 les attendait à la racine
      → sur une sortie réelle de 8 documents, l'Agent 4 en recevait **0** et répondait « corpus
      vide » au lieu de travailler. L'entrée accepte désormais les deux formes (pont automatique).
      Constat : aucun test ne passait la sortie RÉELLE d'un agent au suivant — chaque agent était
      testé avec un payload fabriqué à la main. 3 tests de chaîne ajoutés.
      Passations vérifiées : 1 → 2 OK, 2 → 3 OK (exige seulement `validation.verified`), 3 → 4
      corrigée.
- [x] **Test de CHAÎNE réel Agent 1 → 2 → 3 → 4 (2026-10-07)** : chaque sortie réelle alimente le
      suivant, jusqu'au verdict du vérificateur. Résultat : A1 `verified`, A2 `verified`,
      A3 `verified` (5 documents, 2 lus en texte intégral), A4 `verification_failed` → cause
      identifiée (bibliographie, ci-dessous) → **après correctif, A4 `verified`, zéro correction**
      (vérifié en rejouant le vérificateur sur la sortie réelle reconstruite). Script :
      `~/.hermes/cache/scratch/e2e_chaine.py` ; sorties d'étape conservées dans `chaine/stage*.json`.
- [x] **Bug de bibliographie de l'Agent 4 (contrôle L10)** : les fournisseurs renvoient « Nom
      Initiales » (« Mutiganda JC », « Jiang T ») ; l'Agent 4 prenait le dernier mot pour le nom et
      écrivait « JC, M. » au lieu de « Mutiganda, J. C. ». Même famille de bug que celui corrigé
      sur l'Agent 3, mais implémentation distincte (`bibliography/styles.py`) → détection des
      blocs d'initiales collés (« JC », « MÈ ») et éclatement en « J. C. ». 3 tests ajoutés.
- [x] **Clé OpenAlex gratuite — POSÉE et VÉRIFIÉE le 2026-10-09** : lue depuis `~/.hermes/.env`
      sous `OPENALEX_API_KEY` et transmise en en-tête `Authorization` (jamais dans l'URL ni dans
      les journaux) par les agents 3 et 4. Vérifié par un appel réel à l'API :
      `HTTP 200`, `X-RateLimit-Limit: 10000` (budget quotidien), `X-RateLimit-Remaining: 9990`
      — là où le serveur recevait `429` avec le quota anonyme partagé par IP.
      Prérequis (corrigé) : les agents ne lisaient **pas** `~/.hermes/.env` — seuls le `.env` du
      projet (inexistant) était chargé ; chaque agent charge désormais les deux.
      *Filet de sécurité* : en cas d'exposition de la clé, la faire tourner depuis
      openalex.org → Settings → API key → Rotate, puis relancer `bash /root/poser-cle-openalex.sh`.
- [ ] Agent suivant (à définir) — un seul agent à la fois

