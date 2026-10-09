# Architecture V1 — Agent Hypothèses de recherche (`research_hypotheses_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points).
> Référentiel : `docs/spec-agent-07-hypotheses.md` (SPEC reçue).
> Éléments de l'agent : `docs/elements-agent-07-hypotheses.md` (profil Hermes `agent-hypotheses` +
> paquet `src/research_hypotheses_agent/`). **Cadre autonome** : aucun agent existant n'est modifié et
> aucun code n'est partagé avec eux (duplication contrôlée assumée).
> ⚠️ Architecture à contresigner par le porteur de projet.

---

## 1. Architecture

Un **pipeline de décision et de formulation d'hypothèses**, chaque étape suivie d'une validation
déterministe, d'un **contrôle de neutralité** codé et d'un **portillon humain** obligatoire. Principe
conservé des agents précédents : *aucune sortie LLM utilisée avant Parser → Schéma → Métier →
Sécurité*, et *le modèle ne déclenche jamais lui-même une requête réseau*.

```
ÉTUDIANT (question de recherche validée, objectifs validés, cadre théorique, contraintes, consignes)
   │
   ▼
[1] Input Controller          ── student_id/session_id + snapshots amont (objectifs, question)
[2] Input Validation          ── contrat d'entrée, tailles, champs obligatoires
[3] Security Layer            ── entrées étudiantes + consignes = DONNÉES NON FIABLES (balisage + scan)
   │
   ▼
[4] PRÉ-CADRAGE (déterministe) ── question de recherche ET objectifs présents ? sujet ? discipline ?
   │     non → status `needs_clarification` + questions ciblées, AUCUNE production lancée
   │     oui → suite
   ▼
[5] LLM P1 — ANALYSE : phénomène, action attendue, nature du travail (exploratoire/descriptif/
   │        explicatif…), ambiguïtés BLOQUANTES, provenance
[6] LLM P2 — DÉCISION DE PERTINENCE : HYPOTHESES_RECOMMENDED | HYPOTHESES_NOT_REQUIRED |
   │        HYPOTHESES_REQUIRE_CLARIFICATION + justification
[7] LLM P3 — FORMULATION (UNIQUEMENT si RECOMMENDED) : hypothèses (id, formulation, rattachement,
   │        concepts/variables, justification, sources, données requises, limites) + alignement
   │        question/objectifs + support théorique/littérature + preuves requises
[8] CONTRÔLES DÉTERMINISTES (H1–H8) ── cohérence décision ↔ hypothèses, hypothèse ≠ question ≠
   │        objectif (H2), aucun fait présupposé (H3), causalité non établie (H4), examinabilité (H5),
   │        justification traçable (H6), redondance (H7), anti-fusion (H8)
[9] CONTRÔLE DE COHÉRENCE (déterministe) ── objectifs couverts par les hypothèses ; non couverts
   │        → déclarés
[10] CLARIFICATION DOCUMENTAIRE (déterministe, OPTIONNELLE, bornée) ── lever une ambiguïté
   │        terminologique via API publiques gratuites sans clé ; jamais déclenchée par le modèle.
[11] Parser → Schéma → Métier → Sécurité   (sur CHAQUE sortie LLM des étapes [5], [6], [7])
   ▼
[12] VÉRIFICATEUR INDÉPENDANT (LLM séparé) ── contrôles C1–C13 ; sortie elle-même validée
   │     verified | corrections_requested (≤ MAX_VERIFICATION_RETRIES) | rejected
   │     → pose `verification_result` (jamais `validated`)
   ▼
[13] PORTILLON HUMAIN — status `awaiting_human_validation`
   │     l'étudiant ACCEPTE / MODIFIE / REFUSE (+ décision et/ou hypothèses modifiées)
   ▼
[14] DÉCISION ÉTUDIANTE → pose `student_validation` ; si acceptée ET vérifiée → status `validated`
[15] Persistance + audit + réponse HTTP (transmission à l'Agent Diagnostic méthodologique)
```

Points non négociables :
- **Moindre privilège** : `read: session_only` + recherche publique autorisée, `write:
  workspace_only`, `delete/deploy/send: false`.
- **Pas d'hypothèses forcées** : une décision `HYPOTHESES_NOT_REQUIRED` court-circuite l'étape [7] —
  aucune hypothèse n'est inventée pour remplir un chapitre.
- **Neutralité structurelle** : un contrôle codé cherche les faits présupposés (« il est démontré
  que… »), les questions déguisées en hypothèses et les causalités non établies.
- **Distinctions préservées** : hypothèse ≠ question ≠ objectif ≠ fait ≠ résultat (anti-fusion).
- **Aucune méthode imposée** : ni approche, ni échantillonnage, ni technique de collecte.
- **Honnêteté** : limites, incertitudes et objectifs non couverts sont **déclarés**.
- **0 €** : clarification documentaire sur fournisseurs gratuits sans clé uniquement (voir §13).

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings-hypotheses.yaml           # propre à l'agent (LLM, bornes, chemins, clarification)
├── docs/
│   ├── spec-agent-07-hypotheses.md              # SPEC reçue (déposée)
│   ├── architecture-agent-07-hypotheses-v1.md   # ce document
│   └── elements-agent-07-hypotheses.md          # fiche des 19 éléments
├── src/research_hypotheses_agent/        # paquet AUTONOME
│   ├── main.py  api/routes.py            # FastAPI : /hypotheses/analyze, .../decision, GET, /health
│   ├── pipeline/
│   │   ├── input_controller.py input_validation.py prerequisites.py security_layer.py campaign.py
│   │   ├── analysis_stage.py             # LLM P1 (analyse)
│   │   ├── pertinence_stage.py           # LLM P2 (décision)
│   │   ├── formulation_stage.py          # LLM P3 (hypothèses)
│   │   ├── hypotheses_checks.py          # H1–H8 (déterministe)
│   │   ├── alignment_check.py            # cohérence objectifs ↔ hypothèses (déterministe)
│   │   ├── clarification_stage.py decision_stage.py output_parser.py schema_validation.py
│   │   ├── business_validation.py security_validation.py verifier.py
│   ├── analysis/hypothesis_rules.py      # distinctions, causalité, examinabilité, redondance
│   ├── sources/                          # providers.yaml, registry, http, cache, adapters/
│   ├── schemas/                          # input analysis hypotheses decision output verifier stages common
│   ├── core/                             # config limits errors logging sessions security_rules
│   ├── storage/                          # workspace, audit
│   └── llm/                              # client + prompts (p1, p2, p3, verifier)
├── run-hypotheses.sh                     # port 8070
├── workspace/                            # audit-hypotheses.db, hypotheses-cache.db, <student>/<session>/
└── tests/hypotheses/                     # règles, campagne, décision, sécurité, API, chaîne amont
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `pipeline/prerequisites.py` | Vérifie les prérequis (SPEC §5) : sujet, discipline, **question de recherche** ET **objectifs** (champ direct ou `upstream_objectives.validation.verified`). Manque essentiel → `needs_clarification`. |
| `pipeline/analysis_stage.py` | LLM P1 : dégage le phénomène, l'action attendue, la nature du travail et les ambiguïtés **bloquantes**. |
| `pipeline/pertinence_stage.py` | LLM P2 : décide `HYPOTHESES_RECOMMENDED` / `HYPOTHESES_NOT_REQUIRED` / `HYPOTHESES_REQUIRE_CLARIFICATION` avec justification (+ questions si clarification). |
| `pipeline/formulation_stage.py` | LLM P3 (**si RECOMMENDED uniquement**) : hypothèses, alignement, support, preuves requises. |
| `analysis/hypothesis_rules.py` | Cœur déterministe : hypothèse ≠ question ≠ objectif, faits présupposés, causalité (dont modération) non établie, examinabilité, redondance. |
| `pipeline/hypotheses_checks.py` | Applique `hypothesis_rules` (H1–H8), avec boucle de re-tentative correctrice. |
| `pipeline/alignment_check.py` | Contrôle la chaîne question → objectifs → hypothèses (objectifs non couverts déclarés). |
| `pipeline/decision_stage.py` | Portillon humain : décision acceptée / modifiée (décision et/ou hypothèses) / refusée ; basculer vers « pas d'hypothèses » vide les hypothèses (cohérence H1). |
| `pipeline/business_validation.py` | Décision cohérente avec le contenu, statuts, honnêteté. |

---

## 4. Flux des données

```
POST /hypotheses/analyze
  body: { student_id, session_id?, subject_text, research_problem?, validated_problematic?,
          main_research_question, secondary_research_questions?, general_objective?,
          specific_objectives?[], theoretical_framework?, existing_hypotheses?, discipline,
          academic_level?, country?, geographical_area?, study_period?, target_population?,
          research_context?, student_constraints?, university_instructions?,
          supervisor_instructions?, previous_answers?, language_prefs?,
          upstream_subject?, upstream_problem?, upstream_problematic?, upstream_question?,
          upstream_objectives (vérifié), constraints? }
   │
   ├─ Input Controller → session ; snapshots amont acceptés SEULEMENT si `validation.verified`
   ├─ Input Validation → 422 INVALID_INPUT si non conforme
   ├─ Security Layer   → balisage non fiable
   ├─ Pré-cadrage      → question/objectifs absents ? → 200 `needs_clarification`, FIN
   │
   ├─ LLM P1 → analyse                            → Parser → Schéma → Métier → Sécurité
   ├─ LLM P2 → décision de pertinence
   │     ├─ REQUIRE_CLARIFICATION → 200 `needs_clarification` + questions, FIN (P3 non appelée)
   │     └─ RECOMMENDED → LLM P3 → hypothèses      → Parser → Schéma → Métier
   │           NOT_REQUIRED → aucune hypothèse (P3 non appelée)
   ├─ Contrôles des hypothèses (déterministes)     → H1–H8
   ├─ Contrôle de cohérence (déterministe)         → objectifs couverts / non couverts
   ├─ Clarification documentaire (optionnelle)     → concept vérifié ou `unavailable` (déclaré)
   ├─ Sécurité (toutes sorties)
   ├─ VÉRIFICATEUR INDÉPENDANT                      → verified | corrections_requested | rejected
   └─ Persistance + audit
        → 200 { status: "awaiting_human_validation", décision, hypothèses, alignement }

POST /hypotheses/{student_id}/{session_id}/decision
  body: { decision: "accepted"|"modified"|"refused", student_comment?,
          modified_decision?, modified_hypotheses?[] }
   ├─ accepted + verified → `validated` ; refused → `blocked`
   └─ modified → contrôles H1–H8 puis re-vérification
```

---

## 5. Modèle de données

| Objet | Champs principaux | Remarques |
|---|---|---|
| `HypothesisAnalysis` | `phenomene`, `action_attendue`, `nature_du_travail`, `ambiguites[]`, `provenance` | Les ambiguïtés sont **bloquantes** ; vides sinon |
| `hypotheses_decision` | enum {HYPOTHESES_RECOMMENDED, HYPOTHESES_NOT_REQUIRED, HYPOTHESES_REQUIRE_CLARIFICATION} | Toujours accompagnée de `decision_rationale` |
| `Hypothesis` | `id`, `formulation`, `linked_to`, `concepts_variables[]`, `justification`, `sources[]`, `required_data[]`, `limits[]` | Proposition à examiner ; jamais un fait |
| `HypothesisObjectiveAlignment` | `general_to_objectives`, `hypotheses_cover_objectives`, `uncovered_objectives[]`, `contradictions[]` | Chaîne Question → Objectifs → Hypothèses |
| `theoretical_or_literature_support` | liste de chaînes | Appuis mobilisés (fournis, jamais inventés) |
| `required_evidence` | liste de chaînes | Ce qu'il faudra observer/mesurer (sans méthode) |
| `Ambiguity` | `description`, `impact`, `clarification_question` | Alimente le human gate |
| `VerificationResult` | `verified: bool`, `verifier_status` | Posé par le vérificateur uniquement |
| `StudentValidation` | `decision` ∈ {accepted, modified, refused}, `comment`, `at` | Posé par l'endpoint de décision |
| `Confidence` | `overall`, `rationale` | Dérivée des preuves (décision, vérification, manques) |
| `Evidence` | compteurs : appels LLM, requêtes réseau, reformulations | Preuve d'honnêteté |

---

## 6. Contrat d'entrée (SPEC §6)

| Champ | Type | Requis | Provenance |
|---|---|---|---|
| `student_id` | string | oui | fourni |
| `main_research_question` | string | oui (ou `upstream_objectives`/`upstream_question` vérifié) | fourni |
| `general_objective` / `specific_objectives` | string / array | oui (ou amont vérifié) | fourni |
| `subject_text` | string | oui (ou amont vérifié) | fourni |
| `discipline` | string | oui | fourni |
| `secondary_research_questions` | array | non | fourni / amont |
| `validated_problematic`, `research_problem` | string | non | fourni / amont |
| `theoretical_framework`, `existing_hypotheses` | string | non | fourni (données non fiables) |
| `academic_level`, `country`, `geographical_area`, `study_period`, `target_population`, `research_context` | string | non | fourni |
| `student_constraints`, `university_instructions`, `supervisor_instructions` | string | non | fourni (données non fiables) |
| `previous_answers` | array | non | réponses antérieures |
| `upstream_subject/problem/problematic/question/objectives` | object | non | acceptés si `validation.verified = true` |
| `constraints` | string | non | bornes de session |

Taille maximale : 40000 caractères. Un amont non vérifié ⇒ `422` / `MISSING_INFORMATION`.

---

## 7. Contrat de sortie (SPEC §16)

```json
{
  "status": "needs_clarification | ready_for_verification | verification_failed | awaiting_human_validation | blocked | validated",
  "subject": "...",
  "main_research_question": "...",
  "secondary_research_questions": [],
  "general_objective": "...",
  "specific_objectives": [],
  "analysis": { "phenomene": "...", "action_attendue": "...", "nature_du_travail": "explicatif",
                "ambiguites": [], "provenance": "provided" },
  "hypotheses_decision": "HYPOTHESES_RECOMMENDED",
  "decision_rationale": "...",
  "research_hypotheses": [
    { "id": "H1", "formulation": "...", "linked_to": "...", "concepts_variables": [],
      "justification": "...", "sources": [], "required_data": [], "limits": [] }
  ],
  "hypothesis_objective_alignment": { "general_to_objectives": "...",
      "hypotheses_cover_objectives": "...", "uncovered_objectives": [], "contradictions": [] },
  "theoretical_or_literature_support": [],
  "required_evidence": [],
  "missing_information": [],
  "ambiguities": [],
  "source_evidence": [],
  "verification_result": { "verified": false, "verifier_status": "pending" },
  "student_validation": { "decision": null, "comment": "", "at": null },
  "confidence": { "overall": 0.0, "rationale": "..." },
  "evidence": { "llm_calls": 0, "network_requests": 0, "reformulations": 0 }
}
```

Aucun champ de l'étape suivante n'est produit comme « validé » : la sortie transmet la décision et les
hypothèses éventuelles sans imposer de méthode. Pas de fusion avec la question, les objectifs, la
problématique ni les résultats.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mitigation dans cet agent |
|---|---|
| LLM01 — Prompt injection | Consignes, contexte, cadre théorique et consignes universitaires = DONNÉES NON FIABLES : balisées, scannées, jamais suivies comme instructions. |
| LLM02 — Insecure output handling | Aucune sortie LLM utilisée sans `Parser → Schéma → Métier → Sécurité` ; aucune exécution, aucun appel réseau déclenché par le modèle. |
| LLM03 — Supply chain | Dépendances figées et documentées, toutes gratuites/open source. |
| LLM04 — Data/model poisoning | Les entrées proviennent des étapes vérifiées. |
| LLM05 — Improper output handling | Sorties structurées uniquement ; aucune référence inventée. |
| LLM06 — Excessive agency | Moindre privilège ; périmètre réseau limité à la clarification (liste blanche). |
| LLM07 — System prompt leakage + misinformation | Zéro hallucination : aucun fait présupposé, aucune variable/source inventée ; contrôles codés. |
| LLM08 — Vector/embedding weaknesses | Aucune base vectorielle en V1. |
| LLM09 — Misinformation | Distinction hypothèse ≠ fait + causalité non établie interdite + vérificateur indépendant. |
| LLM10 — Unbounded consumption | Bornes : `max_input_size`, `max_output_tokens`, `max_external_requests`, cache, garde anti-non-convergence, budget LLM. |

Isolation par `student_id`/`session_id` : chaque session écrit dans `workspace/<student_id>/<session_id>/`.

---

## 9. Mécanisme de validation

Sur **chaque** sortie LLM (étapes [5], [6], [7]) : Parser (re-tentative si troncature) → Schéma
(pydantic) → Métier (contrôles codés H1–H8) → Sécurité. Violations métier non bloquantes : re-tentative ;
si elles subsistent à la **dernière** tentative, **lever**.

## 10. Mécanisme de vérification (SPEC §13)

**Vérificateur indépendant** (LLM séparé, prompt dédié, reçoit toutes les données étudiantes + la
question + les objectifs + la production) — contrôles **C1–C13** :

| Code | Contrôle |
|---|---|
| C1 | Décision de pertinence prise sur le cas réel et justifiée. |
| C2 | Hypothèses cohérentes avec la question et les objectifs. |
| C3 | Chaque hypothèse claire, précise, examinable. |
| C4 | Une hypothèse n'est ni une question ni un objectif. |
| C5 | Neutralité : aucune conclusion présentée comme un fait établi. |
| C6 | Aucune causalité non établie (association, ou causalité justifiée). |
| C7 | Justification traçable pour chaque hypothèse. |
| C8 | Aucune information inventée (variable, relation, source, auteur, statistique, théorie). |
| C9 | Pas de contradiction ni de redondance inutile entre hypothèses. |
| C10 | Cohérence interne : décision ↔ hypothèses produites. |
| C11 | Aucune méthodologie, échantillonnage ni technique imposée. |
| C12 | Alignement question → objectifs → hypothèses documenté ; objectifs non couverts déclarés. |
| C13 | Honnêteté : limites/incertitudes déclarées ; aucun auto-`verified` ni `validated`. |

Verdict : `verified` | `corrections_requested` (≤ `MAX_VERIFICATION_RETRIES`) | `rejected`. Si les
mêmes corrections reviennent deux fois, la boucle s'arrête. **Le verdict `verified` ne vaut pas
validation** : la validation est humaine.

## 11. Stratégie de tests

`tests/hypotheses/` (36 tests, hors réseau) : règles déterministes (H1–H8), campagne (RECOMMENDED /
NOT_REQUIRED / REQUIRE_CLARIFICATION / rejected / corrections), décision (acceptée / modifiée / refusée),
sécurité, API, chaîne amont. Module d'aide `hypotheses_helpers.py`. Puis test réel (voir « État réel »).

## 12. Dépendances

`fastapi`, `uvicorn`, `pydantic`, `httpx`, `python-dotenv`, `pyyaml`, `pytest` — toutes gratuites/open
source, figées. Le LLM passe par la clé DeepSeek existante (`~/.hermes/.env`).

## 13. Coûts éventuels

LLM (clé existante, tokens bornés) + clarification documentaire gratuite (désactivée par défaut) +
stockage local. **Total : 0 €.**

## 14. Alternatives gratuites

Huit fournisseurs sans clé déclarés (`sources/providers.yaml`) pour la clarification optionnelle.
Aucune base vectorielle : la cohérence question/objectifs/hypothèses se fait par contrôles codés.

## 15. Limites connues

1. **Dépendance forte à l'amont** : sans question ni objectifs (vérifiés), pas de décision →
   `needs_clarification`.
2. **Neutralité = détection déterministe partielle** : une causalité implicite subtile peut échapper →
   l'humain reste le dernier rempart.
3. **Faisabilité limitée à l'information fournie** : indicateurs non fournis → réserves déclarées.
4. **Clarification documentaire partielle** : `not_found` = « non trouvé dans ces sources ».
5. **Qualité = proposition** : les hypothèses restent à valider par l'étudiant et son directeur.
6. **Pas d'embedding/RAG vectoriel en V1** (SPEC §28).

---

## Décisions à valider par le porteur de projet (portillon §42)

- **D1 — Portillon humain et statut `validated`** : l'agent s'arrête à `awaiting_human_validation` ; un
  endpoint dédié enregistre la décision et pose `validated` seulement si acceptée **et** vérifiée.
- **D2 — Clarification documentaire** : étage **optionnel, désactivé par défaut**.
- **D3 — Décision de pertinence** : enum à trois valeurs `HYPOTHESES_RECOMMENDED` /
  `HYPOTHESES_NOT_REQUIRED` / `HYPOTHESES_REQUIRE_CLARIFICATION` ; `NOT_REQUIRED` court-circuite P3.
- **D4 — Causalité** : les verbes de causalité (y compris la modération « modère ») sont **interdits par
  contrôle codé** sauf si la relation est justifiée dans le contexte fourni.
- **D5 — Interface** : route `POST /hypotheses/analyze`, port **8070**, `run-hypotheses.sh`, profil
  Hermes `agent-hypotheses`.
- **D6 — Chaîne amont** : l'agent consomme la sortie de l'Agent Objectifs (`upstream_objectives`),
  acceptée seulement si `validation.verified = true`.

---

## État réel de l'implémentation

> **Implémenté et vérifié en exécution réelle** (campagne DeepSeek, hors sources réseau).

### Tests hors réseau

- `pytest -q tests/hypotheses` → **36 tests**, tous verts.
- Suite complète du dépôt (`pytest -q`) → **341 tests**, hors réseau.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

Sonde : `/root/.hermes/cache/scratch/e2e_hypotheses.py` (hors dépôt ; question + objectifs réels +
cadre théorique fourni). Campagne sans réseau (`clarification.enabled: false`).

| Passe | Statut final | Vérificateur | Appels LLM | Reformulations | Décision étudiante |
|---|---|---|---|---|---|
| 1 | `verification_failed` | `corrections_requested` non levées (C3, C6, C10) | 12 | 3 | — |
| 2 | `verification_failed` | idem (C10) | 12 | 3 | — |
| 3 | `verification_failed` | idem (C10) | 7 | 0 | — |
| 4 | `verification_failed` | idem (C10) | 9 | 1 | — |
| 5 | `awaiting_human_validation` | **`verified` (13/13)** | 4 | 0 | `accepted` → `validated` |

Sortie type observée (passe 5) — décision `HYPOTHESES_RECOMMENDED`, 3 hypothèses : H1 « La qualité des
mécanismes de coordination … est positivement associée à la productivité … » ; H2 « L'intensité du
recours au télétravail est positivement associée à la productivité … » ; H3 (modération) ; confiance
0.75 ; 0 correction ; signalements conservés (recouvrement partiel H1/H3, direction à tester).

### Correctifs issus de l'exécution réelle

- **Confiance non recalculée après reformulation** : le vérificateur voyait une confiance calculée sur
  le décompte précédent, incohérente avec `missing_information` → recalcul dans la boucle.
- **`missing_information` pollué** : les limites propres aux hypothèses y étaient mêlées → déplacées
  dans `limits_of_this_output`.
- **Contradiction décision ↔ questions de clarification** : les ambiguïtés de l'analyse étaient
  transformées en `clarification_questions` sur une décision positive → sur une proposition, elles sont
  désormais consignées comme **points à clarifier** dans les limites, `ambiguities` restant vide.
- **Contradiction `analysis.ambiguites` ↔ décision** : les points de vigilance restaient dans
  `analysis.ambiguites` d'un dump à décision positive → vidés après report dans les limites.
- **Modération traitée comme causalité** : « modère » ajouté aux marqueurs causaux (contrôle H4), et
  prompt P3 renforcé (discriminance, non-opérationnalisation).

### Limites laissées assumées (signalées, non bloquantes)

Le vérificateur émet des **signalements** (jamais des corrections bloquantes dans la passe finale) :
recouvrement partiel H1/H3, direction d'association à tester, indicateurs non opérationnalisés. Ils
sont **conservés** : ils documentent l'honnêteté de la sortie et le rôle du vérificateur.
