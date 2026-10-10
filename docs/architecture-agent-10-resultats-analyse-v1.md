# Architecture V1 — Agent Résultats et analyse (`research_results_analysis_agent` 1.0)

> Étape 10 du parcours. **Architecture AUTORISÉE D'AVANCE par le porteur de projet (2026-10-10)** —
> publiée pour mémoire, sans attente de validation (dérogation explicite au portillon §42 pour cet
> agent). SPEC de référence : `docs/spec-agent-10-resultats-analyse.md` (source de vérité).
> Fiche d'éléments : `docs/elements-agent-10-resultats-analyse.md`.
> Prédécesseur : `docs/architecture-agent-09-methodologie-v1.md`.

---

## 1. Architecture

### Position dans le parcours

```
[1] Sujet ─► [2] Problème ─► [3] Revue de littérature ─► [4] Problématique
   ─► [5] Question ─► [6] Objectifs ─► [7] Hypothèses ─► [8] Diagnostic méthodologique
   ─► [9] Méthodologie ─► [10] RÉSULTATS ET ANALYSE (ce document) ─► [11] Conclusion
```

Paquet Python **autonome** `src/research_results_analysis_agent/`, sur le même moule que les agents
1 à 9 : configuration propre, bornes propres, client LLM propre, prompts propres, vérificateur propre,
workspace propre, journal d'audit propre. **Aucun agent existant n'est modifié.**

### Le principe de conception qui gouverne tout : LES CHIFFRES VIENNENT DU CODE

L'étape 10 est la seule où l'agent manipule des **données**. Le risque d'invention y est maximal :
un modèle de langue produirait volontiers des moyennes, des pourcentages et des tableaux plausibles.
La défense est **structurelle, pas déclarative** :

```
données fournies (CSV / notes / corpus) ──► analysis/data_engine.py  (DÉTERMINISTE, stdlib)
                                                    │
                                                    ▼
                                     résultats CALCULÉS (effectifs, fréquences,
                                     moyennes, médianes, étendues, croisements…)
                                                    │
                          passés au modèle comme FAITS, avec leur valeur exacte
                                                    ▼
                       le modèle INTERPRÈTE, il ne calcule jamais
```

Corollaire vérifiable : **tout nombre figurant dans le texte produit doit appartenir à l'ensemble des
valeurs réellement calculées** (contrôle déterministe Q5, « liste blanche numérique »). Un chiffre
inventé est détecté mécaniquement, pas par la bonne volonté du modèle.

### Ce que l'agent 10 est — et n'est pas

| L'agent 10 EST | L'agent 10 N'EST PAS |
|---|---|
| Un analyste de données **réellement fournies** | Un générateur de données, de tableaux ou de résultats |
| Un interprète prudent, relié aux objectifs et aux hypothèses | Un rédacteur de conclusion (rôle de l'étape 11) |
| Un vérificateur de la qualité des données (manquants, doublons, incohérences) | Un nettoyeur silencieux : toute transformation est documentée et validée |
| Un présentateur honnête (limites, résultats contraires, non-couverture) | Un avocat de la thèse : un résultat contraire est présenté fidèlement |
| Un producteur d'une **synthèse exploitable par l'étape 11** | Un décideur : `validated` vient de l'humain |

### Les quatre étages internes + moteur déterministe + vérificateur

```
Entrée (données + méthodologie validée de l'étape 9 + dossier amont)
   │
   ├─ P1 — Inventaire et qualité des données   → variables, période, manquants, doublons,
   │                                             provenance, analyses impossibles en l'état
   │
   ├─ MOTEUR DÉTERMINISTE (analyse/data_engine.py) → résultats CALCULÉS (aucun LLM)
   │
   ├─ P2 — Plan d'analyse et lecture des résultats → résultats descriptifs par objectif,
   │                                                  examen des hypothèses (soutenue / non
   │                                                  soutenue / non examinable)
   │
   ├─ P3 — Interprétation et présentation → tableaux et figures DÉCRITS (titre, unités, lecture),
   │                                        comparaison à la littérature, limites, résultats
   │                                        inattendus
   │
   ├─ P4 — Rédaction de la section « Résultats et analyse » + synthèse pour l'étape 11
   │
   └─ Contrôles déterministes Q1–Q9 → validations S1–S6 → sécurité
        → VÉRIFICATEUR indépendant (C1–C13) → PORTILLON HUMAIN
```

Pipeline de sécurité imposé partout : `LLM → Parser → Schema → Business → Security`.

---

## 2. Arborescence des fichiers

```
src/research_results_analysis_agent/
├── __init__.py                     # identité (étape 10), principe « les chiffres viennent du code »
├── main.py                         # application FastAPI
├── api/routes.py                   # POST /results/analyze, /results/{...}/decision, GET, /health
├── core/
│   ├── config.py  limits.py  errors.py  logging.py  security_rules.py  sessions.py
├── llm/
│   ├── client.py
│   └── prompts/
│       ├── p1_inventory_system.md      # P1 — inventaire et qualité des données
│       ├── p2_analysis_system.md       # P2 — plan d'analyse et lecture des résultats calculés
│       ├── p3_interpretation_system.md # P3 — interprétation, présentation, limites
│       ├── p4_writing_system.md        # P4 — rédaction + synthèse pour l'étape 11
│       └── verifier_system.md          # vérificateur indépendant (C1–C13)
├── analysis/
│   ├── data_engine.py              # MOTEUR DÉTERMINISTE : parsing CSV, statistiques descriptives
│   ├── numeric_guard.py            # liste blanche numérique + détection des chiffres non calculés
│   └── results_rules.py            # contrôles codés Q1–Q9
├── pipeline/
│   ├── campaign.py                 # orchestrateur (4 étages + moteur + vérificateur + décision)
│   ├── input_controller.py  input_validation.py  prerequisites.py
│   ├── inventory_stage.py          # P1
│   ├── analysis_stage.py           # moteur + P2
│   ├── interpretation_stage.py     # P3
│   ├── writing_stage.py            # P4
│   ├── results_checks.py           # application de Q1–Q9 + contrôles de cohérence
│   ├── business_validation.py      # S1–S6 (statut, honnêteté, anti-invention)
│   ├── schema_validation.py  security_layer.py  security_validation.py
│   ├── verifier.py  decision_stage.py  llm_stage.py  output_parser.py
├── schemas/
│   ├── common.py  input.py  inventory.py  analysis.py  interpretation.py  draft.py
│   ├── decision.py  stages.py  verifier.py  output.py
└── storage/
    ├── workspace.py  audit.py

config/settings-resultats.yaml      # configuration propre
run-resultats.sh                    # service (port 8100, bind 127.0.0.1)
tests/resultats/                    # suite hors réseau
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `analysis/data_engine.py` | **Cœur anti-invention.** Parse un jeu de données fourni (CSV en texte, séparateur et en-tête détectés), identifie les colonnes numériques et catégorielles, et calcule : effectif, manquants, doublons, effectifs et fréquences par modalité, moyenne, médiane, minimum, maximum, étendue, et croisements (tableau de contingence) entre deux variables catégorielles. **Aucune bibliothèque externe, aucune écriture de fichier.** Chaque résultat porte un identifiant (`R1`, `R2`…) réutilisé par le modèle. |
| `analysis/numeric_guard.py` | Construit la **liste blanche numérique** (toutes les valeurs calculées + celles fournies par l'étudiant + les années et les effectifs déclarés), puis détecte tout nombre du texte produit qui n'y figure pas. Extrait les nombres avec leurs unités (« 62 % », « 3,4 »). |
| `analysis/results_rules.py` | Contrôles codés Q1–Q9 (voir § 10). |
| `schemas/inventory.py` | `Dataset` (nom, format, contenu, source, période, description), `ColumnProfile`, `Inventory` (variables, manquants, doublons, anomalies, analyses impossibles). |
| `schemas/analysis.py` | `Resultat` (identifiant, libellé, valeur, unité, effectif de référence, source du calcul), `ObjectifAnalyse`, `ExamenHypothese` (statut ∈ {soutenue, non_soutenue, non_examinable}), `AnalysisPlan`. |
| `schemas/interpretation.py` | `Lecture` (résultat → observation → objectif → interprétation prudente → limites → autres explications), `TableauDescription`, `FigureDescription`, `CompareLitterature`. |
| `schemas/draft.py` | `DraftSection` + `MethodologyDraft`-like `ResultsDraft`, avec le **statut** de chaque affirmation et la **synthèse pour l'étape 11**. |
| `storage/workspace.py` | Écrit aussi les **résultats calculés** (`computed_results.json`) : la traçabilité des calculs est un livrable. |

---

## 4. Flux des données

```
étudiant ── données (CSV/notes) ─┐
                                 ├─► input_controller → prerequisites → P1 inventaire
amont (1..9) ── méthodologie ────┘                     │
                                                       ▼
                                        MOTEUR (data_engine) : résultats CALCULÉS
                                                       │
                                          passés comme FAITS au modèle
                                                       ▼
                                       P2 plan + lecture → P3 interprétation → P4 rédaction
                                                       │
                          schema → business (S1–S6) → results_checks (Q1–Q9) → numeric_guard
                                                       │
                                             VÉRIFICATEUR (C1–C13)
                                                       │
                                       ┌───────────────┴───────────────┐
                                 corrections                    verdict verified
                                       └───────────────┬───────────────┘
                                          awaiting_human_validation
                                                       │
                                        décision étudiante (accepted/modified/refused)
                                                       │
                                          validated (posé par l'HUMAIN, jamais par l'agent)
```

Artefacts écrits sous `workspace/<student_id>/<session_id>/` : `inventory.json`, `dataset_profile.json`,
`computed_results.json`, `analysis.json`, `interpretation.json`, `results_draft.json`,
`results_output.json` et le journal `workspace/audit-resultats.db`. Aucune écriture hors de cet espace
(contrôle de traversée de chemin).

---

## 5. Modèle de données

| Objet | Clés principales | Règle |
|---|---|---|
| `Dataset` | `nom`, `format`, `contenu`, `source`, `periode`, `description`, `autorisation` | Le contenu reste une **donnée non fiable** ; il n'est jamais exécuté |
| `Inventory` | `datasets[]`, `variables[]`, `lignes`, `manquants`, `doublons`, `anomalies[]`, `analyses_impossibles[]` | Les anomalies sont **déclarées**, jamais corrigées en silence |
| `ComputedResults` | `resultats[]` (`id`, `libelle`, `valeur`, `unite`, `effectif`, `methode`, `source`) | Produit par le MOTEUR uniquement ; le modèle ne peut pas en ajouter |
| `Resultat` | `id_resultat` (référence obligatoire), `observation`, `objectif` | Un résultat affirmé sans référence à un calcul est refusé (Q4) |
| `ExamenHypothese` | `hypothese`, `statut` (soutenue / non_soutenue / non_examinable), `justification`, `resultats[]` | `soutenue` exige des résultats calculés ; `non_examinable` est une réponse valable |
| `Lecture` | `resultat`, `objectif`, `interpretation`, `limites[]`, `autres_explications[]` | Séparation stricte observation / interprétation (Q6) |
| `ResultsDraft` | `sections[]` (`titre`, `contenu`, `statut`), `synthese_pour_conclusion[]`, `elements_a_confirmer[]` | `synthese_pour_conclusion` alimente l'étape 11 |
| `Output` | dossier de preuve SPEC §16 + `status` + `document_status` + `computed_results` | Le contrat n'offre aucun champ « résultat » sans référence de calcul |

---

## 6. Contrat d'entrée (SPEC §6)

`schemas/input.py` — `ResultsAnalysisRequest` :

| Champ | Type | Rôle |
|---|---|---|
| `student_id`, `session_id` | `str` | Isolation |
| `subject_text`, `discipline`, `academic_level` | `str` | Contexte |
| `datasets` | `list[Dataset]` | **Les données réellement collectées** : CSV en texte, notes d'entretien, tableau saisi |
| `documents` | `list[DocumentCorpus]` | Pour une analyse documentaire : documents étudiés + notes d'extraction |
| `data_origin`, `data_period`, `collection_notes` | `str` | Provenance, période, conditions de collecte déclarées |
| `previous_answers`, `realise_preuves` | `list[str]` | Réponses et preuves fournies |
| `upstream_*` | `UpstreamPayload \| None` | Sujet, problème, littérature, problématique, question, objectifs, hypothèses, diagnostic, **méthodologie de l'étape 9** |

**Contrôle des amont** (leçons de la chaîne 1 → 9, appliquées d'emblée) : `is_verified` accepte
`validation.verified` (agents 1-4) ET `verification_result.verified` (agents 5-9) ; les champs sont lus
sous leur forme réelle ; les listes tolèrent les objets (`StrList`).
**La méthodologie de l'étape 9 est REQUISE et VALIDÉE** : sans elle, aucun traitement ni analyse ne peut
être justifié (SPEC §5, §6) ⇒ arrêt motivé sur `needs_clarification`.

---

## 7. Contrat de sortie (SPEC §16)

Dossier de preuve complet : identifiant du mémoire, version de la méthodologie utilisée, objectifs et
hypothèses examinés, **origine et version des données**, période et périmètre, transformations effectuées
et leur justification, méthodes et paramètres réellement utilisés, **résultats calculés** et éléments qui
les soutiennent, tableaux et figures produits, sources externes réellement consultées, anomalies et
données manquantes, interprétations proposées, résultat du vérificateur, remarques étudiant/encadreur,
historique des corrections, statut du document, date et version.

Interdit structurel : **aucun champ ne permet de saisir une donnée ou un résultat à la main** — les
résultats proviennent exclusivement du moteur déterministe.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mesure |
|---|---|
| LLM01 — Injection | Les données fournies et les notes de terrain sont balisées « non fiable » : un « Total : 999 » écrit dans un fichier de données n'est JAMAIS une instruction ni un résultat |
| LLM02 — Divulgation | Aucun secret dans les prompts ; clé LLM en environnement, jamais journalisée, jamais dans une URL |
| LLM03 — Chaîne d'approvisionnement | Moteur statistique **écrit sur place, stdlib uniquement** : aucune dépendance de calcul ajoutée |
| LLM04 — Empoisonnement | Les données ne sont pas « corrigées » : manquants, doublons et incohérences sont déclarés |
| LLM05 — Sortie non sûre | `LLM → Parser → Schema → Business → Security` |
| LLM06 — Agentivité excessive | Aucune action externe : `max_external_requests: 0` |
| LLM07 — Fuite de prompt | Prompt construit côté serveur ; testé |
| LLM08 — Embeddings | Aucun RAG |
| LLM09 — Désinformation | **Liste blanche numérique** (Q5) : un chiffre non calculé est détecté mécaniquement |
| LLM10 — Consommation | Bornes dures + garde anti-non-convergence |

Isolation : `workspace/<student_id>/<session_id>`, contrôle de traversée, aucune lecture croisée.
**Données personnelles** : les noms propres détectés dans les données sont signalés comme à anonymiser
(le journal et les artefacts ne recopient pas les données brutes au-delà du nécessaire).

---

## 9. Mécanisme de validation

```
schema_validation → business_validation (S1–S6) → results_checks (Q1–Q9)
                  → numeric_guard → security_validation → vérificateur (C1–C13)
```

| Code | Règle |
|---|---|
| S1 | Socle : données fournies + méthodologie validée de l'étape 9 présentes |
| S2 | Cohérence du statut de document (seul l'état final `valide` exige la vérification réussie) |
| S3 | Tout résultat affirmé référence un calcul réel (`id_resultat` existant) |
| S4 | Aucun chiffre du texte hors liste blanche numérique |
| S5 | Les données personnelles repérées sont signalées comme à anonymiser |
| S6 | Aucune auto-vérification ni auto-validation |

---

## 10. Mécanisme de vérification (SPEC §13)

Vérificateur indépendant (appel distinct, prompt dédié, sans accès aux décisions internes) :

| Contrôle | Objet |
|---|---|
| C1 | Les données analysées sont identifiables et leur provenance documentée |
| C2 | Les analyses respectent la méthodologie validée de l'étape 9, ou l'écart est expliqué |
| C3 | Les calculs et résultats sont retraçables (chaque résultat renvoie à un calcul) |
| C4 | Les tableaux et figures correspondent aux données (aucune valeur ajoutée) |
| C5 | Chaque analyse répond à un objectif ou une question pertinente |
| C6 | Les hypothèses ne sont examinées que si les données et la méthode le permettent |
| C7 | Les interprétations sont prudentes et justifiées, séparées des observations |
| C8 | Les résultats inattendus et contraires sont présentés fidèlement |
| C9 | Les limites et les données manquantes sont déclarées, jamais masquées |
| C10 | Les sources externes citées sont vérifiables (ou l'absence de source est assumée) |
| C11 | Aucune donnée, valeur ou citation n'est inventée |
| C12 | Les points non résolus sont signalés, et une synthèse exploitable existe pour l'étape 11 |
| C13 | Le document est compréhensible et scientifiquement rigoureux pour l'étudiant |

**Contrôles déterministes codés (Q1–Q9)** — le fond reste au vérificateur :

| Code | Contrôle |
|---|---|
| Q1 | Résultat affirmé sans référence à un calcul ⇒ refus |
| Q2 | Chiffre absent de la liste blanche numérique ⇒ refus (anti-invention) |
| Q3 | Hypothèse déclarée « soutenue » sans résultat calculé associé ⇒ refus |
| Q4 | Résultat déclaré « confirmé » alors que l'analyse ne le permet pas ⇒ refus |
| Q5 | Causalité affirmée sans dispositif (fenêtre de négation mesurée en mots — leçon M4/P7) ⇒ refus |
| Q6 | Observation et interprétation confondues dans le même champ ⇒ signalement |
| Q7 | Données manquantes / doublons non déclarés alors qu'ils existent ⇒ refus |
| Q8 | Citation attribuée à un participant ou à une source absente du corpus fourni ⇒ refus |
| Q9 | Conclusion générale rédigée (rôle de l'étape 11) ⇒ refus |

---

## 11. Stratégie de tests

| Fichier | Objet |
|---|---|
| `tests/resultats/test_resultats_01_moteur.py` | **Moteur déterministe** : calculs vérifiés à la main (effectifs, fréquences, moyenne, médiane, étendue, croisements, manquants, doublons) ; CSV malformé, colonne unique, valeurs non numériques |
| `tests/resultats/test_resultats_02_regles.py` | Q1–Q9, chacun éprouvé dans les deux sens (refuse ce qui est fautif, ne refuse pas ce qui est juste) |
| `tests/resultats/test_resultats_03_numeric_guard.py` | Liste blanche : un chiffre inventé est détecté, un chiffre calculé passe, les années et unités ne déclenchent pas de faux positif |
| `tests/resultats/test_resultats_04_campagne.py` | Campagne complète (LLM simulé) avec et sans données (chemin « plan d'analyse seulement ») |
| `tests/resultats/test_resultats_05_decision.py` | Portillon humain |
| `tests/resultats/test_resultats_06_securite.py` | Injection dans les données, secrets, fuite de prompt, isolation, anonymisation |
| `tests/resultats/test_resultats_07_api.py` | Routes HTTP |
| `tests/resultats/test_resultats_08_chaine_amont.py` | Passation depuis les sorties RÉELLES de la chaîne (méthodologie de l'étape 9) |
| `tests/resultats/test_resultats_09_passation_reelle.py` | Les pièges de passation (les deux clés de vérification, formes réelles, listes tolérantes) |

Puis **campagne réelle** : `scripts/e2e_chaine.py` étendu à l'étape 10, avec un jeu de données fourni
(« données de l'étudiant ») — jamais un résultat fabriqué : c'est l'ENTRÉE, l'agent n'en invente rien.

---

## 12. Dépendances

| Dépendance | État | Coût |
|---|---|---|
| `pydantic` (v2), `fastapi`, `uvicorn`, `httpx` | déjà installées | 0 € |
| Moteur statistique | **écrit sur place, stdlib uniquement** (`csv`, `statistics`, `collections`) | 0 € |
| Clé DeepSeek | déjà présente dans `~/.hermes/.env` | déjà budgétée |
| Réseau | aucun (`max_external_requests: 0`) | 0 € |

Aucune bibliothèque scientifique (numpy/pandas/scipy) n'est requise en V1 : les statistiques descriptives
et les croisements se calculent en bibliothèque standard, ce qui **réduit la surface de dépendance**.

---

## 13. Coûts éventuels

Une campagne nominale : **5 appels LLM** (P1 inventaire, P2 analyse, P3 interprétation, P4 rédaction,
vérificateur) plus re-tentatives et reformulations (borne `max_llm_calls: 22`). Un test statistique
inférentiel n'est PAS exécuté en V1 : l'agent recommande la méthode et déclare que le calcul relève de
l'étudiant, plutôt que d'implémenter des tests dont les conditions d'application seraient invérifiables.

---

## 14. Alternatives gratuites

| Besoin | Choix retenu (gratuit) | Alternatives écartées |
|---|---|---|
| Statistiques descriptives | moteur stdlib écrit sur place | pandas/scipy (dépendance lourde, non nécessaire) |
| Graphiques | **description** textuelle précise (titre, unités, données, lecture) | génération d'images (hors périmètre des agents, et source d'invention visuelle) |
| Modèle | DeepSeek `deepseek-flash` | API payantes (budget 0 €) |

---

## 15. Limites connues

1. **Aucun test inférentiel calculé en V1** : corrélation, régression et tests d'hypothèses sont
   *recommandés et conditionnés*, jamais exécutés — les conditions d'application ne peuvent pas être
   vérifiées par le programme seul.
2. **Pas de génération de graphiques** : l'agent décrit la figure (titre, variables, unités, lecture),
   l'étudiant produit l'image.
3. **Pas d'analyse de texte intégral d'entretiens en V1 au-delà du codage thématique** : le corpus
   qualitatif est traité par thèmes déclarés, avec extraits cités uniquement s'ils sont présents.
4. **La qualité des données est celle fournie** : l'agent détecte les manquants et les incohérences, il
   ne peut pas savoir si une valeur collectée est vraie.
5. **Un jeu de données volumineux n'est pas couvert** : le contenu fourni est borné par
   `max_input_size` (les très gros fichiers devront être agrégés en amont par l'étudiant).
6. **Le document reste un brouillon** tant que l'étudiant n'a pas validé : `validated` lui appartient.

---

## Décisions prises (portillon §42 — dérogation « autorisée d'avance »)

1. **Nom, emplacement, exposition** : `src/research_results_analysis_agent/`, API
   `POST /results/analyze`, port **8100** (`run-resultats.sh`), profil Hermes `agent-resultats`.
2. **Frontière avec l'étape 9** : l'agent 10 **suit** la méthodologie validée ; tout écart est déclaré
   (`ecarts_methodologie`), jamais appliqué en silence.
3. **Les chiffres viennent du code** : le modèle interprète, il ne calcule pas ; les résultats calculés
   sont persistés pour la traçabilité.
4. **Liste blanche numérique** (Q2) comme garantie anti-invention structurelle.
5. **Quatre étages LLM** (P1 inventaire, P2 analyse, P3 interprétation, P4 rédaction).
6. **Aucun test inférentiel exécuté en V1** ; recommandation et conditions déclarées.
7. **Réseau désactivé** (`max_external_requests: 0`).
8. **Absence de données ⇒ plan d'analyse seul**, jamais de résultats : c'est le chemin STOP de la SPEC.
9. **Synthèse pour l'étape 11** : champ dédié dans la sortie (contrat de passation 10 → 11).
10. **Anonymisation** : les données personnelles repérées sont signalées, jamais recopiées dans l'audit.

---

## État réel de l'implémentation

> **Implémenté, vérifié en exécution réelle** (architecture autorisée d'avance par le porteur).
> Paquet `src/research_results_analysis_agent/`, API `POST /results/analyze` (port 8100),
> profil Hermes `agent-resultats`, `config/settings-resultats.yaml`, `run-resultats.sh`.

### Tests hors réseau

`pytest -q` : **559 tests** au total, dont **62 pour l'étape 10** — moteur déterministe (calculs
vérifiés à la main : effectif, moyenne, médiane, étendue, fréquences, croisements, manquants,
doublons, séparateurs, virgule décimale, colonnes d'identification), garde numérique, contrôles
Q1–Q9 (chacun éprouvé dans les deux sens), campagne (avec et sans données), portillon humain,
sécurité (injection dans les données, anonymisation, isolation), API, passation depuis les sorties
réelles de la chaîne.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

| Passe | Statut | Vérificateur | Calculs | Appels LLM |
|---|---|---|---|---|
| 1 | échec (`S5`) | — | — | — |
| 2 | **`awaiting_human_validation`** | **`verified`** | **106 résultats calculés** | **6** |

Puis **décision étudiante sur la sortie réelle** : `accepted` → statut `validated`, document `valide`,
confiance 0,65 avec son calcul explicité, 6 points de synthèse transmis à l'étape 11.
**CHAÎNE 1 → 10 entièrement `verified`.**

### Correctifs issus de l'exécution réelle

1. **S5 trop stricte / mal ciblée** : la règle exigeait une mention d'anonymisation dès qu'une entrée
   figurait dans `donnees_personnelles` — y compris une entrée disant « aucune ». Corrigé : seules les
   entrées décrivant de VRAIES données identifiantes déclenchent la règle, et **la mesure
   d'anonymisation est désormais DÉCLARÉE par le programme** (défaut déterministe corrigé, pas laissé
   au modèle).
2. **Le vérificateur lisait des champs d'une autre étape** : `_student_block` hérité de l'étape 9
   appelait `request.country`, `request.field_access`, `request.realise_preuves`… inexistants ici
   (`AttributeError` à chaque campagne). Corrigé sur les champs réels de l'étape 10 + ajout des
   helpers manquants (`effective_problem`, `effective_problematic`).
3. **Colonnes d'identification** : `id`, `code`, `référence` recevaient une moyenne (bruit inutile et
   source de valeurs parasites). Exclues du calcul.
4. **Fréquences sans groupe** : les effectifs/fréquences par modalité ne renseignaient pas `groupe`,
   si bien qu'une modalité (« Abidjan ») n'était pas rattachable à sa valeur. Corrigé.

### Limites laissées assumées (signalées, non bloquantes)

- Aucun test inférentiel exécuté : l'agent recommande et conditionne, il ne calcule pas (les conditions
  d'application ne sont pas vérifiables par le programme seul).
- Les figures sont décrites (titre, variables, unités, lecture), pas produites.
- Le corpus qualitatif est traité par thèmes déclarés, avec extraits cités uniquement s'ils figurent
  mot pour mot dans les données fournies (contrôle Q8).
