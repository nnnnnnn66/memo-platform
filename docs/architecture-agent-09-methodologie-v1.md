# Architecture V1 — Agent Méthodologie (`methodology_agent` 1.0)

> Étape 9 du parcours. **Architecture VALIDÉE par le porteur (portillon §42, 2026-10-10) et
> implémentée.** Voir la section « État réel de l'implémentation » en fin de document.
> SPEC de référence : `docs/spec-agent-09-methodologie.md` (source de vérité).
> Fiche d'éléments : `docs/elements-agent-09-methodologie.md`.
> Prédécesseur : `docs/architecture-agent-08-diagnostic-methodologique-v1.md`.

---

## 1. Architecture

### Position dans le parcours

```
[1] Sujet ─► [2] Problème ─► [3] Revue de littérature ─► [4] Problématique
   ─► [5] Question ─► [6] Objectifs ─► [7] Hypothèses ─► [8] Diagnostic méthodologique
   ─► [9] MÉTHODOLOGIE (ce document) ─► [10] Résultats et analyse ─► [11] Conclusion
```

L'agent 9 est un **paquet Python autonome** (`src/methodology_agent/`), sur le même moule que les
agents 1 à 8 : configuration propre, bornes propres, client LLM propre, prompts propres,
vérificateur propre, workspace propre, journal d'audit propre. **Aucun agent existant n'est modifié.**

### Ce que l'agent 9 est — et n'est pas

| L'agent 9 EST | L'agent 9 N'EST PAS |
|---|---|
| Un transformateur de **choix validés** (agent 8) en **protocole opérationnel** | Un re-diagnostic : il ne re-tranche jamais les six catégories de l'agent 8 |
| Un constructeur d'**instruments** (questionnaire, guide d'entretien, grille d'observation, grille documentaire, fiche de relevé, dictionnaire de variables) | Un générateur de texte : il explique et justifie, il ne remplit pas un chapitre |
| Un constructeur de **matrice de cohérence** objectifs → données → collecte → analyse | Un exécutant de la recherche : il ne collecte rien, ne fait aucune enquête |
| Un rédacteur d'une **proposition** de section « Méthodologie », statut déclaré | Un producteur de résultats : c'est le rôle de l'agent 10 |
| Un demandeur de validation humaine à chaque décision engageante | Un décideur : il n'attribue jamais `validated` lui-même |

**Frontière dure avec l'agent 8.** L'agent 8 a produit six choix (`approche`, `logique`,
`type_recherche`, `strategie`, `collecte`, `analyse`) avec justification, alternatives et limites.
L'agent 9 les **reprend tels quels comme socle** et les déploie en protocole. Si l'agent 9 détecte
une contradiction dans ce socle (par ex. une stratégie expérimentale avec une collecte
déclarée uniquement documentaire), il **ne corrige pas en silence** : il produit un
`contradiction` explicite, marque le protocole `a_reviser` et demande l'arbitrage humain (SPEC §6,
§12, §15).

### Les quatre étages internes + vérificateur

```
Entrée        P1 — Lecture du diagnostic     P2 — Protocole détaillé
(étudiant     - diagnostic agent 8 validé    - terrain / contexte
 + amont      - choix repris et rappelés     - population cible / accessible / unité
 + agent 8)   - contradictions, manques      - échantillonnage (+ taille justifiée)
              - éléments à confirmer          - données, techniques, variables/indicateurs
                                              - qualité scientifique, éthique, limites
                                                          │
     P4 — Rédaction de la section ◄── P3 — Instruments et matrice de cohérence
     - sous-sections retenues        - instruments de collecte adaptés
     - statut déclaré                - matrice : objectif → données → collecte → analyse
     - prévu / réalisé / à confirmer - couverture vérifiée (couverte/partielle/non couverte)
                                                          │
                          Vérificateur indépendant (C1–C13) ──► Décision étudiante
```

Chaque étage LLM suit le pipeline de sécurité imposé :
`LLM → Parser → Schema → Business → Security → composant suivant`.

---

## 2. Arborescence des fichiers

```
src/methodology_agent/
├── __init__.py                      # identité du paquet (étape 9, frontière avec l'étape 8)
├── main.py                          # application FastAPI (santé + routes)
├── api/
│   ├── __init__.py
│   └── routes.py                    # POST /methodology/protocol/analyze, .../decision, GET, /health
├── core/
│   ├── __init__.py
│   ├── config.py                    # chargement config/settings-methode.yaml + clé LLM (.env)
│   ├── limits.py                    # bornes dures (appels LLM, taille, tentatives)
│   ├── errors.py                    # ErrorState, PipelineError
│   ├── logging.py                   # journal d'audit (SQLite) + logs structurés
│   ├── security_rules.py            # anti-invention, anti-fabrication, règles de contenu
│   └── sessions.py                  # isolation par student_id / session_id
├── llm/
│   ├── __init__.py
│   ├── client.py                    # client DeepSeek (budget, finish_reason, reprise)
│   └── prompts/
│       ├── p1_protocol_system.md    # P1 — lecture du diagnostic + analyse
│       ├── p2_detailed_system.md    # P2 — protocole détaillé (population, données, collecte…)
│       ├── p3_matrix_system.md      # P3 — instruments + matrice de cohérence
│       ├── p4_writing_system.md     # P4 — rédaction de la section « Méthodologie »
│       └── verifier_system.md       # vérificateur indépendant (C1–C13)
├── analysis/
│   ├── __init__.py
│   ├── protocol_rules.py            # vocabulaire d'échantillonnage, interdits, cohérence
│   └── matrix_rules.py              # construction et contrôle de la matrice de cohérence
├── pipeline/
│   ├── __init__.py
│   ├── campaign.py                  # orchestrateur (4 étages + vérificateur + décision)
│   ├── input_controller.py          # normalisation + contrôle des entrées et des amont
│   ├── prerequisites.py             # diagnostic agent 8 présent ET validé (sinon arrêt)
│   ├── input_validation.py          # validation du contrat d'entrée
│   ├── protocol_stage.py            # P1 + P2 (analyse + protocole)
│   ├── instruments_stage.py         # P3 (instruments + matrice)
│   ├── writing_stage.py             # P4 (rédaction de la section)
│   ├── protocol_checks.py           # contrôles déterministes codés P1–P9
│   ├── business_validation.py       # règles R1–R6 (statut, cohérence interne, prévu/réalisé)
│   ├── schema_validation.py         # validation des schémas produits par le modèle
│   ├── security_layer.py            # injection / exfiltration / contenus interdits
│   ├── security_validation.py       # contrôles de sécurité sur la sortie assemblée
│   ├── verifier.py                  # appel du vérificateur indépendant + boucle de correction
│   ├── decision_stage.py            # décision de l'étudiant (portillon humain)
│   ├── llm_stage.py                 # exécution générique d'un étage (JSON, schéma, re-tentative)
│   └── output_parser.py             # extraction JSON tolérante
├── schemas/
│   ├── __init__.py
│   ├── common.py                    # StrictModel, énumérations communes
│   ├── input.py                     # MethodologyRequest + UpstreamPayload (tolérance des deux clés)
│   ├── analysis.py                  # analyse P1
│   ├── protocol.py                  # protocole P2 (population, échantillonnage, données…)
│   ├── matrix.py                    # instruments + matrice de cohérence (P3)
│   ├── draft.py                     # proposition de rédaction (P4)
│   ├── decision.py                  # décision étudiante
│   ├── stages.py                    # ce que le modèle doit produire à chaque étage
│   ├── verifier.py                  # verdict + contrôles C1–C13
│   └── output.py                    # contrat de sortie final (SPEC §16)
└── storage/
    ├── __init__.py
    └── workspace.py                 # écriture des artefacts par session + journal des décisions

config/settings-methode.yaml          # configuration propre à l'agent 9
run-protocole.sh                      # lancement du service (port 8090, bind 127.0.0.1)
tests/methode/                         # suite hors réseau de l'agent 9
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `analysis/protocol_rules.py` | Vocabulaire fermé de l'échantillonnage (probabiliste / non probabiliste / exhaustif / sans objet), verbes interdits de présupposé (« nous avons collecté », « les entretiens ont montré »), marqueurs d'exigence d'établissement, contrôle de cohérence `collecte ↔ analyse` hérité du diagnostic. **Défauts déterministes traités en code, jamais par le prompt.** |
| `analysis/matrix_rules.py` | Construit la matrice objectif → données → collecte → analyse et calcule la couverture (`couverte` / `partielle` / `non couverte`). Un objectif sans donnée ou sans analyse est signalé, jamais comblé. |
| `pipeline/prerequisites.py` | Vérifie que le diagnostic de l'agent 8 est présent **et validé** ; sinon arrêt motivé (`MISSING_INFORMATION`) et proposition de clarification seulement (SPEC §5, §14). |
| `pipeline/protocol_checks.py` | Contrôles codés P1–P9 (voir § 10). |
| `pipeline/business_validation.py` | Règles R1–R6 : socle présent, statut de document cohérent, protocole ≠ réalisé, matrice sans objectif orphelin, éthique déclarée si personnes concernées, aucune auto-vérification. |
| `schemas/protocol.py` | Le cœur du contrat : `PopulationCible` / `PopulationAccessible` / `UniteAnalyse`, `Echantillonnage` (type, critères, taille, **justification obligatoire si taille chiffrée**), `Donnee`, `TechniqueCollecte`, `Instrument`, `VariableIndicatrice`, `MethodeAnalyse`, `Qualite`, `Ethique`, `Limite`, `EtapeMiseEnOeuvre`. |
| `schemas/matrix.py` | `CoherenceMatrix` : lignes `{objectif, donnees_necessaires[], techniques[], analyses[], statut, remarque}`. |

---

## 4. Flux des données

```
étudiant ─┐
          ├──► input_controller ──► prerequisites (agent 8 validé ?) ──► P1 (analyse)
amont ────┤                                        │
(1..8)    │                                        ▼
          │                              P2 (protocole détaillé)
          │                                        │
          │                              P3 (instruments + matrice)
          │                                        │
          │                              P4 (rédaction de la section)
          │                                        │
          │                    schema → business (R1–R6) → checks (P1–P9) → sécurité
          │                                        │
          │                              vérificateur (C1–C13)
          │                                        │
          │                        ┌───────────────┴───────────────┐
          │                  corrections                      verdict verified
          │                        │                               │
          └────────────────────────┴──────────────► awaiting_human_validation
                                                        │
                                          décision étudiante (accepted/modified/refused)
                                                        │
                                        validated (posé par l'HUMAIN, jamais par l'agent)
```

Chaque artefact est écrit sous `workspace/<student_id>/<session_id>/` : `analysis.json`,
`protocol.json`, `coherence_matrix.json`, `methodology_draft.json`, `methodology_output.json` et
`audit-methode.db`. Aucune écriture hors de cet espace (contrôle de traversée de chemin).

---

## 5. Modèle de données

| Objet | Clés principales | Règle |
|---|---|---|
| `Analysis` | `discipline`, `elements_disponibles[]`, `elements_manquants[]` (BLOQUANTS), `contradictions[]`, `provenance` | Un manque non bloquant va dans `unknowns`, jamais dans `elements_manquants` (leçon agent 8 : R3) |
| `Protocol` | `approche`, `type_recherche`, `strategie`, `terrain`, `population`, `echantillonnage`, `donnees[]`, `techniques[]`, `variables_indicateurs[]`, `analyses[]`, `qualite`, `ethique`, `limites[]`, `etapes[]` | Les six choix repris de l'agent 8 sont **recopiés à l'identique** ; toute divergence est une `contradiction` |
| `Echantillonnage` | `type` (probabiliste / non probabiliste / exhaustif / sans objet), `critere_inclusion[]`, `critere_exclusion[]`, `taille`, `justification`, `source_taille` | `taille` chiffrée **exige** une `justification` ET une `source_taille` (`fournie` / `documentee` / `a_determiner`) ; sinon le champ reste vide et le manque est déclaré |
| `Instrument` | `type`, `objet`, `structure[]`, `statut` | Un instrument est PROPOSÉ (`statut = propose`), jamais présenté comme administré |
| `CoherenceMatrix` | `lignes[]` (`objectif`, `donnees_necessaires[]`, `techniques[]`, `analyses[]`, `statut`) | Un objectif sans ligne est impossible : construction déterministe depuis les objectifs vérifiés de l'agent 6 |
| `MethodologyDraft` | `sections[]` (`titre`, `contenu`, `statut`), `elements_a_confirmer[]` | `statut` de chaque affirmation ∈ {prevu, realise, a_confirmer} — `realise` exige une preuve fournie par l'étudiant |
| `Output` | dossier de preuve SPEC §16 + `status` + `document_status` ∈ {brouillon, a_verifier, en_attente_de_validation, valide, a_reviser} | `document_status` distinct du statut de pipeline (leçon agent 8) |

---

## 6. Contrat d'entrée (SPEC §6)

`schemas/input.py` — `MethodologyRequest` :

| Champ | Type | Rôle |
|---|---|---|
| `student_id`, `session_id` | `str` | Isolation (obligatoires) |
| `subject_text`, `discipline`, `academic_level`, `country`, `geographical_area` | `str` | Contexte |
| `university_instructions`, `supervisor_instructions` | `str` | Consignes académiques — **données non fiables**, jamais transformées en règles inventées (SPEC §10.12-13) |
| `field_access`, `available_data`, `available_tools` | `str` | Faisabilité de terrain (contraintes fournies) |
| `previous_answers` | `list[str]` | Réponses de l'étudiant aux clarifications |
| `upstream_*` | `UpstreamPayload \| None` | Sujet, problème, littérature, problématique, question, objectifs, hypothèses, **diagnostic méthodologique** |

**Contrôle des amont (leçon de la chaîne 1→8, à appliquer dès le premier jour) :**

- `UpstreamPayload.is_verified` accepte **`validation.verified` (agents 1-4) ET
  `verification_result.verified` (agents 5-8)** — jamais `verified: false`.
- Les champs lus sur l'amont sont **ceux réellement produits** (`identified_problem.statement`,
  `problematique_note.texte_complet`, `research_hypotheses[].formulation`,
  `general_objective` / `specific_objectives`), avec repli en chaîne — jamais un nom supposé.
- Les listes de chaînes acceptent les **objets** (normalisation défensive `mode="before"`), en
  conservant la formulation, jamais le seul identifiant.
- **Le diagnostic de l'agent 8 est REQUIS et VALIDÉ** : `upstream_methodology_diagnostic` doit être
  présent, `is_verified`, et son `diagnostic_status` ∈ {`valide`, `en_attente_de_validation`} avec
  décision étudiante `accepted`. Sinon : arrêt motivé (SPEC §5, §14.1).

---

## 7. Contrat de sortie (SPEC §16)

`schemas/output.py` — dossier de preuve complet :

```
identifiant_du_memoire, version_diagnostic_agent8_utilisee, trace_validation_diagnostic,
elements_de_recherche_examines[], choix_methodologiques_retenus[] + justification,
matrice_objectifs_donnees_collecte_analyse, outils_de_collecte_proposes[],
hypotheses_de_travail[], informations_a_confirmer[], sources_methodologiques_consultees[],
limites_et_risques[], resultat_verification (verifier), remarques_etudiant_encadreur[],
historique_modifications[], document_status, date, version
+ status (statut de pipeline) + verification_result (posé par le vérificateur seul)
```

Interdits structurels : le document ne peut contenir **aucun** résultat, aucune donnée collectée,
aucune autorisation obtenue, sauf si l'étudiant les a fournis (alors marqués `realise` avec la
preuve). Le schéma lui-même n'offre aucun champ pour un résultat de recherche.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mesure |
|---|---|
| LLM01 — Injection de prompt | Tout contenu étudiant est encadré et marqué « donnée non fiable » ; les consignes académiques ne peuvent jamais modifier les règles du système (`security_layer`) |
| LLM02 — Divulgation d'informations | Aucun secret dans les prompts ; clé LLM lue dans l'environnement, jamais journalisée ; **jamais de secret dans une URL** |
| LLM03 — Chaîne d'approvisionnement | Dépendances strictement locales (`pydantic`, `fastapi`, `httpx`) ; budget 0 € |
| LLM04 — Empoisonnement de données | L'amont n'est accepté que vérifié ; les contradictions sont signalées, jamais absorbées |
| LLM05 — Sortie non sûre | `LLM → Parser → Schema → Business → Security` : rien du modèle n'est transmis brut |
| LLM06 — Agentivité excessive | Aucune action externe : `max_external_requests: 0`, pas de collecte, pas d'envoi hors vérificateur |
| LLM07 — Fuite de prompt système | Le prompt est construit côté serveur ; les tests vérifient qu'il n'est jamais renvoyé |
| LLM08 — Faiblesses d'embeddings | Aucun RAG, aucune base vectorielle en V1 |
| LLM09 — Désinformation | **Règle centrale** : ne jamais inventer participants, échantillon, dates, résultats, autorisations, référence méthodologique ni consigne d'établissement ; l'absence est déclarée, jamais comblée |
| LLM10 — Consommation non maîtrisée | Bornes dures : `max_llm_calls`, `max_input_size`, `max_verification_retries`, garde anti-non-convergence |

Isolation : tout accès disque passe par `workspace/<student_id>/<session_id>` avec contrôle de
traversée de chemin ; un étudiant ne peut jamais lire l'espace d'un autre.

---

## 9. Mécanisme de validation

```
schema_validation  →  business_validation (R1–R6)  →  protocol_checks (P1–P9)
                   →  security_validation  →  vérificateur (C1–C13)
```

| Code | Règle |
|---|---|
| R1 | Le socle (question + objectifs + diagnostic agent 8) est présent et exploitable |
| R2 | `document_status` cohérent avec les manques : un manque bloquant ⇒ jamais `valide` |
| R3 | Le protocole ne contient aucune affirmation au passé sans preuve fournie (prévu ≠ réalisé) |
| R4 | Chaque objectif a une ligne de matrice (aucun objectif orphelin) |
| R5 | Si la recherche implique des personnes, l'éthique est traitée (sinon le manque est déclaré) |
| R6 | Aucune auto-vérification, aucune auto-validation ; `verification_result` posé par le vérificateur seul |

**Échec partiel assumé** : si des violations subsistent après la dernière tentative, la campagne
**lève** (jamais de sortie non conforme transmise au vérificateur) — leçon de l'agent 2.

---

## 10. Mécanisme de vérification (SPEC §13)

Vérificateur **indépendant** (appel LLM distinct, prompt dédié, sans accès aux décisions internes) :

| Contrôle | Objet |
|---|---|
| C1 | Le protocole découle bien du diagnostic validé de l'agent 8 (aucun choix re-tranché en silence) |
| C2 | Chaque méthode est cohérente avec la question de recherche et les objectifs |
| C3 | Population et échantillonnage définis **quand c'est nécessaire** et absents quand ça ne l'est pas |
| C4 | Toute taille d'échantillon chiffrée est justifiée (aucun nombre inventé) |
| C5 | Les techniques de collecte correspondent aux données recherchées |
| C6 | Les méthodes d'analyse correspondent aux données **prévues** et à leur nature |
| C7 | Les instruments proposés sont utilisables et adaptés au sujet et au niveau de l'étudiant |
| C8 | La matrice de cohérence couvre chaque objectif ; les non-couvertures sont déclarées |
| C9 | Contraintes, limites et considérations éthiques prises en compte ; les consignes d'établissement non inventées |
| C10 | La rédaction distingue explicitement le PRÉVU du RÉALISÉ |
| C11 | Aucune donnée, source, autorisation ni référence méthodologique inventée |
| C12 | Les points restant à confirmer sont explicitement signalés |
| C13 | Le document est compréhensible par l'étudiant et discutable avec son encadreur |

**Contrôles déterministes codés (P1–P9) — le juge du fond reste le vérificateur :**

| Code | Contrôle |
|---|---|
| P1 | Verbe de collecte ou d'analyse au passé sans preuve fournie ⇒ refus (prévu ≠ réalisé) |
| P2 | Aucune méthode déduite de la seule discipline |
| P3 | `taille_echantillon` chiffrée sans `justification` ⇒ refus |
| P4 | Enquête de terrain imposée alors que le diagnostic ne la retient pas ⇒ refus |
| P5 | Hypothèses ajoutées alors que l'agent 7 a conclu `HYPOTHESES_NOT_REQUIRED` ⇒ refus |
| P6 | Analyse incompatible avec la nature des données prévues (inférentiel sur du qualitatif pur, etc.) ⇒ refus |
| P7 | Causalité affirmée sans dispositif adéquat (fenêtre de négation mesurée en mots — leçon M4) |
| P8 | Exigence présentée comme règle de l'établissement alors qu'aucune consigne n'a été fournie ⇒ refus |
| P9 | Contradiction avec le diagnostic de l'agent 8 non déclarée ⇒ refus |

**Boucle de vérification** : après la DERNIÈRE reformulation, le vérificateur est **rejoué** (leçon
de la chaîne : sinon une campagne échoue alors que la version corrigée passe). Non-convergence
(les mêmes corrections deux fois) ⇒ arrêt déclaré.

**Portillon humain (SPEC §12)** : l'agent s'arrête à `awaiting_human_validation` ; `validated` ne
peut être posé que par l'étape de décision étudiante. Les désaccords et incertitudes non résolus
sont conservés, jamais masqués.

---

## 11. Stratégie de tests

| Fichier prévu | Objet |
|---|---|
| `tests/methode/test_methode_01_regles.py` | Contrôles déterministes P1–P9 (prévu/réalisé, échantillon non justifié, hypothèses non pertinentes, causalité niée ≠ affirmée, exigence d'établissement inventée) |
| `tests/methode/test_methode_02_campagne.py` | Campagne complète avec LLM simulé (nommé `methode_helpers.py`, jamais `helpers.py`) |
| `tests/methode/test_methode_03_decision.py` | Portillon humain : `validated` ne vient jamais de l'agent ; refus et modification étudiante |
| `tests/methode/test_methode_04_securite.py` | Injection, fuite de prompt, traversée de chemin, isolation par session |
| `tests/methode/test_methode_05_api.py` | Routes HTTP |
| `tests/methode/test_methode_06_chaine_amont.py` | Passation réelle : charger un **fichier réel** de diagnostic agent 8 du disque, et échouer si la clé de vérification n'est pas reconnue |
| `tests/methode/test_methode_07_passation_reelle.py` | Les quatre pièges de passation (clé `validation` ET `verification_result`, champs réels, objets dans les listes de chaînes, entrées de commodité) |

Puis **test réel** : `scripts/e2e_chaine.py` étendu à l'étape 9 (modèle réel), et le rejeu complet
1 → 9. Les tests simulés ne prouvent rien sur les formats — leçon vérifiée du projet.

---

## 12. Dépendances

| Dépendance | État | Coût |
|---|---|---|
| `pydantic` (v2) | déjà installée | 0 € |
| `fastapi`, `uvicorn` | déjà installés | 0 € |
| `httpx` (client DeepSeek) | déjà installée | 0 € |
| Clé DeepSeek (`DEEPSEEK_API_KEY`) | déjà présente dans `~/.hermes/.env` | déjà budgétée |
| Réseau | **aucun par défaut** (`max_external_requests: 0`) | 0 € |

---

## 13. Coûts éventuels

Une campagne nominale : **5 appels LLM** (P1, P2, P3, P4, vérificateur), plus les re-tentatives et
les reformulations (borne `max_llm_calls: 20`). Aucun service payant, aucune API commerciale,
aucun envoi d'e-mail. Coût marginal : celui des jetons DeepSeek déjà utilisés par les agents 1 à 8.

---

## 14. Alternatives gratuites

| Besoin | Choix retenu (gratuit) | Alternatives écartées |
|---|---|---|
| Modèle | DeepSeek `deepseek-flash` (déjà en place) | API payantes (interdites par le budget 0 €) |
| Sources méthodologiques | aucune en V1 (le protocole se déduit des entrées + du diagnostic) | RAG / base vectorielle (hors V1, SPEC §28) |
| Stockage | fichiers JSON + SQLite locaux | base managée (payante) |
| Statistiques (agent 10, plus tard) | bibliothèque locale (`statistics`, `numpy` si déjà présente) | services en ligne (payants) |

---

## 15. Limites connues

1. **L'agent 9 ne peut pas juger la faisabilité réelle du terrain** : il ne connaît ni le budget de
   l'étudiant, ni ses autorisations, ni la disponibilité des participants. Il déclare donc les
   hypothèses de faisabilité comme « à confirmer » (SPEC §14, §15).
2. **Aucun instrument n'est testé sur le terrain** : l'agent propose des instruments, il ne les
   valide pas (pré-test, test de clarté) — cette étape est explicitement listée comme à faire par
   l'étudiant.
3. **La taille d'échantillon ne peut être calculée sans données d'entrée** : sans variance estimée,
   sans population connue, l'agent ne peut pas produire un calcul de puissance. Il propose la
   méthode de détermination et signale les informations nécessaires (SPEC §7.B).
4. **Les consignes d'établissement sont inconnues par défaut** : sans consignes fournies, la
   structure de la section suit les usages courants et **c'est déclaré** — jamais présentée comme
   une exigence de l'université de l'étudiant.
5. **Le protocole reste un document de travail** : `validated` appartient à l'étudiant/l'encadreur.
6. **Pas de génération de questionnaire prêt à imprimer en V1** : la structure et les items sont
   proposés en texte (le formatage riche relèverait de l'interface, hors périmètre des agents).

---

## Décisions à valider par le porteur de projet (portillon §42)

1. **Nom, emplacement et exposition du paquet** : `src/methodology_agent/`, API
   `POST /methodology/protocol/analyze`, port **8090** (`run-protocole.sh`), profil Hermes
   `agent-methode`. Le nom de route `/methodology/protocol/*` évite la collision avec l'agent 8
   (`/methodology/*`, port 8080). **Valider les noms.**
2. **La frontière avec l'agent 8** : l'agent 9 reprend les six catégories **sans les re-trancher**,
   et signale toute contradiction au lieu de corriger. **Confirmer cette frontière.**
3. **Nombre d'étages LLM** : quatre (P1 lecture/analyse, P2 protocole détaillé, P3 instruments +
   matrice, P4 rédaction). Alternative : trois étages (fusionner P1 dans P2). **Choisir.**
4. **La matrice de cohérence** : construction **déterministe** depuis les objectifs de l'agent 6
   (une ligne par objectif, couverture calculée). Alternative : la laisser au modèle (risque
   d'objectif oublié). **Confirmer le choix déterministe.**
5. **La liste des contrôles codés P1–P9** (§ 10) : **valider, retirer ou ajouter** — un contrôle
   déterministe mal calibré bloque une campagne saine (leçons F5, M4, R2 et R7).
6. **La règle « prévu vs réalisé »** : la valeur `realise` dans la rédaction exige une **preuve
   fournie par l'étudiant** ; sans elle, l'affirmation est refusée. **Confirmer la sévérité.**
7. **Le réseau** : `max_external_requests: 0` pour l'agent 9 en V1 (aucune vérification
   documentaire en ligne). **Confirmer.**
8. **Le contenu de la section rédigée** : structure par défaut en 10 sous-sections (SPEC §9 étape 4),
   seules les sous-sections pertinentes étant conservées. **Valider la structure par défaut.**
9. **Le statut de document** : cinq valeurs (brouillon, à vérifier, en attente de validation, validé,
   à réviser) — **confirmer l'enum**.
10. **Le budget** : `max_llm_calls: 20`. **Ajuster si nécessaire après la première campagne réelle.**

---

## État réel de l'implémentation

> **Implémenté, vérifié en exécution réelle et validé par le porteur** (feu vert du 2026-10-10 :
> « go »). Paquet `src/methodology_agent/`, API `POST /methodology/protocol/analyze` (port 8090),
> profil Hermes `agent-methode`, `config/settings-methode.yaml`, `run-protocole.sh`.

### Tests hors réseau

`pytest -q` : **497 tests** au total, dont **72 pour l'étape 9** —
contrôles P1–P9 (chacun éprouvé dans les deux sens : il refuse ce qui est fautif ET n'écrase pas ce
qui est juste), campagne complète, portillon humain, sécurité (injection, secrets, fuite de prompt,
isolation), API, passation depuis les sorties réelles de la chaîne, et les quatre pièges de passation.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

| Passe | Statut | Vérificateur | Matrice | Appels LLM |
|---|---|---|---|---|
| 1 (18/10) | `verification_failed` | `corrections_requested` (C13) | 6/6 | 22 (budget épuisé) |
| 2 (18/10) | **`awaiting_human_validation`** | **`verified`** | **6/6** | **5** |

Puis **décision étudiante sur la sortie réelle** : `accepted` → statut `validated`, document `valide`,
confiance 0,45 avec son calcul explicité. **CHAÎNE 1 → 9 entièrement `verified`.**

### Correctifs issus de l'exécution réelle

1. **Sous-objets descriptifs** : le modèle nommait librement les champs d'un instrument (« nom »,
   « description », « rubriques ») → 6 erreurs « extra inputs are not permitted » et campagne morte.
   Corrigé par `LenientModel` (tolérance aux clés inconnues) + normalisation d'alias, **réservé aux
   objets descriptifs** : les contrats (entrée, sortie, étage) restent stricts.
2. **Chaîne éclatée caractère par caractère** (BUG) : une chaîne au lieu d'une liste dans
   `modalites`/`conditions` était ITÉRÉE → « m », « o », « d »… Le vérificateur l'a signalée
   (« tableaux éclatés, illisibles »). Corrigé dans `flatten_strings` (une chaîne = un élément).
3. **Diagnostic déclaré « absent du dossier »** alors que le modèle le lisait : P1 ne recevait pas le
   bloc du diagnostic. Corrigé (le bloc est fourni à P1 comme à P2) + garde déterministe `_clean_missing`
   qui retire tout manque niant un élément pourtant présent.
4. **`trace_validation_diagnostic`** affirmée en bloc : désormais DÉRIVÉE des faits transmis
   (statut + vérification + décision).
5. **Règle métier R2 trop stricte** : elle refusait un document vérifié portant des réserves
   DÉCLARÉES — or c'est précisément ce que le portillon humain doit arbitrer. Seul le statut FINAL
   `valide` exige une vérification réussie. Même leçon que F5, M4, R2 et R7.

### Limites laissées assumées (signalées, non bloquantes)

- La matrice marque `couverte` un objectif dont les données sont prévues ; le vérificateur a signalé
  (flag, pas échec) qu'un objectif dépendant de données « à confirmer » mériterait une nuance.
- Les bornes de modalités proposées sans source sont explicitement marquées « à valider sur le terrain ».
- La taille d'échantillon reste `a_determiner` : l'agent ne peut pas la calculer sans effectif connu
  (comportement voulu, SPEC §7.B).
