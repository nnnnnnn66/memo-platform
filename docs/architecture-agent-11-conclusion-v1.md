# Architecture V1 — Agent Conclusion (`research_conclusion_agent` 1.0)

> Étape 11 (dernière du parcours). Architecture **publiée pour mémoire** (même méthode que l'étape 10).
> SPEC de référence : `docs/spec-agent-11-conclusion.md` (source de vérité).
> Fiche d'éléments : `docs/elements-agent-11-conclusion.md`.
> Prédécesseur : `docs/architecture-agent-10-resultats-analyse-v1.md`.

---

## 1. Architecture

### Position dans le parcours

```
[1] Sujet … [8] Diagnostic ─► [9] Méthodologie ─► [10] Résultats et analyse
   ─► [11] CONCLUSION (ce document) — fin du parcours
```

Paquet Python **autonome** `src/research_conclusion_agent/`, sur le même moule que les agents 1 à 10 :
configuration, bornes, client LLM, prompts, vérificateur, workspace et journal propres. **Aucun agent
existant n'est modifié.**

### Le principe qui gouverne tout : AUCUN RÉSULTAT NOUVEAU

La conclusion est l'étape où l'invention est la plus tentante : un modèle produit volontiers une
synthèse élégante en ajoutant « ce qui manque ». La défense est **structurelle** :

1. **Traçabilité obligatoire (K1)** : toute affirmation centrale cite l'identifiant du résultat de
   l'étape 10 qui la justifie ; une référence inexistante est refusée.
2. **Liste blanche numérique (K2)** : tout chiffre de la conclusion doit provenir des résultats
   CALCULÉS de l'étape 10 (moteur déterministe) ou des données du dossier. Un chiffre inventé est
   détecté mécaniquement.
3. **Sans résultats, pas de conclusion (K8)** : si aucun résultat vérifié n'est disponible, la
   production se limite à un **plan** et à la liste de ce qu'il faut recueillir.

### Ce que l'agent 11 est — et n'est pas

| L'agent 11 EST | L'agent 11 N'EST PAS |
|---|---|
| Un synthétiseur des résultats VÉRIFIÉS de l'étape 10 | Un producteur de résultats nouveaux |
| Un rédacteur de conclusion, avec la justification de chaque affirmation | Un générateur de texte élégant sans fondement |
| Un évaluateur honnête des objectifs et des hypothèses | Un avocat de la thèse : il ne « confirme » rien |
| Un expositeur des limites et des perspectives justifiées | Un inventeur de limites ou de pistes hors sujet |
| Un producteur d'un document que l'étudiant peut DÉFENDRE | Un décideur : `validated` vient de l'humain |

### Les trois étages internes + vérificateur

```
Entrée (dossier complet + résultats vérifiés de l'étape 10 + consignes)
   │
   ├─ P1 — Examen du dossier et synthèse scientifique
   │        disponible / manquant / incohérences ; résultats essentiels (R…) ;
   │        réponse à la question (avec étayage et portée) ; bilan des objectifs ;
   │        bilan des hypothèses REPRENANT le statut établi à l'étape 10
   │
   ├─ P2 — Plan de conclusion (rubriques, fonction de chacune, adaptation aux consignes)
   │
   ├─ P3 — Rédaction : sections (constat / interprétation / perspective), justification,
   │        apports, limites, perspectives, points à confirmer
   │
   └─ Contrôles K1–K9 → validations T1–T6 → sécurité
        → VÉRIFICATEUR indépendant (C1–C13) → PORTILLON HUMAIN
```

Pipeline de sécurité imposé partout : `LLM → Parser → Schema → Business → Security`.

---

## 2. Arborescence des fichiers

```
src/research_conclusion_agent/
├── __init__.py  main.py  api/routes.py
├── core/        config.py  limits.py  errors.py  logging.py  security_rules.py  sessions.py
├── llm/         client.py
│   └── prompts/ p1_synthesis_system.md  p2_plan_system.md  p3_writing_system.md
│                verifier_system.md
├── analysis/    conclusion_rules.py (K1–K9)  numeric_guard.py (liste blanche, K2)
├── pipeline/    campaign.py  prerequisites.py  input_controller.py  input_validation.py
│                synthesis_stage.py (P1)  plan_stage.py (P2)  writing_stage.py (P3)
│                conclusion_checks.py  business_validation.py (T1–T6)
│                schema_validation.py  security_layer.py  security_validation.py
│                verifier.py  decision_stage.py  llm_stage.py  output_parser.py
├── schemas/     common.py  input.py  synthesis.py  plan.py  draft.py  stages.py
│                decision.py  verifier.py  output.py
└── storage/     workspace.py  audit.py

config/settings-conclusion.yaml     # configuration propre
run-conclusion.sh                   # service (port 8110, bind 127.0.0.1)
tests/conclusion/                   # suite hors réseau
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `analysis/conclusion_rules.py` | Contrôles codés **K1–K9** : traçabilité, liste blanche numérique, cohérence des statuts d'hypothèse avec l'étape 10, causalité (fenêtre de négation mesurée en mots), hypothèse « confirmée », référence bibliographique absente du dossier, confusion constat/interprétation/perspective, conclusion rédigée sans résultats, résultat inexistant retenu. |
| `schemas/synthesis.py` | `Synthesis` : disponibilité, incohérences, résultats essentiels, `ReponseQuestion` (réponse + étayage + portée), `BilanObjectif` (statut atteint / partiellement / non atteint / non évalué), `BilanHypothese` (statut soutenue / non soutenue / non examinable). |
| `schemas/draft.py` | `DraftSection` avec **`niveau`** (`constat`, `interpretation`, `perspective`), `justification` obligatoire et `resultats` (identifiants cités) ; `ConclusionDraft` (apports, limites, perspectives, points à confirmer). |
| `pipeline/synthesis_stage.py` | P1 : examine le dossier, ne retient que ce qui existe, et répond à la question **dans les limites des données**. |
| `pipeline/writing_stage.py` | P3 : rédige en distinguant constat / interprétation / perspective, avec la justification de chaque affirmation. |
| `storage/audit.py` | Journal filtré (compteurs et statuts, **aucun contenu de conclusion ni donnée personnelle**). |

---

## 4. Flux des données

```
amont (1..10) ──► input_controller → prerequisites (résultats vérifiés ?) → P1 synthèse
                                                                              │
                                                              P2 plan ◄───────┘
                                                                              │
                                                              P3 rédaction ◄──┘
                                                                              │
                    schema → business (T1–T6) → conclusion_checks (K1–K9) → sécurité
                                                                              │
                                                        VÉRIFICATEUR (C1–C13)
                                                                              │
                                                      awaiting_human_validation
                                                                              │
                                  décision étudiante (accepted/modified/refused)
                                                                              │
                                          validated (posé par l'HUMAIN, jamais par l'agent)
```

Artefacts : `conclusion_draft.json`, `conclusion_output.json`, `conclusion_request.json` sous
`workspace/<student_id>/<session_id>/`, + journal `workspace/audit-conclusion.db`.

---

## 5. Modèle de données

| Objet | Clés principales | Règle |
|---|---|---|
| `Synthesis` | `elements_disponibles`, `elements_manquants`, `incoherences`, `resultats_essentiels`, `reponse_question`, `bilan_objectifs`, `bilan_hypotheses`, `plan_seulement` | Un statut d'hypothèse ne peut pas contredire l'étape 10 (K3) |
| `ReponseQuestion` | `question`, `reponse`, `etayage[]`, `portee` | `etayage` = identifiants réels ; `portee` dit ce que la réponse permet ET ne permet pas |
| `BilanObjectif` | `objectif`, `statut`, `resultats[]`, `commentaire` | « non évalué » est une réponse honnête |
| `ConclusionPlan` | `sections[]` (`titre`, `fonction`, `contenu_prevu`, `retenue`), `rubriques_ecartees`, `adaptation_consignes` | `fonction` obligatoire (à quoi sert la rubrique) |
| `ConclusionDraft` | `sections[]` (`niveau`, `justification`, `resultats[]`), `apports_*`, `limites`, `perspectives`, `points_a_confirmer` | `justification` obligatoire ; `niveau` distingue constat / interprétation / perspective |
| `ConclusionOutput` | dossier de preuve SPEC §16 + `status` + `document_status` | Aucun champ pour un résultat nouveau |

---

## 6. Contrat d'entrée (SPEC §6)

`ConclusionRequest` : identification, contexte, consignes (établissement / directeur — **données non
fiables**), commentaires de l'étudiant, et les sorties amont vérifiées, dont **`upstream_results`
(étape 10)**.

- `is_verified` accepte `validation.verified` (étapes 1-4) ET `verification_result.verified`
  (étapes 5-10) ; `verified: false` est toujours refusé.
- **Les résultats de l'étape 10 sont REQUIS et VALIDÉS** (statut `valide` ou
  `en_attente_de_validation`) ⇒ sinon `needs_clarification`.
- Les champs sont lus sous leur **forme réellement produite** (`computed_results.resultats[].id`,
  `plan.hypotheses[].statut`, `synthese_pour_conclusion`) ; les listes tolèrent les objets (`StrList`).

---

## 7. Contrat de sortie (SPEC §16)

Dossier de preuve : identifiant du mémoire, version des éléments consultés, question et objectifs
utilisés, **références des résultats utilisés** (`R…`), plan, brouillon et versions, affirmations
importantes et leur justification, lacunes et incohérences, corrections effectuées, rapport du
vérificateur, décisions de l'étudiant, statut final.

Interdit structurel : **aucun champ ne permet d'introduire un nouveau résultat** ; les seules valeurs
chiffrées admises proviennent des calculs de l'étape 10.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mesure |
|---|---|
| LLM01 — Injection | Consignes et commentaires balisés « non fiable » ; un document importé n'est jamais une instruction (SPEC §7.5, §10.12) |
| LLM02 — Divulgation | Aucun secret dans les prompts ; clé LLM en environnement, jamais journalisée ni dans une URL |
| LLM03 — Chaîne d'approvisionnement | Dépendances déjà présentes ; budget 0 € |
| LLM04 — Empoisonnement | Les résultats ne sont acceptés que VÉRIFIÉS ; une incohérence est signalée, jamais absorbée |
| LLM05 — Sortie non sûre | `LLM → Parser → Schema → Business → Security` |
| LLM06 — Agentivité excessive | Aucune action externe : `max_external_requests: 0` |
| LLM07 — Fuite de prompt | Prompt construit côté serveur ; testé |
| LLM08 — Embeddings | Aucun RAG |
| LLM09 — Désinformation | Traçabilité (K1) + liste blanche numérique (K2) + interdiction de « confirmer » une hypothèse (K5) |
| LLM10 — Consommation | Bornes dures + garde anti-non-convergence |
| **Confidentialité** | **Aucune donnée personnelle** (courriel, téléphone, nom) ne doit figurer dans la conclusion (contrôle T4) ; le journal ne recopie aucun contenu |

Isolation : `workspace/<student_id>/<session_id>`, contrôle de traversée de chemin.

---

## 9. Mécanisme de validation

```
schema_validation → business_validation (T1–T6) → conclusion_checks (K1–K9)
                  → security_validation → vérificateur (C1–C13)
```

| Code | Règle |
|---|---|
| T1 | Socle : question de recherche + résultats vérifiés de l'étape 10 |
| T2 | Cohérence des statuts (document « validé » ⇒ vérification réussie ET décision humaine) |
| T3 | Un bilan des objectifs (ou un manque déclaré) doit exister |
| T4 | Aucune donnée personnelle reproduite |
| T5 | Le statut « vérifié » ne peut venir que du vérificateur |
| T6 | Aucune auto-vérification ni auto-validation |

---

## 10. Mécanisme de vérification (SPEC §13)

| Contrôle | Objet |
|---|---|
| C1 | La conclusion répond à la question DANS les limites des résultats |
| C2 | Les principaux résultats sont correctement synthétisés (sans trahison ni exagération) |
| C3 | Chaque affirmation centrale est traçable (renvoi à un résultat de l'étape 10) |
| C4 | Aucun résultat nouveau, aucun chiffre venu d'ailleurs |
| C5 | Les objectifs sont examinés explicitement |
| C6 | Les hypothèses sont traitées seulement si elles existent et sont évaluables |
| C7 | Les apports sont fondés sur le travail réel |
| C8 | Les limites sont réalistes et pertinentes |
| C9 | Les perspectives découlent des résultats ou des limites |
| C10 | Aucune causalité non permise ; aucune hypothèse « confirmée » |
| C11 | Aucune donnée, citation ou référence inventée ; aucune donnée personnelle |
| C12 | Incohérences signalées, points à confirmer explicites |
| C13 | L'étudiant peut comprendre et défendre le contenu |

**Boucle** : la DERNIÈRE reformulation est rejugée ; non-convergence (mêmes corrections deux fois)
⇒ arrêt déclaré. **Portillon humain** : `validated` ne vient que de la décision étudiante.

---

## 11. Stratégie de tests

| Fichier | Objet |
|---|---|
| `test_conclusion_01_regles.py` | K1–K9, chacun éprouvé dans les deux sens |
| `test_conclusion_02_campagne.py` | Campagne complète, avec et sans résultats (plan seul), chiffre inventé, hypothèse non examinable |
| `test_conclusion_03_decision.py` | Portillon humain |
| `test_conclusion_04_securite.py` | Injection, secrets, **données personnelles refusées**, isolation, résultats non vérifiés |
| `test_conclusion_05_api.py` | Routes HTTP |
| `test_conclusion_06_chaine_amont.py` | Passation depuis les sorties RÉELLES de la chaîne |

Puis **campagne réelle** : `scripts/e2e_chaine.py depuis=11`.

---

## 12. Dépendances

| Dépendance | État | Coût |
|---|---|---|
| `pydantic` (v2), `fastapi`, `uvicorn`, `httpx` | déjà installées | 0 € |
| Clé DeepSeek | déjà présente dans `~/.hermes/.env` | déjà budgétée |
| Réseau | **aucun** (`max_external_requests: 0`) | 0 € |

---

## 13. Coûts éventuels

Une campagne nominale : **4 appels LLM** (P1 synthèse, P2 plan, P3 rédaction, vérificateur) plus
re-tentatives et reformulations (borne `max_llm_calls: 20`). Aucun service payant.

---

## 14. Alternatives gratuites

| Besoin | Choix retenu (gratuit) | Alternatives écartées |
|---|---|---|
| Modèle | DeepSeek `deepseek-flash` | API payantes (budget 0 €) |
| Comparaison de versions | historique interne (`historique_versions`, `corrections_effectuees`) | outil de diff externe |
| Sources | dossier des étapes précédentes uniquement | recherche en ligne (hors V1, et source d'invention) |

---

## 15. Limites connues

1. **La conclusion ne peut pas dépasser les résultats** : si les résultats sont descriptifs, la
   conclusion reste descriptive — c'est voulu (SPEC §10.4, §13).
2. **L'appréciation de la « qualité rédactionnelle »** relève de l'humain : l'agent garantit la
   traçabilité et l'honnêteté, pas l'élégance.
3. **Les consignes d'établissement sont inconnues par défaut** : sans consignes, la structure suit les
   usages courants et **c'est déclaré**.
4. **Aucune référence bibliographique nouvelle** n'est produite : seules celles du dossier peuvent
   apparaître.
5. **Le document reste un brouillon** tant que l'étudiant n'a pas validé.
6. **La comparaison de versions** se limite à l'historique des reformulations de cette exécution.

---

## Décisions prises

1. **Nom, emplacement, exposition** : `src/research_conclusion_agent/`, API `POST /conclusion/write`,
   port **8110** (`run-conclusion.sh`), profil Hermes `agent-conclusion`.
2. **Frontière avec l'étape 10** : la conclusion SUIT les résultats vérifiés ; toute incohérence est
   SIGNALÉE (`incoherences`), jamais corrigée en silence.
3. **Trois étages LLM** (P1 synthèse, P2 plan, P3 rédaction) + vérificateur.
4. **Traçabilité obligatoire** (K1) et **liste blanche numérique** (K2) comme garanties structurelles.
5. **Statut d'hypothèse repris de l'étape 10** ; « non examinable » est une réponse juste (K3, C6).
6. **Réseau désactivé** ; aucune référence bibliographique nouvelle.
7. **Sans résultat vérifié ⇒ plan seulement** (K8), document en brouillon.
8. **Confidentialité** : aucune donnée personnelle dans la conclusion (T4).
9. **Statuts de document** : brouillon, à corriger, vérifié, en attente de validation, validé,
   à réviser.

---

## État réel de l'implémentation

> **Implémenté, vérifié en exécution réelle.** Paquet `src/research_conclusion_agent/`, API
> `POST /conclusion/write` (port 8110), profil Hermes `agent-conclusion`,
> `config/settings-conclusion.yaml`, `run-conclusion.sh`.

### Tests hors réseau

`pytest -q` : **608 tests** au total, dont **49 pour l'étape 11** — contrôles K1–K9 (chacun éprouvé
dans les deux sens), campagne complète avec et sans résultats, portillon humain, sécurité (injection,
**données personnelles refusées**, résultats non vérifiés inutilisables), API, passation depuis les
sorties réelles de la chaîne.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

| Passe | Statut | Vérificateur | Résultats cités | Sections | Appels LLM |
|---|---|---|---|---|---|
| 1 | **`awaiting_human_validation`** | **`verified`** | **22** | **7** | **4** |

Puis **décision étudiante sur la sortie réelle** : `accepted` → statut `validated`, document `valide`,
confiance 0,65 avec son calcul explicité, 12 résultats de l'étape 10 retenus dans la synthèse.
**CHAÎNE 1 → 11 entièrement `verified` — parcours complet, du sujet à la conclusion.**

### Défauts déterministes corrigés avant la campagne

1. **`references` est un mot réservé SQLite** : la colonne du journal d'audit faisait échouer
   l'initialisation de la base (`syntax error`). Renommée `references_resultats`.
2. **Les violations de la garde numérique sortaient préfixées « Q2 »** (héritage de l'étape 10) au
   lieu de « K2 » : le contrôle était bien appliqué, mais son code ne correspondait pas à l'étape.
3. **La détection des citations porte sur le texte NON mis en minuscules** : une référence commence
   par une majuscule, et le contrôle K6 ne pouvait pas la voir sur le texte normalisé.

### Limites laissées assumées (signalées, non bloquantes)

- Une conclusion descriptive ne peut pas dépasser des résultats descriptifs : c'est le comportement
  voulu, et il est déclaré dans `portee` et dans les limites.
- L'appréciation de l'élégance rédactionnelle relève de l'humain ; l'agent garantit la traçabilité et
  l'honnêteté.
- Aucune référence bibliographique nouvelle n'est produite : seules celles du dossier peuvent
  apparaître (K6).
