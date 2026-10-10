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
      **Rotation effectuée le 2026-10-09 et vérifiée** : la clé exposée renvoie désormais `401`
      (morte), la nouvelle répond `200` sur 3 appels successifs.
- [x] **Agent 5 — Question de recherche : implémenté et VALIDÉ en exécution réelle (2026-10-09)**
      (`src/research_question_agent/`, API `/question/analyze`, profil Hermes `agent-question`,
      `run-question.sh`) : pré-cadrage, compréhension P1, intention P2 (+ contrôle d'intention
      déterministe), formulation P3, contrôles de neutralité codés (F2–F6 : présupposé, question
      double, question trop large, délimitation non sourcée), clarification documentaire bornée
      (désactivée par défaut), vérificateur indépendant (C1–C12), puis **portillon humain** — le
      statut `validated` ne vient que de la décision de l'étudiant. Campagne réelle : statut
      `awaiting_human_validation`, vérificateur `verified` (12/12), 0 correction, confiance 0,95,
      décision étudiante `validated`.
- [x] **Blocage réel de l'Agent 5 corrigé (règle F5)** : la campagne échouait AVANT le vérificateur
      (`PipelineError: formulation non conforme — F5: délimitation ajoutée sans source
      (geo=Côte d'Ivoire, Abidjan)`). Ce n'était pas une invention du modèle : l'étudiant fournit le
      pays et la ville dans DEUX champs distincts, et F5 exigeait la délimitation entière comme bloc
      contigu. Un défaut déterministe (donc du code, pas du prompt). F5 vérifie désormais chaque
      élément d'une délimitation composée (« X, Y », « X et Y ») ; une délimitation dont UN élément
      n'est nulle part reste signalée. 2 tests ajoutés. Suite : `pytest -q` = 269 tests.
- [x] **Agent 6 — Objectifs de recherche : implémenté et VALIDÉ en exécution réelle (2026-10-09)** :
      suite complète `pytest -q` = **304 tests**, hors réseau ; campagne réelle DeepSeek jusqu'au
      verdict `verified` (13/13) puis décision étudiante `validated`. Détails et résultats :
      `docs/architecture-agent-06-objectifs-recherche-v1.md`.
- [x] **Agent 7 — Hypothèses de recherche : implémenté et VALIDÉ en exécution réelle (2026-10-09)** :
      suite complète `pytest -q` = **341 tests**, hors réseau ; campagne réelle DeepSeek jusqu'au
      verdict `verified` (13/13) puis décision étudiante `validated`. Détails et résultats :
      `docs/architecture-agent-07-hypotheses-v1.md`.
- [ ] **Test de chaîne A4 → A5 sur sortie RÉELLE** : la passation est couverte par un test unitaire
      construit sur la forme de sortie de l'Agent 4 (`subject_reference.original`,
      `problematique_note.texte_complet`, `validation.verified`), mais pas encore par une sortie
      réelle de bout en bout (la leçon « les payloads fabriqués à la main ne prouvent rien »).
- [x] **Agent 6 — Objectifs de recherche : implémenté et VALIDÉ en exécution réelle (2026-10-09)**
      (`src/research_objectives_agent/`, API `/objectives/analyze`, profil Hermes `agent-objectifs`,
      `run-objectifs.sh`, port 8060) : pré-cadrage (question de recherche validée requise), analyse
      P1 de la question, objectif général P2, objectifs spécifiques P3 (+ alignement et faisabilité),
      contrôles codés O1–O9 (verbe d'action, **aucun résultat présupposé**, objectif ≠ hypothèse ≠
      activité administrative, redondance, délimitation/année sans source, anti-fusion), clarification
      documentaire bornée (désactivée par défaut), vérificateur indépendant (C1–C13), puis
      **portillon humain**. Campagne réelle (4 passes) : statut `awaiting_human_validation`,
      vérificateur `verified` (13/13), 0 correction, puis décision étudiante `validated`. 34 tests
      hors réseau. Paquet autonome, agents 1-5 non modifiés.
- [x] **Correctifs de l'Agent 6 issus de l'exécution réelle** : (a) champs dérivés cohérents —
      `missing_information` et faisabilité `uncertain` désormais répercutés dans `limits_of_this_output` ;
      (b) les ambiguïtés relevées par l'analyse remontent au champ `ambiguities` (avec question de
      clarification) et à `clarification_questions`. Le vérificateur ne demande plus de corrections.
- [x] **Agent 7 — Hypothèses de recherche : implémenté et VALIDÉ en exécution réelle (2026-10-09)**
      (`src/research_hypotheses_agent/`, API `/hypotheses/analyze`, profil Hermes `agent-hypotheses`,
      `run-hypotheses.sh`, port 8070) : pré-cadrage (question + objectifs requis), analyse P1, décision
      de pertinence P2 (`HYPOTHESES_RECOMMENDED` | `HYPOTHESES_NOT_REQUIRED` |
      `HYPOTHESES_REQUIRE_CLARIFICATION`), formulation P3 **uniquement si recommandées** (pas
      d'hypothèses forcées), contrôles codés H1–H8 (hypothèse ≠ question ≠ objectif ≠ fait, causalité
      non établie, examinabilité, redondance, anti-fusion), vérificateur indépendant (C1–C13), puis
      **portillon humain**. Campagne réelle : statut `awaiting_human_validation`, vérificateur
      `verified` (13/13), 0 correction, puis décision étudiante `validated`. 36 tests hors réseau.
      Paquet autonome, agents 1-6 non modifiés.
- [x] **Correctifs de l'Agent 7 issus de l'exécution réelle (4 passes avant le verdict)** : confiance
      recalculée après reformulation ; limites d'hypothèses sorties de `missing_information` ;
      ambiguïtés d'analyse consignées comme points à clarifier (fin de la contradiction décision ↔
      questions de clarification et `analysis.ambiguites` ↔ décision) ; « modère » traité comme
      causalité (H4) et prompt P3 renforcé (discriminance, non-opérationnalisation).
- [ ] **Test de chaîne A6 → A7 sur sortie RÉELLE** : passation couverte par un test unitaire (forme de
      sortie de l'Agent 6 : `general_objective`, `specific_objectives`, `validation.verified`), pas
      encore par une chaîne réelle de bout en bout.
- [ ] **Agent 7 : architecture à contresigner par le porteur** (portillon §42).
- [ ] **Agent 6 : architecture à contresigner par le porteur** (portillon §42).
- [ ] **Agent 5 : architecture à contresigner par le porteur** (portillon §42).
- [x] **Agent 8 — Diagnostic méthodologique : implémenté et VALIDÉ en exécution réelle (2026-10-09)** :
      suite complète `pytest -q` = **390 tests**, hors réseau (dont **49** pour l'agent 8) ; campagne
      réelle DeepSeek jusqu'au verdict `verified` (13/13, C1–C13), 0 correction, puis décision étudiante
      `validated`. Détails et résultats : `docs/architecture-agent-08-diagnostic-methodologique-v1.md`.
- [x] **Agent 8 — Diagnostic méthodologique : documents de référence** →
      `docs/spec-agent-08-diagnostic-methodologique.md` (SPEC reçue), `docs/elements-agent-08-diagnostic-methodologique.md`
      (fiche des 19 éléments), `docs/architecture-agent-08-diagnostic-methodologique-v1.md` (15 points, §42) ;
      profil Hermes `agent-methodologie`, `config/settings-methodologie.yaml`, `run-methodologie.sh` (port 8080).
- [x] **Correctifs de l'Agent 8 issus de l'exécution réelle** : M4 — une causalité niée n'est pas une
      causalité affirmée (fenêtre de négation en mots) ; champs `unknowns` et `alternatives_overview`
      jamais remplis (ajout au contrat du modèle / agrégation déterministe) ; `provisional` cohérent
      avec la déclaration du modèle ; rationale de confiance énonçant son calcul.
- [x] **Agent 8 — test de chaîne A7 → A8 sur sorties RÉELLES (2026-10-09)** : les sorties réelles des
      agents 5, 6 et 7 (`question_output.json`, `objectives_output.json`, `hypotheses_output.json`
      de `workspace/etudiant-demo/session-demo/`) sont ingérées **telles quelles** dans la campagne de
      l'agent 8 → `awaiting_human_validation`, vérificateur `verified` (13/13, C1–C13), 0 correction,
      puis décision étudiante `validated`. **Bug de chaîne réel trouvé et corrigé** : les
      sorties des agents 5-7 portent la vérification dans `verification_result`, alors que l'entrée de
      l'agent 8 n'acceptait que `validation` (clé des agents 1-4) → toute sortie réelle des agents 5-7
      était déclarée « non vérifiée » (mêmes symptômes que la passation 3 → 4). L'entrée accepte
      désormais les deux formes ; 2 tests de non-régression (dont l'ingestion du fichier réel).
      Script : `/root/.hermes/cache/scratch/e2e_chaine_a7_a8.py`.
- [x] **Agent 8 — correctifs de la chaîne réelle (2026-10-09)** : (a) **C11 vérifié** — le `echec` observé
      était un aléa du vérificateur LLM, non reproductible (passe suivante : 13/13) ; (b) **M5 étendu à la
      collecte** — une approche mono-méthode ne peut pas mêler collecte qualitative et quantitative
      (relevé : « entretiens sous approche quantitative ») → déclarer « mixte » ; prompt P2 aligné ;
      (c) **`coherence_controls` en français clair** — les libellés d'outillage (« M1–M3 ») n'étaient pas
      lisibles par l'étudiant. Reste **assumé** (choix de conception D5) : la séparation
      `missing_information` (manques bloquants) / `unknowns` (inconnues non bloquantes), que le
      vérificateur signale encore sans la remettre en cause.
- [x] **Agent 8 : architecture contresignée par le porteur de projet le 2026-10-09** (portillon §42).
- [x] **Audit de sécurité (2026-10-10)** — quatre points vérifiés, quatre corrections :
      1. **SSRF par redirection HTTP (corrigé)** : le client réseau ne contrôlait que l'URL
         initiale ; `urlopen` suivait ensuite les redirections SANS repasser par la liste blanche
         (démontré en local : une redirection vers un service interne était bien suivie, y compris
         `169.254.169.254`). Chaque saut est désormais revalidé (`open_checked`, tous les agents).
      2. **Permissions du fichier de secrets (corrigé)** : `~/.hermes/.env` était lisible par tous
         (`644`) → passé en `600`.
      3. **Exposition réseau des API (corrigé)** : les scripts `run-*.sh` écoutaient sur `0.0.0.0`
         alors qu'aucune route n'a d'authentification → écoute par défaut sur `127.0.0.1`
         (`HOST=0.0.0.0` pour exposer volontairement).
      4. **Vérifiés sans faille** : aucun secret dans le dépôt, aucun `eval`/`exec`/`subprocess`,
         traversée de chemin neutralisée (`workspace/<étudiant>/<session>` reste dans la racine).
      ⚠️ Reste à décider par le porteur : pare-feu inactif sur le serveur (aucune règle iptables,
      ufw inactif) — à activer en gardant l'accès SSH ouvert.
- [x] **TEST DE CHAÎNE RÉEL Agent 1 → 8 : CHAÎNE COMPLÈTE VÉRIFIÉE (2026-10-10)** — chaque agent
      reçoit la sortie RÉELLE du précédent, jusqu'au verdict du vérificateur :
      **A1 `verified`, A2 `verified`, A3 `verified`, A4 `verified`, A5 `verified`, A6 `verified`,
      A7 `verified`, A8 `verified`**.
      Script pérennisé (il avait déjà été perdu une fois en zone temporaire) :
      `scripts/e2e_chaine.py` (étapes 1 à 8, reprise par étape : `depuis=N`), sorties d'étape dans
      `workspace/chaine-live/stage<N>.json`, + `scripts/replay_verif_litterature.py` (rejoue le seul
      vérificateur de l'agent 3 sur une sortie déjà produite, en ~1 min au lieu de 25).
      Ce test a révélé **16 défauts réels** qu'aucun test unitaire ne voyait (voir les correctifs
      des 2026-10-09/10 : blocs d'initiales, capitales, affiliations, tirets typographiques,
      corpus tronqué du vérificateur, dernière reformulation non jugée, R7, R2, prompt P3).
- [x] **Extension de la chaîne aux agents 6, 7 et 8 (2026-10-10)** — quatre défauts de passation
      supplémentaires, tous invisibles en tests unitaires parce que les fixtures portaient les clés
      ATTENDUES et non les clés RÉELLEMENT produites (fixtures désormais copiées de sorties réelles) :
      (a) les agents 6 et 7 n'acceptaient la vérification amont que sous `validation`, alors que les
      agents 5 à 7 la publient sous `verification_result` → sortie pourtant validée déclarée « non
      vérifiée » ; (b) l'agent 6 lisait `upstream_problem.research_problem` (l'agent 2 publie
      `identified_problem.statement`) et `upstream_problematic.validated_problematic` (l'agent 4
      publie `problematique_note.texte_complet`) → `AttributeError` à la passation 2 → 6 ;
      (c) l'agent 7 mourait sur 17 erreurs de validation, le modèle renvoyant des OBJETS dans
      `theoretical_or_literature_support` (`list[str]`) → normalisation défensive + prompt précisé ;
      (d) l'agent 8 refusait la liste d'objets d'hypothèses de l'agent 7 et la revue de littérature
      structurée de l'agent 3 → conversion en texte (la formulation est conservée, jamais le seul
      identifiant). Outil de diagnostic ajouté : `scripts/probe_agent7.py` (capture la réponse BRUTE
      du modèle pour distinguer un JSON mal formé d'un schéma non respecté). **425 tests.**
- [x] **Agent 9 — Méthodologie (étape 9) : construit, vérifié en exécution réelle (2026-10-10)** —
      paquet autonome `src/methodology_agent/`, API `POST /methodology/protocol/analyze` (port 8090,
      `run-protocole.sh`), profil `agent-methode`, `config/settings-methode.yaml`. Transforme le
      **diagnostic validé de l'étape 8** en protocole de recherche détaillé (terrain, population,
      échantillonnage justifié, données, techniques, instruments, variables/indicateurs, analyses,
      qualité, éthique, limites, étapes), **matrice de cohérence** objectifs → données → collecte →
      analyse (construite déterministiquement : un objectif oublié devient `non_couverte`, jamais
      supprimé) et **proposition de rédaction** de la section. Quatre étages LLM (P1→P4) +
      vérificateur C1–C13 + portillon humain. Le socle de l'étape 8 est REPRIS, jamais re-tranché ;
      PRÉVU ≠ RÉALISÉ ; aucun échantillon sans justification ; aucune hypothèse si l'étape 7 a conclu
      `NOT_REQUIRED` ; aucune consigne d'établissement inventée. Campagne réelle : 1ʳᵉ passe
      `verification_failed` (C13), 2ᵉ passe **`verified`, 6/6 objectifs couverts, 5 appels LLM,
      0 correction**, puis décision étudiante `accepted` → `validated`. Docs :
      `docs/spec-agent-09-methodologie.md`, `docs/elements-agent-09-methodologie.md`,
      `docs/architecture-agent-09-methodologie-v1.md`.
- [x] **CHAÎNE RÉELLE 1 → 9 VÉRIFIÉE (2026-10-10)** — les neuf agents enchaînés sur leurs sorties
      réelles donnent tous `verified` (`scripts/e2e_chaine.py depuis=9`). **497 tests.**
- [x] **Agent 10 — Résultats et analyse (étape 10) : construit et vérifié en exécution réelle
      (2026-10-10)** — paquet autonome `src/research_results_analysis_agent/`, API
      `POST /results/analyze` (port 8100, `run-resultats.sh`), profil `agent-resultats`,
      `config/settings-resultats.yaml`. Architecture autorisée d'avance par le porteur.
      Traite les **données réellement collectées** conformément à la méthodologie validée de
      l'étape 9 : inventaire et qualité, analyse, interprétation prudente, examen des hypothèses,
      limites, rédaction de la section et **synthèse pour l'étape 11**. Principe fondateur :
      **les chiffres viennent du CODE** — le moteur déterministe `analysis/data_engine.py`
      (bibliothèque standard, aucun réseau) calcule effectifs, fréquences, moyennes, médianes,
      étendues et croisements ; le modèle ne fait que LIRE et INTERPRÉTER, et la **garde numérique**
      (contrôle Q2) refuse tout chiffre absent des résultats calculés. Sans données exploitables,
      l'agent produit un **plan d'analyse** et aucun résultat. Campagne réelle : **`verified`,
      106 résultats calculés, 6 appels LLM**, puis décision étudiante `accepted` → `validated`.
      Docs : `docs/spec-agent-10-resultats-analyse.md`,
      `docs/elements-agent-10-resultats-analyse.md`,
      `docs/architecture-agent-10-resultats-analyse-v1.md`.
- [x] **CHAÎNE RÉELLE 1 → 10 VÉRIFIÉE (2026-10-10)** — les dix agents enchaînés sur leurs sorties
      réelles donnent tous `verified` (`scripts/e2e_chaine.py depuis=10`). **559 tests.**
- [x] **Agent 11 — Conclusion (étape 11, dernière) : construit et vérifié en exécution réelle
      (2026-10-10)** — paquet autonome `src/research_conclusion_agent/`, API `POST /conclusion/write`
      (port 8110, `run-conclusion.sh`), profil `agent-conclusion`,
      `config/settings-conclusion.yaml`. Transforme les **résultats VÉRIFIÉS de l'étape 10** en
      conclusion générale : réponse argumentée à la question de recherche, bilan des objectifs et des
      hypothèses, apports, limites réelles, perspectives justifiées. Principe fondateur :
      **AUCUN RÉSULTAT NOUVEAU** — chaque affirmation centrale cite l'identifiant (`R…`) du résultat
      qui la justifie (contrôle K1), la **garde numérique** refuse tout chiffre absent des calculs
      vérifiés (K2), et sans résultats vérifiés l'agent produit un **plan de conclusion** et rien
      d'autre (K8). Contrôles codés K1–K9 (statut d'hypothèse repris de l'étape 10, causalité sans
      dispositif, hypothèse « confirmée », référence bibliographique absente du dossier, perspective
      déguisée en constat), règles métier T1–T6 (**aucune donnée personnelle reproduite**), vérificateur
      indépendant C1–C13, portillon humain. Campagne réelle : **`verified`, 22 résultats cités,
      7 sections, 4 appels LLM**, puis décision étudiante `accepted` → `validated` (confiance 0,65).
      Docs : `docs/spec-agent-11-conclusion.md`, `docs/elements-agent-11-conclusion.md`,
      `docs/architecture-agent-11-conclusion-v1.md`.
- [x] **CHAÎNE RÉELLE 1 → 11 VÉRIFIÉE (2026-10-10) — PARCOURS COMPLET** — les onze agents enchaînés
      sur leurs sorties réelles donnent tous `verified` (`scripts/e2e_chaine.py depuis=11`).
      **608 tests.** Du choix du sujet à la conclusion générale, en exécution réelle.
- [x] **Agent 13 — Vérificateur global de cohérence (étape 13) : construit et vérifié en exécution
      réelle (2026-10-10)** — paquet autonome `src/research_coherence_verifier/`, API
      `POST /coherence/audit` (port 8130, `run-coherence.sh`), profil `agent-coherence`,
      `config/settings-coherence.yaml`. Architecture autorisée d'avance (portillon 42, publiée pour
      mémoire). L'étape 12 reste réservée. **Audit TRANSVERSAL du dossier complet** : chaque étape a
      son vérificateur, personne ne vérifiait l'enchaînement. Principe de conception : **le programme
      établit les FAITS (X1–X12), le modèle juge les LIENS** — découlement question/problématique,
      service des objectifs, examinabilité des hypothèses par la méthodologie, couverture des objectifs
      par les résultats, fidélité de la conclusion, contradictions, **fusions abusives**, références
      orphelines, étapes vérifiées au contenu vide. Deux exigences dures : **aucun constat sans preuve**
      et **la portée est toujours déclarée** (ce que l'agent NE PEUT PAS vérifier : véracité du terrain,
      exactitude des sources, plagiat, style, règles locales non fournies, éthique de terrain, jugement
      du jury). Audit lui-même contrôlé (C1–C13) puis portillon humain. Campagne réelle : **`verified`,
      verdict `coherent_avec_reserves`, 9 constats fondés sur le dossier réel de la chaîne** (objectifs
      non couverts, question changée d'objet, « effets » annoncés vs analyses d'association, période
      2020-2024 contre 2024, terrain Abidjan contre 7 répondants sur 20 à Bouaké, analyse bivariée
      prévue non produite), 4 appels LLM, puis décision étudiante `accepted` → `validated`.
      Docs : `docs/spec-agent-13-verificateur-coherence.md`,
      `docs/elements-agent-13-verificateur-coherence.md`,
      `docs/architecture-agent-13-verificateur-coherence-v1.md`.
- [x] **AUDIT DE COHÉRENCE DU DOSSIER RÉEL 1 → 11 (2026-10-10)** — rapport d'audit produit sur les
      sorties réelles de la chaîne, portée déclarée (8 éléments non vérifiables), **688 tests**.
- [ ] Suite : porter la chaîne au-delà (interface étudiante, tableau de bord, export du mémoire).

