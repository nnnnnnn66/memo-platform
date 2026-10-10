# Architecture V1 — Agent 13 : Vérificateur global de cohérence (`research_coherence_verifier` 1.0)

> Architecture en 15 points. **Portillon 42 — autorisation d'avance du porteur** : l'architecture est
> publiée pour mémoire, l'implémentation se poursuit sans arrêt de validation.
> SPEC de référence : `docs/spec-agent-13-verificateur-coherence.md` (source de vérité).
> Fiche d'éléments : `docs/elements-agent-13-verificateur-coherence.md`.
> Prédécesseurs : `docs/architecture-agent-11-conclusion-v1.md`.

---

## 1. Architecture

### Position dans le parcours

```
[1] Sujet … [10] Résultats et analyse ─► [11] CONCLUSION
                                             │
                                             ▼
                            [13] VÉRIFICATEUR GLOBAL DE COHÉRENCE
                                 (audit transversal du dossier complet)
                                             │
                                  rapport d'audit + portée déclarée
                                             ▼
                              étudiant / directeur de mémoire
```

Étape 12 : **réservée, non attribuée** ; la numérotation du porteur place le vérificateur global en
étape 13.

Le dossier étant complet, cet agent ne se place pas « après l'étape 11 » comme un maillon qui produit :
il se place **au-dessus** du dossier, qu'il confronte à lui-même.

### Le problème que résout cet agent

Chaque agent vérifie SA sortie. Personne ne vérifie **l'enchaînement**. Or les défauts les plus coûteux
d'un mémoire sont transversaux : une question qui ne découle pas de la problématique, un objectif sans
résultat, une hypothèse que la méthodologie ne peut pas examiner, une conclusion qui affirme plus que
les résultats, un sujet recopié dans la problématique.

### Les trois principes de conception

1. **Le programme établit les FAITS, le modèle juge les LIENS.** Ce qui est confrontable mécaniquement
   (présence, couverture, traçabilité, identité des textes, statuts) est calculé en Python : ce sont des
   **constats objectivés** (X1–X12). Le modèle ne sert que là où il faut comprendre (découlement,
   adéquation, fidélité sémantique).
2. **Aucun constat sans preuve.** Tout constat cite les éléments réels du dossier qui le fondent. Un
   constat sans preuve est refusé par le programme.
3. **La portée est déclarée.** Chaque rapport dit ce qui N'A PAS pu être vérifié — portée statique
   (ce qui échappe par nature à un audit sur dossier) + portée dynamique (les liens rendus inexplorables
   par une étape absente).

### Ce que l'agent est — et n'est pas

| L'agent 13 EST | L'agent 13 N'EST PAS |
|---|---|
| Un auditeur de l'ENCHAÎNEMENT | Un producteur de contenu du mémoire |
| Un évaluateur hiérarchisé (bloqueur / majeur / mineur) | Un juge du style ou de l'orthographe |
| Un révélateur de contradictions et de fusions | Un correcteur des étapes validées |
| Un énonciateur honnête de sa propre portée | Un certificateur de la véracité du terrain |
| Un producteur de constats motivés et actionnables | Un fabricant d'impressions générales |

### Les étages internes

```
Entrée : dossier complet (étapes 1 → 11) + consignes éventuelles
   │
   ├─ 0. Déterministe — état de complétude du dossier (présence, vérification, validation)
   │
   ├─ 1. Déterministe — FAITS transversaux X1–X12 (aucun modèle sollicité)
   │
   ├─ P1 — Audit transversal (LLM) : liens sémantiques ; confirmation, nuance, infirmation
   │        des constats déterministes ; constats supplémentaires motivés
   │
   ├─ P2 — Rapport (LLM) : synthèse, constats hiérarchisés, recommandations, PORTÉE déclarée
   │
   └─ Contrôles X1–X12 (re-vérifiés sur la sortie) → validations T1–T6 → sécurité
        → CONTRÔLEUR DE L'AUDIT (C1–C13) → PORTILLON HUMAIN
```

Pipeline imposé partout : `LLM → Parser → Schema → Business → Security`.

---

## 2. Arborescence des fichiers

```
src/research_coherence_verifier/
├── __init__.py  main.py  api/routes.py
├── core/        config.py  limits.py  errors.py  logging.py  security_rules.py  sessions.py
├── llm/         client.py
│   └── prompts/ p1_audit_system.md  p2_report_system.md  verifier_system.md
├── analysis/    coherence_rules.py (X1–X12)  fusion.py  numeric_guard.py  scope.py (portée)
├── pipeline/    campaign.py  prerequisites.py  input_controller.py  input_validation.py
│                dossier_stage.py (état de complétude)  facts_stage.py (X1–X12)
│                audit_stage.py (P1)  report_stage.py (P2)
│                coherence_checks.py  business_validation.py (T1–T6)
│                schema_validation.py  security_layer.py  security_validation.py
│                verifier.py  decision_stage.py  llm_stage.py  output_parser.py
├── schemas/     common.py  input.py  audit.py  report.py  stages.py
│                decision.py  verifier.py  output.py
└── storage/     workspace.py  audit.py

config/settings-coherence.yaml      # configuration propre
run-coherence.sh                    # service (port 8130, bind 127.0.0.1)
tests/coherence/                    # suite hors réseau
```

---

## 3. Rôle de chaque fichier

| Fichier | Rôle |
|---|---|
| `analysis/coherence_rules.py` | Les **faits transversaux X1–X12** : complétude, question absente, fusion sujet/problème/problématique, objectifs absents, objectifs sans service de la question, hypothèses contredisant la décision de l'étape 7, **hypothèses examinables par la méthodologie**, objectifs non couverts par les résultats, **références orphelines de la conclusion**, résultats ignorés par la conclusion, contradiction de statut d'hypothèse entre étapes 10 et 11, étape « vérifiée » au contenu vide. |
| `analysis/fusion.py` | Détection des **éléments fusionnés à tort** : identité ou quasi-identité de deux textes (normalisation, recouvrement de tokens, seuil). Distingue « recopié » de « même thème ». |
| `analysis/scope.py` | **Portée de l'audit** : liste statique des éléments non vérifiables par nature + limites dynamiques (étape absente ⇒ liens inexplorables). |
| `schemas/audit.py` | `Finding` (code, axe, sévérité, éléments concernés, preuve, recommandation, origine déterministe/LLM, statut confirmé/nuancé/infirmé), `ElementNonVerifiable`. |
| `schemas/report.py` | Rapport : synthèse, constats, recommandations, portée, verdict global. |
| `pipeline/facts_stage.py` | Exécute X1–X12 et fige les faits AVANT tout appel de modèle. |
| `pipeline/audit_stage.py` | P1 : audit sémantique, à partir des faits établis (le modèle ne peut pas supprimer un fait, seulement le nuancer en le motivant). |
| `pipeline/report_stage.py` | P2 : rédige le rapport et **déclare la portée** (obligatoire, contrôlé). |
| `pipeline/verifier.py` | Contrôleur de l'audit : chaque constat est-il fondé ? la sévérité est-elle justifiée ? la portée est-elle déclarée ? |
| `storage/audit.py` | Journal filtré (compteurs, statuts, verdict ; aucun contenu du dossier). |

---

## 4. Flux des données

```
dossier 1..11 ─► input_controller ─► prerequisites (≥ 2 étapes exploitables, sujet & question ?)
                                        │
                       dossier_stage ───┤ (complétude, statuts)
                                        │
                       facts_stage ─────┤ (X1–X12 : FAITS, aucun LLM)
                                        │
                       audit_stage ─────┤ (P1 : liens sémantiques, constats consolidés)
                                        │
                       report_stage ────┤ (P2 : rapport + portée déclarée)
                                        │
        schema → business (T1–T6) → coherence_checks (X1–X12 rejoués) → sécurité
                                        │
                        CONTRÔLEUR DE L'AUDIT (C1–C13)
                                        │
                          awaiting_human_validation
                                        │
                   décision étudiante (accepted / modified / refused)
                                        │
                    validated (posé par l'HUMAIN, jamais par l'agent)
```

Artefacts : `coherence_request.json`, `coherence_facts.json`, `coherence_audit.json`,
`coherence_report.json` sous `workspace/<student_id>/<session_id>/`, + `workspace/audit-coherence.db`.

---

## 5. Modèle de données

| Objet | Clés principales | Règle |
|---|---|---|
| `Finding` | `code` (X…), `axe`, `severite` (bloqueur/majeur/mineur), `elements` (étapes concernées), `constat`, `preuve`, `recommandation`, `origine` (deterministe/llm), `suite` (confirme/nuance/infirme) | **Sans `preuve` non vide, le constat est refusé** |
| `ElementNonVerifiable` | `element`, `raison`, `portee` (statique/dynamique) | La portée ne peut pas être vide dans un rapport |
| `CoherenceReport` | `synthese`, `constats[]`, `non_verifiable[]`, `recommandations[]`, `verdict` | `verdict` ∈ {cohérent, cohérent_avec_réserves, incohérent} |
| `DossierState` | étapes présentes, vérifiées, validées ; éléments manquants | Sert de socle aux faits |
| `AuditOutput` | constats consolidés + faits rejoués | Aucun constat ne peut CONTREDIRE un fait déterministe sans motivation |

**Verdict déterministe** (calculé par le programme, pas par le modèle) :

| Condition | Verdict |
|---|---|
| au moins un **bloqueur** | `incoherent` |
| au moins un **majeur** (et aucun bloqueur) | `coherent_avec_reserves` |
| seulement des **mineurs** ou aucun constat | `coherent` |

---

## 6. Contrat d'entrée

`CoherenceRequest` : identification, consignes éventuelles (données non fiables), et le **dossier
complet** : `upstream_subject` (1), `upstream_problem` (2), `upstream_literature` (3),
`upstream_problematic` (4), `upstream_question` (5), `upstream_objectives` (6),
`upstream_hypotheses` (7), `upstream_methodology_diagnostic` (8), `upstream_methodology` (9),
`upstream_results` (10), `upstream_conclusion` (11).

- `is_verified` accepte `validation.verified` (étapes 1-4) ET `verification_result.verified`
  (étapes 5-11).
- Éléments de service extraits des sorties réelles : `main_research_question`, `validated_problematic`,
  `identified_problem.statement`, `general_objective`, `specific_objectives`,
  `research_hypotheses[].formulation`, `protocol.{approche,type_recherche,strategie}`,
  `plan.{objectifs_couverts,objectifs_non_couverts,hypotheses[].statut}`,
  `computed_results.resultats[].{id,valeur}`, `conclusion.synthesis.bilan_hypotheses[].statut`,
  `conclusion.references_resultats`.

---

## 7. Contrat de sortie (SPEC §16)

Dossier de preuve : identifiant du dossier et de l'exécution ; version des éléments consultés ; étapes
présentes et leur statut ; faits transversaux X1–X12 ; constats consolidés (preuve + sévérité) ;
constats **retirés ou reclassés** et pourquoi ; **liste des éléments non vérifiables** ;
recommandations ; rapport du contrôleur ; décision de l'étudiant ; statut final.

**Aucun champ ne permet d'écrire dans une étape du dossier.**

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mesure |
|---|---|
| LLM01 — Injection | Toutes les sorties d'agents balisées « non fiable » : un dossier n'est jamais un jeu d'instructions |
| LLM02 — Divulgation | Aucun secret dans les prompts ; clé LLM en environnement |
| LLM04 — Empoisonnement | Les éléments ne sont jamais absorbés : ils sont confrontés ; une contradiction est signalée |
| LLM05 — Sortie non sûre | `LLM → Parser → Schema → Business → Security` |
| LLM06 — Agentivité excessive | Aucune action externe ; `max_external_requests: 0` ; aucune écriture dans le dossier |
| LLM07 — Fuite de prompt | Prompts construits côté serveur ; testés |
| LLM09 — Désinformation | **Aucun constat sans preuve** ; sévérité justifiée ; portée déclarée |
| LLM10 — Consommation | Bornes dures + garde anti-non-convergence |
| Confidentialité | Aucune donnée personnelle recopiée dans le rapport (contrôle T4) |

Isolation : `workspace/<student_id>/<session_id>`, contrôle de traversée de chemin.

---

## 9. Mécanisme de validation

| Code | Règle |
|---|---|
| T1 | Socle : au moins deux étapes exploitables, sujet et question connus |
| T2 | Cohérence des statuts (rapport « validé » ⇒ contrôle réussi ET décision humaine) |
| T3 | Chaque constat porte une preuve et une recommandation ; les sévérités sont dans la grille |
| T4 | Aucune donnée personnelle reproduite ; aucune écriture dans les étapes du dossier |
| T5 | Le statut « contrôlé » ne peut venir que du contrôleur |
| T6 | Aucune auto-validation : `validated` vient de l'étudiant |

---

## 10. Mécanisme de vérification (contrôleur de l'audit)

| Contrôle | Objet |
|---|---|
| C1 | Chaque constat est FONDÉ : sa preuve existe réellement dans le dossier |
| C2 | Aucun constat inventé (rien qui ne soit dans le dossier) |
| C3 | La sévérité est justifiée (une fragilité n'est pas annoncée comme rupture) |
| C4 | Aucun fait déterministe n'a été supprimé sans motivation |
| C5 | Les fusions abusives signalées sont réelles (textes effectivement identiques ou recopiés) |
| C6 | Les contradictions signalées sont réelles (les deux affirmations coexistent) |
| C7 | La **portée est déclarée** et couvre les non-vérifiables attendus |
| C8 | Les recommandations sont actionnables et rattachées à leur constat |
| C9 | Aucun jugement hors compétence (style, plagiat, éthique de terrain, règles locales non fournies) |
| C10 | Aucune étape du dossier n'est modifiée ni proposée comme « corrigée d'office » |
| C11 | Le verdict correspond bien à la grille (bloqueur ⇒ incohérent, etc.) |
| C12 | L'étudiant peut comprendre chaque constat et le vérifier lui-même |
| C13 | Aucune donnée personnelle, aucun secret dans le rapport |

**Boucle** : la dernière reformulation est rejugée ; non-convergence ⇒ arrêt déclaré.
**Portillon humain** : `validated` ne vient que de la décision étudiante.

---

## 11. Stratégie de tests

| Fichier | Objet |
|---|---|
| `test_coherence_01_regles.py` | X1–X12, chacun éprouvé dans les deux sens (fusion détectée / textes distincts non signalés, etc.) |
| `test_coherence_02_campagne.py` | Audit complet d'un dossier cohérent et d'un dossier incohérent ; verdict déterministe |
| `test_coherence_03_decision.py` | Portillon humain |
| `test_coherence_04_securite.py` | Injection, secrets, données personnelles, **aucune écriture dans le dossier**, isolation |
| `test_coherence_05_api.py` | Routes HTTP |
| `test_coherence_06_dossier_reel.py` | Audit du dossier RÉEL de la chaîne 1 → 11 |

Puis **campagne réelle** : `scripts/e2e_chaine.py depuis=11` puis audit du dossier complet.

---

## 12. Dépendances

| Dépendance | État | Coût |
|---|---|---|
| `pydantic` v2, `fastapi`, `uvicorn`, `httpx` | déjà installées | 0 € |
| Clé DeepSeek | déjà présente dans `~/.hermes/.env` | déjà budgétée |
| Réseau | **aucun** (`max_external_requests: 0`) | 0 € |

---

## 13. Coûts éventuels

Audit nominal : **3 appels LLM** (P1 audit transversal, P2 rapport, contrôleur) plus re-tentatives
(borne `max_llm_calls: 14`). Aucun service payant.

---

## 14. Alternatives gratuites

| Besoin | Choix retenu | Alternatives écartées |
|---|---|---|
| Confrontation des textes | comparaison de tokens normalisés (stdlib) | embeddings (payants/complexes) |
| Détection des liens | moteur déterministe + LLM pour le sémantique | LLM seul (moins fiable, plus coûteux) |
| Modèle | DeepSeek `deepseek-flash` | API payantes (budget 0 €) |

---

## 15. Limites connues

1. **La véracité du terrain est hors de portée** : le dossier ne prouve pas que les données ont été
   réellement recueillies. L'agent le DÉCLARE.
2. **L'exactitude des sources citées** n'est pas vérifiable sans accès à leur contenu réel.
3. **Le plagiat et le style** ne sont pas jugés.
4. **La conformité aux règles locales** n'est examinée que si les consignes sont fournies.
5. **L'audit est relatif au dossier transmis** : une étape absente rend inexplorables les liens qui en
   dépendent (déclaré en portée dynamique).
6. **La détection de fusion est lexicale** : deux textes reformulés en profondeur peuvent échapper au
   programme — le modèle peut alors les signaler, avec preuve.
7. **Le verdict global est un indicateur**, pas une décision : l'arbitrage appartient à l'étudiant et à
   son directeur de mémoire.

---

## Décisions prises

1. **Nom, emplacement, exposition** : `src/research_coherence_verifier/`, API `POST /coherence/audit`,
   port **8130** (`run-coherence.sh`), profil Hermes `agent-coherence`.
2. **Le programme établit les faits, le modèle juge les liens** : X1–X12 en Python, puis audit LLM.
3. **Aucun constat sans preuve** : refusé par le programme, contrôlé par le contrôleur (C1, C2).
4. **Hiérarchie imposée** : bloqueur / majeur / mineur ; verdict global déterministe.
5. **Portée obligatoire** : statique (par nature) + dynamique (étapes absentes) dans chaque rapport.
6. **Aucune écriture dans les étapes** : l'agent signale, ne corrige jamais.
7. **Contrôle de l'audit** par un contrôleur indépendant (C1–C13) avant le portillon humain.
8. **Réseau désactivé** ; aucune donnée personnelle dans le rapport.

---

## État réel de l'implémentation

> **Implémenté et vérifié en exécution réelle.** Paquet `src/research_coherence_verifier/`, API
> `POST /coherence/audit` (port 8130), profil Hermes `agent-coherence`,
> `config/settings-coherence.yaml`, `run-coherence.sh`.

### Tests hors réseau

`pytest -q` : **688 tests** au total, dont **70 pour l'étape 13** — faits X1–X12 (chacun éprouvé dans
les deux sens), audit complet sur dossier cohérent et sur dossiers rompus, portillon humain, sécurité
(injection, **aucune écriture dans le dossier**, données personnelles), API, **dossier réel**, et
l'intégrité du digest envoyé au modèle.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

Audit du dossier produit par la chaîne 1 → 11 (`scripts/audit_coherence.py`, réseau désactivé) :

| Mesure | Valeur |
|---|---|
| Statut | **`awaiting_human_validation`** → décision étudiante `accepted` → **`validated`** |
| Contrôleur de l'audit | **`verified`** (1 passe) |
| Verdict global | **`coherent_avec_reserves`** — 0 bloqueur, 8 majeurs, 1 mineur |
| Étapes examinées | 11 présentes, 0 absente, 0 non vérifiée |
| Éléments non vérifiables déclarés | **8** (portée statique) |
| Appels LLM | 4 (P1 + P2 + contrôleur + re-tentative) |
| Confiance | 0,75, calcul explicité |

**Constats réels remontés sur la chaîne** (chacun avec sa preuve citée) : objectifs non couverts
(X8, déterministe) ; changement d'objet entre la question de la problématique et la question retenue ;
titre annonçant des « effets » (lecture causale) face à des analyses d'association ; période annoncée
2020-2024 contre des résultats 2024 ; terrain « Abidjan » contre 7 répondants sur 20 déclarés à Bouaké
(soit 35 %) ; analyse bivariée prévue mais non produite ; volet qualitatif mixte annoncé mais non
mobilisé. **C'est exactement ce que les vérificateurs d'étape ne pouvaient pas voir.**

### Défauts déterministes corrigés avant la campagne

1. **Digest tronqué ⇒ faux constats bloquants (défaut majeur, corrigé).** Le premier audit réel a
   rendu **2 faux constats bloquants** : « la conclusion cite des résultats absents de l'étape 10 » et
   « des étapes vérifiées sont sans contenu » (étape 3, étape 8). Vérification faite : l'étape 10
   contient **106** résultats et **zéro** référence n'était orpheline. La cause était **mon propre
   digest** : il coupait la liste des résultats (60 premiers) et celle des références (40 premières),
   et ne montrait que quelques champs par étape. Correction : digest **complet** (toutes les clés de
   contenu de chaque étape), **listes d'identifiants exhaustives**, toute coupe explicitement marquée
   (« … », « … +N autre(s) »), et règle dure dans le prompt (« tu ne peux jamais conclure qu'un
   résultat manque sans t'appuyer sur la liste exhaustive »). Test de non-régression :
   `tests/coherence/test_coherence_07_digest.py`.
2. **`AuditItem` sans champ `code`** alors que l'orchestrateur le lisait : l'audit échouait à
   l'assemblage (`AttributeError`). Champ ajouté.
3. **Faux positif de fusion (X3).** Le seuil de recouvrement était rapporté au plus **court** des deux
   textes : deux textes traitant du même thème (sujet et problème de recherche) atteignaient 86 % et
   étaient déclarés « le même texte ». Rapporté au plus **long**, le seuil ne se franchit que si l'un
   reprend réellement l'autre ; la recopie directe reste détectée par le test d'inclusion.
4. **Faux positif de contenu (X12).** Le contrôle énumérait les champs attendus par étape : l'étape 3,
   dont la revue vit sous `synthesis`, était déclarée « vide ». Le contrôle teste désormais la présence
   d'un **contenu substantiel, toutes clés confondues**.

### Limites laissées assumées (signalées, non bloquantes)

- L'audit est **relatif au dossier transmis** : une étape absente rend inexplorables les liens qui en
  dépendent (déclaré en portée dynamique).
- La détection de fusion est **lexicale** : deux textes profondément reformulés peuvent échapper au
  programme — le modèle peut alors les signaler, preuve à l'appui.
- Le verdict global est un **indicateur**, pas une décision : l'arbitrage appartient à l'étudiant et à
  son directeur de mémoire.
- Le digest du dossier est borné par étape (coupes marquées) : au-delà de ces bornes, l'audit signale
  qu'il n'a pas tout vu plutôt que de conclure sur ce qu'il n'a pas lu.
