# Architecture V1 — Agent Objectifs de recherche (`research_objectives_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points).
> Référentiel : `docs/spec-agent-06-objectifs-recherche.md` (SPEC reçue).
> Éléments de l'agent : `docs/elements-agent-06-objectifs-recherche.md` (profil Hermes
> `agent-objectifs` + paquet `src/research_objectives_agent/`). **Cadre autonome** : aucun agent
> existant n'est modifié et aucun code n'est partagé avec eux (duplication contrôlée assumée).
> ⚠️ Architecture à contresigner par le porteur de projet.

---

## 1. Architecture

Un **pipeline de définition d'objectifs** en étapes, chacune suivie d'une validation déterministe,
d'un **contrôle de neutralité** codé (pas seulement demandé au modèle) et d'un **portillon humain**
obligatoire. Principe conservé des agents précédents : *aucune sortie LLM utilisée avant
Parser → Schéma → Métier → Sécurité*, et *le modèle ne déclenche jamais lui-même une requête réseau*.

```
ÉTUDIANT (sujet, problème, problématique, QUESTION DE RECHERCHE validée, contraintes, consignes)
   │
   ▼
[1] Input Controller          ── student_id/session_id + snapshots amont (question de recherche, …)
[2] Input Validation          ── contrat d'entrée, tailles, champs obligatoires
[3] Security Layer            ── entrées étudiantes + consignes = DONNÉES NON FIABLES (balisage + scan)
   │
   ▼
[4] PRÉ-CADRAGE (déterministe) ── question de recherche VALIDÉE présente ? sujet ? discipline ?
   │     non → status `needs_clarification` + questions ciblées, AUCUNE formulation lancée
   │     oui → suite
   ▼
[5] LLM P1 — ANALYSE DE LA QUESTION : phénomène, action intellectuelle attendue, dimensions,
   │        périmètre, ambiguïtés + provenance (fourni / déduit / inconnu)
[6] LLM P2 — OBJECTIF GÉNÉRAL : la finalité principale, un seul objectif, verbe d'action adapté,
   │        neutre (aucun résultat annoncé)
[7] LLM P3 — OBJECTIFS SPÉCIFIQUES : décomposition + rationale + alignement question↔objectifs +
   │        évaluation de faisabilité (verdict + raisons + manques)
[8] CONTRÔLES DÉTERMINISTES DES OBJECTIFS ── verbe d'action (O1/O4), aucun résultat présupposé (O2),
   │        objectif ≠ hypothèse / activité (O2/O3), objectif trop vague (O5), redondance (O6),
   │        nombre (alerte O7), délimitation/année sans source (O8), anti-fusion (O9)
[9] CONTRÔLE DE COHÉRENCE (déterministe) ── dimensions de la question couvertes par les objectifs ;
   │        dimension non couverte → déclarée dans les limites
[10] CLARIFICATION DOCUMENTAIRE (déterministe, OPTIONNELLE, bornée) ── lever une ambiguïté
   │        terminologique via API publiques gratuites sans clé ; jamais déclenchée par le modèle.
[11] Parser → Schéma → Métier → Sécurité   (sur CHAQUE sortie LLM des étapes [5], [6], [7])
   ▼
[12] VÉRIFICATEUR INDÉPENDANT (LLM séparé) ── contrôles C1–C13 ; sortie elle-même validée
   │     verified | corrections_requested (≤ MAX_VERIFICATION_RETRIES) | rejected
   │     → pose `verification_result` (jamais `validated`)
   ▼
[13] PORTILLON HUMAIN — status `awaiting_human_validation`
   │     l'étudiant ACCEPTE / MODIFIE / REFUSE + commentaire  (endpoint de décision)
   ▼
[14] DÉCISION ÉTUDIANTE → pose `student_validation` ; si acceptée ET vérifiée → status `validated`
[15] Persistance + audit + réponse HTTP (transmission à l'Agent Hypothèses / diagnostic méthodologique)
```

Points non négociables :
- **Moindre privilège** : `read: session_only` + recherche publique autorisée, `write:
  workspace_only`, `delete/deploy/send: false`.
- **Neutralité structurelle** : un contrôle codé cherche les verbes qui présupposent un résultat
  (« démontrer », « prouver », « montrer que », « confirmer », « établir ») et les hypothèses
  déguisées ; un présupposé déclenche une reformulation ou une question — jamais une validation
  silencieuse.
- **Distinctions préservées** : objectif ≠ hypothèse ≠ activité ≠ résultat ; objectif ≠ question
  (anti-fusion).
- **Aucune méthode imposée** : ni approche (qualitative/quantitative/mixte) ni logique
  (inductive/déductive) n'est décidée ici ; ce choix appartient au diagnostic méthodologique.
- **Honnêteté** : faisabilité `uncertain` si le terrain/les ressources ne sont pas connus ;
  dimension non couverte, information manquante ou échec de clarification sont **déclarés**.
- **0 €** : clarification documentaire sur fournisseurs gratuits sans clé uniquement (voir §13).

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings-objectifs.yaml           # propre à l'agent (LLM, bornes, chemins, clarification)
├── docs/
│   ├── spec-agent-06-objectifs-recherche.md              # SPEC reçue (déposée)
│   ├── architecture-agent-06-objectifs-recherche-v1.md   # ce document
│   └── elements-agent-06-objectifs-recherche.md          # fiche des 19 éléments
├── src/research_objectives_agent/        # paquet AUTONOME
│   ├── main.py                           # app FastAPI (lifespan, state)
│   ├── api/routes.py                     # POST /objectives/analyze, POST .../decision, GET ..., /health
│   ├── pipeline/
│   │   ├── input_controller.py           # session + snapshots amont
│   │   ├── input_validation.py           # contrat d'entrée, tailles
│   │   ├── prerequisites.py              # pré-cadrage SPEC §5/§12 (étape [4], déterministe)
│   │   ├── security_layer.py             # balisage + scan des entrées ET des consignes
│   │   ├── campaign.py                   # orchestrateur, points de reprise
│   │   ├── analysis_stage.py             # LLM P1 (analyse de la question)
│   │   ├── general_stage.py              # LLM P2 (objectif général)
│   │   ├── specific_stage.py             # LLM P3 (objectifs spécifiques + alignement + faisabilité)
│   │   ├── objectives_checks.py          # étape [8] : contrôles codés O1–O9
│   │   ├── alignment_check.py            # étape [9] : cohérence question ↔ objectifs (déterministe)
│   │   ├── clarification_stage.py        # étape [10] : clarification documentaire (optionnelle)
│   │   ├── decision_stage.py             # étapes [13-14] : décision étudiante → student_validation
│   │   ├── output_parser.py
│   │   ├── schema_validation.py
│   │   ├── business_validation.py        # anti-fusion, statuts, honnêteté
│   │   ├── security_validation.py
│   │   └── verifier.py                   # vérificateur indépendant
│   ├── analysis/
│   │   └── objective_rules.py            # verbes, neutralité, hypothèse, activité, redondance, délimitation
│   ├── sources/
│   │   ├── providers.yaml                # fournisseurs + hôtes autorisés (clarification)
│   │   ├── registry.py http.py cache.py  # registre, client borné, cache SQLite
│   │   └── adapters/                     # adaptateurs gratuits sans clé (repris en autonome)
│   ├── schemas/
│   │   ├── input.py analysis.py objectives.py decision.py output.py verifier.py stages.py common.py
│   ├── core/
│   │   ├── config.py limits.py errors.py logging.py sessions.py security_rules.py
│   ├── storage/
│   │   ├── workspace.py                  # artefacts par session
│   │   └── audit.py                      # journal d'audit (SQLite)
│   └── llm/
│       ├── client.py                     # client LLM (clé héritée, budget, re-tentative)
│       └── prompts/
│           ├── p1_analysis_system.md p2_general_system.md p3_specific_system.md verifier_system.md
├── run-objectifs.sh                      # port 8060
├── workspace/                            # audit-objectifs.db, objectifs-cache.db, <student>/<session>/
└── tests/objectifs/                      # neutralité, campagne, décision, sécurité, API, chaîne amont
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `pipeline/prerequisites.py` | Vérifie les prérequis (SPEC §5, §12) : sujet, discipline et **question de recherche** (champ direct ou `upstream_question.validation.verified`). Manque essentiel → `needs_clarification`, aucune formulation lancée. |
| `pipeline/analysis_stage.py` | LLM P1 : dégage le phénomène, l'action intellectuelle attendue, les dimensions, le périmètre et les ambiguïtés, avec provenance (fourni / déduit / inconnu). |
| `pipeline/general_stage.py` | LLM P2 : formule l'objectif général (un seul, verbe d'action, neutre). |
| `pipeline/specific_stage.py` | LLM P3 : décompose en objectifs spécifiques, produit le rationale, l'alignement question↔objectifs et l'évaluation de faisabilité. |
| `analysis/objective_rules.py` | Cœur déterministe : verbes d'action, verbes de présupposé interdits, tournures d'hypothèse, activités administratives, redondance (Jaccard), délimitation sans source, années inventées. |
| `pipeline/objectives_checks.py` | Applique `objective_rules` (O1–O9) sur la production assemblée, avec boucle de re-tentative correctrice. |
| `pipeline/alignment_check.py` | Contrôle la chaîne question → objectif général → objectifs spécifiques (dimensions couvertes). |
| `pipeline/clarification_stage.py` | Étape optionnelle (désactivée par défaut) : lève une ambiguïté terminologique via API publiques gratuites sans clé. Aucun appel piloté par le modèle ; un échec réseau est **déclaré**. |
| `pipeline/decision_stage.py` | Portillon humain : enregistre la décision (acceptée / modifiée / refusée) et pose `student_validation` ; seule une décision acceptée **après** vérification donne `validated`. |
| `pipeline/business_validation.py` | Orchestre les contrôles codés : anti-fusion, statuts, honnêteté, délimitation déclarée. |
| `sources/providers.yaml` | Fournisseurs de clarification déclarés en configuration (hôte autorisé). Ajouter un fournisseur gratuit = éditer ce fichier. |

---

## 4. Flux des données

```
POST /objectives/analyze
  body: { student_id, session_id?, subject_text, research_problem?, validated_problematic?,
          main_research_question, secondary_research_questions?, objectives_draft?,
          discipline, academic_level?, country?, geographical_area?, study_period?,
          target_population?, research_context?, student_constraints?, university_instructions?,
          supervisor_instructions?, previous_answers?, language_prefs?,
          upstream_subject?, upstream_problem?, upstream_problematic?,
          upstream_question (vérifié), constraints? }
   │
   ├─ Input Controller → session ; snapshots amont acceptés SEULEMENT si `validation.verified`
   ├─ Input Validation → 422 INVALID_INPUT si non conforme
   ├─ Security Layer   → balisage non fiable (consignes, contexte, consignes universitaires)
   ├─ Pré-cadrage      → question absente / prérequis manquants ?
   │                     → 200 `needs_clarification` + questions, FIN
   │
   ├─ LLM P1 → analyse de la question            → Parser → Schéma → Métier → Sécurité
   ├─ LLM P2 → objectif général                   → Parser → Schéma → Métier
   ├─ LLM P3 → objectifs spécifiques + alignement → Parser → Schéma → Métier
   ├─ Contrôles des objectifs (déterministes)     → neutralité, verbe, hypothèse, redondance, délimitation
   ├─ Contrôle de cohérence (déterministe)        → dimensions couvertes / non couvertes
   ├─ Clarification documentaire (optionnelle)    → concept vérifié ou `unavailable` (déclaré)
   ├─ Sécurité (toutes sorties)                   → rien d'exécutable, aucune URL arbitraire
   ├─ VÉRIFICATEUR INDÉPENDANT                     → verified | corrections_requested | rejected
   └─ Persistance + audit
        → 200 { status: "awaiting_human_validation", objectifs, rationale, alignement, faisabilité }

POST /objectives/{student_id}/{session_id}/decision
  body: { decision: "accepted"|"modified"|"refused", student_comment?,
          modified_general_objective?, modified_specific_objectives?[] }
   ├─ vérifie que la sortie précédente est `verified` et `awaiting_human_validation`
   ├─ pose `student_validation`
   └─ accepted + verified → `validated` ; modified → contrôles puis re-vérification ; refused → `blocked`
```

---

## 5. Modèle de données

| Objet | Champs principaux | Remarques |
|---|---|---|
| `QuestionAnalysis` | `phenomene`, `action_attendue`, `dimensions[]`, `perimetre`, `ambiguites[]`, `provenance` | `provenance` ∈ {provided, inferred, unknown} ; rien d'inventé |
| `general_objective` | chaîne | Un seul objectif, verbe d'action, neutre |
| `specific_objectives` | liste de chaînes | Complémentaires, non redondants ; aucun nombre fixe imposé |
| `objective_rationale` | chaîne | Justification de la formulation des objectifs |
| `QuestionObjectiveAlignment` | `general_to_question`, `specifics_cover_general`, `secondary_questions_coverage[]`, `uncovered_dimensions[]` | Chaîne Question → OG → OS documentée |
| `FeasibilityAssessment` | `verdict` ∈ {feasible, uncertain, not_feasible}, `raisons[]`, `manques[]` | Dépend des contraintes/terrain connus |
| `Ambiguity` | `description`, `impact`, `clarification_question` | Alimente le human gate |
| `SourceEvidence` | `query`, `provider`, `source_id`, `url`, `used` | Si clarification documentaire utilisée |
| `VerificationResult` | `verified: bool`, `checks[]`, `limitations[]` | Posé par le vérificateur uniquement |
| `StudentValidation` | `decision` ∈ {accepted, modified, refused}, `comment`, `at` | Posé par l'endpoint de décision |
| `Confidence` | `overall`, `rationale` | Dérivée des preuves (faisabilité, vérification, ambiguïtés) |
| `Evidence` | compteurs : appels LLM, requêtes réseau, reformulations | Preuve d'honnêteté |

---

## 6. Contrat d'entrée (SPEC §6)

| Champ | Type | Requis | Provenance |
|---|---|---|---|
| `student_id` | string | oui | fourni |
| `session_id` | string | non (généré) | fourni |
| `subject_text` | string | oui (ou amont vérifié) | fourni |
| `main_research_question` | string | oui (ou `upstream_question` vérifié) | fourni |
| `secondary_research_questions` | array | non | fourni / amont |
| `validated_problematic` | string | non | fourni / amont |
| `research_problem` | string | non | fourni |
| `discipline` | string | oui | fourni |
| `academic_level` / `country` / `geographical_area` / `study_period` / `target_population` / `research_context` | string | non | fourni |
| `objectives_draft` | string | non | fourni (donnée non fiable) |
| `student_constraints` / `university_instructions` / `supervisor_instructions` | string | non | fourni (données non fiables) |
| `previous_answers` | array | non | réponses antérieures |
| `upstream_subject` / `upstream_problem` / `upstream_problematic` / `upstream_question` | object | non | acceptés si `validation.verified = true` |
| `constraints` | string | non | bornes de session |

Taille maximale : 40000 caractères. Un amont non vérifié ⇒ `422` / `MISSING_INFORMATION` (jamais de
formulation non fondée).

---

## 7. Contrat de sortie (SPEC §16)

```json
{
  "status": "needs_clarification | ready_for_verification | verification_failed | awaiting_human_validation | blocked | validated",
  "subject": "...",
  "validated_problematic": "...",
  "main_research_question": "...",
  "secondary_research_questions": [],
  "question_analysis": { "phenomene": "...", "action_attendue": "analyser", "dimensions": [],
                         "perimetre": "...", "ambiguites": [], "provenance": "provided" },
  "general_objective": "Analyser la relation entre ...",
  "specific_objectives": ["Identifier ...", "Examiner ...", "Comparer ..."],
  "objective_rationale": "...",
  "question_objective_alignment": { "general_to_question": "...", "specifics_cover_general": "...",
                                    "secondary_questions_coverage": [], "uncovered_dimensions": [] },
  "scope_and_boundaries": { "geo": "", "temps": "", "population": "", "added_without_source": false },
  "feasibility_assessment": { "verdict": "uncertain", "raisons": [], "manques": [] },
  "missing_information": [],
  "ambiguities": [ { "description": "...", "impact": "...", "clarification_question": "..." } ],
  "source_evidence": [],
  "verification_result": { "verified": false, "verifier_status": "pending" },
  "student_validation": { "decision": null, "comment": "", "at": null },
  "confidence": { "overall": 0.0, "rationale": "..." },
  "evidence": { "llm_calls": 0, "network_requests": 0, "reformulations": 0 }
}
```

Aucun champ de l'étape suivante n'est produit comme « validé » : la sortie transmet les objectifs
validés sans imposer de méthodologie ni anticiper de résultats. Pas de fusion avec la question, le
problème, la problématique ni les hypothèses.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mitigation dans cet agent |
|---|---|
| LLM01 — Prompt injection | Consignes, contexte et consignes universitaires/cadre = DONNÉES NON FIABLES : balisées, scannées (motifs d'injection), jamais suivies comme instructions. |
| LLM02 — Insecure output handling | Aucune sortie LLM utilisée sans `Parser → Schéma → Métier → Sécurité` ; aucune exécution, aucun appel réseau déclenché par le modèle. |
| LLM03 — Supply chain | Dépendances figées et documentées, toutes gratuites/open source ; aucune installation automatique. |
| LLM04 — Data/model poisoning | Les entrées proviennent des étapes vérifiées ; aucun contenu non vérifié n'entre dans la formulation. |
| LLM05 — Improper output handling | Sorties structurées uniquement ; aucune référence bibliographique inventée. |
| LLM06 — Excessive agency | Moindre privilège : `read session_only`, `write workspace_only`, `delete/deploy/send = false` ; périmètre réseau limité à la clarification (liste blanche). |
| LLM07 — System prompt leakage + misinformation | Zéro hallucination : aucun présupposé, aucune population/période/zone inventée ; contrôle de neutralité codé. |
| LLM08 — Vector/embedding weaknesses | Aucune base vectorielle en V1 (pas d'embedding) : surface supprimée. |
| LLM09 — Misinformation | Contrôle de neutralité déterministe + distinction objectif ≠ hypothèse + déclaration des ambiguïtés et manques + vérificateur indépendant. |
| LLM10 — Unbounded consumption | Bornes : `max_input_size`, `max_output_tokens`, `max_external_requests`, `max_clarification_queries`, cache, garde anti-non-convergence, budget LLM par campagne. |

Isolation par `student_id`/`session_id` : chaque session écrit dans
`workspace/<student_id>/<session_id>/` et rien d'autre.

---

## 9. Mécanisme de validation

Sur **chaque** sortie LLM (étapes [5], [6], [7]) :

1. **Parser** — extraction JSON stricte ; en cas de troncature (modèle raisonneur), **re-tentative**
   avec consigne de concision (budget large : `max_output_tokens` 32000).
2. **Schéma** — validation pydantic : types, énumérations, champs requis.
3. **Métier** — contrôles codés :
   - verbe d'action en tête de chaque objectif (O1/O4) ;
   - aucun résultat présupposé (O2) ;
   - objectif ≠ hypothèse (O2) ≠ activité administrative (O3) ;
   - objectif trop vague (O5), redondance entre objectifs (O6), nombre (alerte O7) ;
   - délimitation ou année ajoutée sans source (O8) ;
   - anti-fusion : objectif ≠ question (O9) ;
   - `status` honnête.
4. **Sécurité** — aucun contenu exécutable, aucune URL arbitraire, aucune tentative d'injection
   propagée depuis les consignes.

Violations métier non bloquantes : re-tentative ; si des violations subsistent à la **dernière**
tentative, **lever** (jamais de sortie non conforme transmise au vérificateur).

---

## 10. Mécanisme de vérification (SPEC §13)

**Vérificateur indépendant** (LLM séparé, prompt dédié, reçoit toutes les données étudiantes + la
question + la production) — contrôles **C1–C13** :

| Code | Contrôle |
|---|---|
| C1 | L'objectif général répond à la question principale (rattachement explicite, non fusionné). |
| C2 | Les objectifs spécifiques contribuent à l'objectif général et couvrent ses dimensions. |
| C3 | Chaque objectif est clair, précis ; le verbe d'action est adapté. |
| C4 | Les objectifs sont complémentaires : aucune redondance inutile, aucun hors sujet. |
| C5 | Faisabilité examinée au regard des ressources, du terrain et des contraintes connus. |
| C6 | Neutralité : aucun objectif ne présuppose un résultat. |
| C7 | Distinction objectif ≠ hypothèse. |
| C8 | Distinction objectif ≠ activité administrative. |
| C9 | Aucune information inventée (population, terrain, période, causalité, conclusion). |
| C10 | Aucune délimitation ajoutée sans source ; toute délimitation manquante est déclarée. |
| C11 | Aucune méthodologie, échantillonnage ni technique de collecte imposée. |
| C12 | Alignement question → OG → OS documenté ; questions secondaires couvertes le cas échéant. |
| C13 | Honnêteté : limites/incertitudes déclarées ; aucun auto-`verified` ni `validated`. |

Verdict : `verified` | `corrections_requested` (≤ `MAX_VERIFICATION_RETRIES`) | `rejected`.
Si les mêmes corrections reviennent deux fois, la boucle s'arrête. La sortie du vérificateur est
elle-même validée en schéma/métier (format des listes normalisé défensivement). **Le verdict
`verified` ne vaut pas validation** : la validation est humaine (§ 1, étapes [13-14]).

---

## 11. Stratégie de tests

| Niveau | Contenu |
|---|---|
| Unitaire / fonctionnel hors réseau | `tests/objectifs/` : LLM simulé (JSON conformes **et** dégradés). Analyse, objectif général, objectifs spécifiques, contrôles, faisabilité. |
| Neutralité / anti-présupposé | Objectif neutre accepté ; objectif « Démontrer que… » refusé (O2) ; hypothèse déguisée détectée. |
| Distinctions | objectif ≠ hypothèse ; objectif ≠ activité administrative (sauf consigne explicite) ; anti-fusion objectif ≠ question (O9). |
| Complémentarité | Redondance détectée (O6) ; nombre d'objectifs signalé (alerte O7) ; dimension non couverte déclarée. |
| Délimitation | Année citée sans être fournie → signalée (O8) ; délimitation composée issue de champs distincts acceptée. |
| Human gate | Décision `accepted` (→ `validated` si vérifié), `modified` (→ contrôles puis re-vérification), `refused` (→ `blocked`). |
| Sécurité | Injection dans des consignes non suivie ; sortie exécutable/secret rejetée ; isolation par session. |
| Intégration | `POST /objectives/analyze` bout en bout ; `needs_clarification` sans question de recherche. |
| **Réel** | Modèle réel + question de recherche réelle → jusqu'au verdict du vérificateur, puis décision étudiante simulée. Script hors dépôt, résultats dans la section « État réel ». |

Nommage : module d'aide `tests/objectifs/objectifs_helpers.py` (pas `helpers.py` — collision avec
`tests/helpers.py`).

---

## 12. Dépendances

Toutes **gratuites / open source**, figées et documentées (aucune installation automatique) :
`fastapi`, `uvicorn`, `pydantic`, `httpx`, `python-dotenv`, `pyyaml`, `pytest`. Aucune clé tierce : la
clarification documentaire n'utilise que des API publiques sans clé (si activée). Le LLM passe par la
clé existante de `~/.hermes/.env` (DeepSeek, déjà en place).

---

## 13. Coûts éventuels

| Poste | Coût |
|---|---|
| LLM (P1–P3 + vérificateur) | Clé DeepSeek déjà en place (budget projet 0 € ; tokens bornés par campagne). |
| Clarification documentaire (8 fournisseurs gratuits sans clé) | Gratuit, sans clé ; désactivée par défaut. |
| Stockage | Local, nul. |

**Total : 0 €.**

---

## 14. Alternatives gratuites

- Clarification de concept : **huit** fournisseurs sans clé déclarés en configuration — OpenAlex,
  Crossref, HAL, theses.fr, OpenAIRE, DataCite, DOAJ, Europe PMC (adaptateurs repris en autonome).
  Ajouter/retirer un fournisseur = éditer `sources/providers.yaml`. Fonctionnalité **optionnelle**.
- Aucune base vectorielle : la comparaison question / objectifs se fait par contrôles codés
  (verbes, recouvrement terminologique, motifs de présupposé), sans embedding.
- Si la clé OpenAlex gratuite existe (`OPENALEX_API_KEY`, déjà posée), elle est lue et transmise en
  en-tête `Authorization` (jamais dans l'URL) ; sinon les sept autres fournisseurs suffisent.

---

## 15. Limites connues

1. **Dépendance forte à l'amont** : sans question de recherche (validée et vérifiée), l'agent ne peut
   pas définir d'objectifs → `needs_clarification` (choix assumé).
2. **Neutralité = détection déterministe partielle** : le contrôle des présupposés repose sur des
   motifs codés + le vérificateur LLM ; une présupposition implicite subtile peut échapper → l'humain
   reste le dernier rempart (portillon obligatoire).
3. **Nombre d'objectifs** : aucun nombre fixe n'est imposé ; au-delà de 7, un signalement invite à
   vérifier la complémentarité (jamais un refus automatique).
4. **Faisabilité limitée à l'information fournie** : si le terrain, la population ou les ressources ne
   sont pas connus, la faisabilité reste `uncertain` et déclarée — jamais supposée.
5. **Clarification documentaire partielle** : `not_found` signifie « non trouvé dans ces sources »,
   jamais « inexistant » ; toujours déclaré.
6. **Qualité = proposition** : les objectifs restent une proposition à valider par l'étudiant et son
   directeur ; l'agent n'a jamais raison contre eux.
7. **Pas d'embedding/RAG vectoriel en V1** (SPEC §28) : accès à l'information par règles codées et
   API publiques.

---

## Décisions à valider par le porteur de projet (portillon §42)

- **D1 — Portillon humain et statut `validated`.** La SPEC §12 fait de la validation étudiante un
  préalable obligatoire et §16 interdit à l'agent de s'auto-attribuer `validated`. Proposition :
  l'agent s'arrête à `awaiting_human_validation` ; un endpoint dédié
  (`POST /objectives/{student_id}/{session_id}/decision`) enregistre la décision (acceptée / modifiée
  / refusée) et, si acceptée **et** vérifiée, pose `validated`.
- **D2 — Clarification documentaire.** La SPEC §8/§11 l'autorise « si nécessaire ». Proposition :
  étage **optionnel, désactivé par défaut** (0 requête), activable en configuration.
- **D3 — Verbes d'action.** La SPEC §7.B liste 14 verbes. Proposition : liste canonique + variantes
  proches admises ; verbes de présupposé (« démontrer, prouver, montrer, confirmer, établir,
  justifier, valider… ») **interdits par contrôle codé**.
- **D4 — Nombres d'objectifs.** Proposition : aucun minimum/maximum fixe ; seuil d'alerte à 7.
- **D5 — Interface.** Route `POST /objectives/analyze`, port **8060**, `run-objectifs.sh`, profil
  Hermes `agent-objectifs` ; confirmation de l'alignement des routes (`/objectives/...`).
- **D6 — Chaîne amont.** L'agent consomme la sortie de l'Agent Question de recherche
  (`upstream_question`) acceptée seulement si `validation.verified = true`.

---

## État réel de l'implémentation

> **Implémenté et vérifié en exécution réelle** (campagne DeepSeek, hors sources réseau).

### Tests hors réseau

- `pytest -q tests/objectifs` → **34 tests**, tous verts.
- Suite complète du dépôt (`pytest -q`) → **304 tests**, hors réseau.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

Sonde : `/root/.hermes/cache/scratch/e2e_objectifs.py` (hors dépôt ; question de recherche réelle +
problématique réelle). Campagne sans réseau de sources (`clarification.enabled: false`).

| Passe | Statut final | Vérificateur | Appels LLM | Reformulations | Décision étudiante |
|---|---|---|---|---|---|
| 1 | `awaiting_human_validation` | `verified` (13/13) | 4 | 0 | `accepted` → `validated` |
| 2 | `awaiting_human_validation` | `verified` (13/13) | 4 | 0 | `accepted` → `validated` |
| 3 | `awaiting_human_validation` | `verified` (13/13) | 8 | 1 | `accepted` → `validated` |
| 4 | `awaiting_human_validation` | `verified` (13/13) | 4 | 0 | `accepted` → `validated` |

Sortie type observée (passe 4) :

- `action_attendue` : « Mesurer / déterminer l'ampleur de l'influence… » ;
- `general_objective` : « Mesurer l'influence du télétravail sur la productivité des salariés en
  télétravail à Abidjan (Côte d'Ivoire) sur la période 2020-2024. » ;
- `specific_objectives` : 4 à 5 objectifs (décrire les modalités, mesurer/caractériser la
  productivité, analyser la coordination, comparer, identifier les conditions) — **aucun à
  présupposé** ;
- `feasibility_assessment` : `uncertain` (indicateurs de productivité et accès au terrain non
  établis) — **déclaré**, jamais supposé ;
- `missing_information` : 3 à 5 éléments (indicateur de productivité, base de sondage, ressources) ;
- `question_analysis.ambiguites` remontées au champ `ambiguities` avec leur question de clarification.

### Correctifs issus de l'exécution réelle

- **Cohérence des champs dérivés** : un `missing_information` non répercuté dans `limits_of_this_output`
  et une faisabilité `uncertain` non déclarée dans les limites étaient signalés par le vérificateur →
  `_derived` les répercute explicitement.
- **Ambiguïtés de l'analyse** : elles ne remontaient pas au champ de premier niveau (`ambiguities`) ni
  dans `clarification_questions` → `_assemble` les propage désormais (description + question).

### Limites laissées assumées (signalées, non bloquantes)

Le vérificateur émet des **signalements** (jamais des corrections bloquantes dans ces passes) :
tension entre un objectif de « mesure » et une faisabilité `uncertain` ; confiance basse cohérente avec
le nombre d'informations manquantes ; ambiguïtés à lever avant de figer les objectifs. Ils sont
**conservés tels quels** : ils documentent l'honnêteté de la sortie et le rôle du vérificateur.
