# Architecture V1 — Agent Diagnostic méthodologique (`methodology_diagnostic_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points).
> Référentiel : `docs/spec-agent-08-diagnostic-methodologique.md` (SPEC reçue).
> Éléments de l'agent : `docs/elements-agent-08-diagnostic-methodologique.md` (profil Hermes
> `agent-methodologie` + paquet `src/methodology_diagnostic_agent/`). **Cadre autonome** : aucun agent
> existant n'est modifié et aucun code n'est partagé avec eux (duplication contrôlée assumée).
> ✅ **Architecture contresignée par le porteur de projet le 2026-10-09** (portillon §42).

---

## 1. Architecture

Un **pipeline de diagnostic méthodologique** : analyse du dossier → proposition argumentée des six
catégories → contrôles déterministes de cohérence et de faisabilité → vérificateur indépendant →
**portillon humain** obligatoire. Principe conservé des agents précédents : *aucune sortie LLM utilisée
avant Parser → Schéma → Métier → Sécurité*, et *le modèle ne déclenche jamais lui-même une requête
réseau*.

```
ÉTUDIANT (sujet, problème, problématique, question, objectifs, hypothèses, données/terrain/contraintes)
   │
   ▼
[1] Input Controller          ── student_id/session_id + snapshots amont vérifiés
[2] Input Validation          ── contrat d'entrée, tailles, champs obligatoires
[3] Security Layer            ── entrées étudiantes + consignes = DONNÉES NON FIABLES (balisage + scan)
   │
   ▼
[4] PRÉ-CADRAGE (déterministe) ── sujet ET question de recherche présents ? si non → status
   │     `needs_clarification` + questions ciblées, AUCUNE production lancée
   ▼
[5] LLM P1 — ANALYSE DU DOSSIER : phénomène, visée réelle, nature du travail, éléments
   │        disponibles/manquants (BLOQUANTS), contradictions, provenance
[6] LLM P2 — DIAGNOSTIC : les SIX catégories distinctes (approche, logique de raisonnement, type de
   │        recherche, stratégie, techniques de collecte, méthodes d'analyse) ; chacune avec
   │        proposition, justification, alternatives, conditions, limites ; articulation ; réponse à la
   │        question ; hypothèses examinables ; contrôles de faisabilité ; inconnues ; limites ; questions
[7] CONTRÔLES DÉTERMINISTES (M1–M7) ── codes canoniques (M1), justification de chaque choix (M2),
   │        anti-fusion des catégories (M3), causalité sans dispositif (M4), compatibilité
   │        approche ↔ collecte et analyse (M5), conditions de la stratégie / collecte non vide (M6),
   │        hypothèses du dossier traitées (M7) — avec boucle de re-tentative correctrice
[8] ASSEMBLAGE (déterministe) ── provisoire DÉCLARÉ, `missing_information` dérivée, récapitulatif des
   │        alternatives, contrôles de cohérence lisibles, outils/documents réellement consultés,
   │        confiance calculée terme à terme
[9] CLARIFICATION DOCUMENTAIRE (déterministe, OPTIONNELLE, bornée) ── lever une ambiguïté
   │        terminologique via API publiques gratuites sans clé ; jamais déclenchée par le modèle
[10] Parser → Schéma → Métier (R1–R5) → Sécurité   (sur CHAQUE sortie LLM des étapes [5] et [6])
   ▼
[11] VÉRIFICATEUR INDÉPENDANT (LLM séparé) ── contrôles C1–C13 ; sortie elle-même validée
   │     verified | corrections_requested (≤ MAX_VERIFICATION_RETRIES) | rejected
   │     → pose `verification_result` (jamais `validated`)
   ▼
[12] PORTILLON HUMAIN — status `awaiting_human_validation`
   │     l'étudiant / l'encadreur ACCEPTE / MODIFIE / REFUSE
   ▼
[13] DÉCISION ÉTUDIANTE → pose `student_validation` ; si acceptée ET vérifiée → status `validated`
[14] Persistance + audit + réponse HTTP (transmission à l'Agent 9 — Méthodologie)
```

Points non négociables :
- **Moindre privilège** : `read: session_only` + recherche publique autorisée, `write:
  workspace_only`, `delete/deploy/send: false`.
- **Six catégories distinctes** : approche ≠ logique ≠ type ≠ stratégie ≠ collecte ≠ analyse ; un
  contrôle codé (M3) refuse deux catégories formulées de la même façon.
- **Causalité** : aucune lecture causale sans dispositif expérimental (contrôle codé M4) ; une causalité
  **niée** (« sans prétendre à une causalité ») n'est pas une causalité affirmée.
- **Diagnostic PROVISOIRE déclaré** : dès qu'une information manque ou qu'une inconnue est déclarée, le
  diagnostic est marqué provisoire (R3) — jamais présenté comme définitif.
- **Aucune méthode imposée** : alternatives, conditions et limites exposées ; l'agent ne tranche pas à
  la place de l'étudiant.
- **0 €** : clarification documentaire sur fournisseurs gratuits sans clé uniquement (voir §13).

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings-methodologie.yaml             # propre à l'agent (LLM, bornes, chemins, clarification)
├── docs/
│   ├── spec-agent-08-diagnostic-methodologique.md        # SPEC reçue (déposée)
│   ├── architecture-agent-08-diagnostic-methodologique-v1.md  # ce document
│   └── elements-agent-08-diagnostic-methodologique.md    # fiche des 19 éléments
├── src/methodology_diagnostic_agent/          # paquet AUTONOME
│   ├── main.py  api/routes.py                 # FastAPI : /methodology/analyze, .../decision, GET, /health
│   ├── pipeline/
│   │   ├── input_controller.py input_validation.py prerequisites.py security_layer.py campaign.py
│   │   ├── analysis_stage.py                  # LLM P1 (analyse du dossier)
│   │   ├── diagnosis_stage.py                 # LLM P2 (diagnostic)
│   │   ├── diagnosis_checks.py                # M1–M7 (déterministe)
│   │   ├── clarification_stage.py decision_stage.py output_parser.py schema_validation.py
│   │   ├── business_validation.py             # R1–R5 (déterministe)
│   │   ├── security_validation.py verifier.py llm_stage.py
│   ├── analysis/methodology_rules.py          # énumérations des six catégories, causalité, compatibilité
│   ├── sources/                               # providers.yaml, registry, http, cache, adapters/
│   ├── schemas/                               # input analysis methodology decision output verifier stages common
│   ├── core/                                  # config limits errors logging sessions security_rules
│   ├── storage/                               # workspace, audit
│   └── llm/                                   # client + prompts (p1, p2, verifier)
├── run-methodologie.sh                        # port 8080
├── workspace/                                 # audit-methodologie.db, methodologie-cache.db, <student>/<session>/
└── tests/methodologie/                        # règles, campagne, décision, sécurité, API, chaîne amont
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `pipeline/prerequisites.py` | Pré-cadrage (SPEC §5, §14) : **sujet ET question de recherche** essentiels (champ direct ou `upstream_*.validation.verified`). Manque essentiel → `needs_clarification`, AVANT tout appel LLM. |
| `pipeline/analysis_stage.py` | LLM P1 : phénomène, visée RÉELLE, nature du travail, éléments disponibles/manquants, contradictions, provenance. |
| `pipeline/diagnosis_stage.py` | LLM P2 : les six catégories avec proposition/justification/alternatives/conditions/limites + articulation + réponse à la question. |
| `analysis/methodology_rules.py` | Cœur déterministe : énumérations canoniques, normalisation tolérante, marqueurs causaux (avec fenêtre de négation en mots), compatibilité approche ↔ collecte ET approche ↔ analyse, anti-fusion. |
| `pipeline/diagnosis_checks.py` | Applique `methodology_rules` (M1–M7) avec boucle de re-tentative correctrice ; la campagne lève si les violations subsistent après la DERNIÈRE tentative. |
| `pipeline/business_validation.py` | R1–R5 : socle fourni (sujet + question), cohérence du statut de diagnostic, provisoire déclaré si manques, anti auto-vérification, `validated` réservé au portillon humain. |
| `pipeline/decision_stage.py` | Portillon humain : accepté (exige `verified`) → `validated` ; modifié → contrôles M1–M7 puis re-vérification ; refusé → `blocked`. |
| `pipeline/campaign.py` | Orchestrateur ; agrège les alternatives déjà proposées, vide `analysis.elements_manquants` (déplacés vers `missing_information`), calcule la confiance terme à terme. |

---

## 4. Flux des données

```
POST /methodology/analyze
  body: { student_id, session_id?, subject_text, research_problem, validated_problematic,
          main_research_question, secondary_research_questions?[], general_objective,
          specific_objectives?[], hypotheses?[], literature_review, discipline, academic_level,
          country, geographical_area, study_period, target_population, research_context,
          available_data, field_access, available_resources, existing_methodology,
          previous_answers?[], student_constraints?, university_instructions?,
          supervisor_instructions?, language_prefs?, constraints?,
          upstream_subject?, upstream_problem?, upstream_problematic?, upstream_question?,
          upstream_objectives?, upstream_hypotheses (vérifiés) }
   │
   ├─ Input Controller → session ; snapshots amont acceptés SEULEMENT si `validation.verified`
   ├─ Input Validation → 422 INVALID_INPUT si non conforme
   ├─ Security Layer   → balisage non fiable
   ├─ Pré-cadrage      → sujet/question absents ? → 200 `needs_clarification`, FIN
   │
   ├─ LLM P1 → analyse du dossier                 → Parser → Schéma → Métier → Sécurité
   ├─ LLM P2 → diagnostic (six catégories)        → Parser → Schéma → Métier → Sécurité
   ├─ Contrôles déterministes M1–M7               → violations ? re-tentative ; sinon lever
   ├─ Assemblage                                  → provisional, missing_information, alternatives, confiance
   ├─ Clarification documentaire (optionnelle)    → concept vérifié ou `unavailable` (déclaré)
   ├─ Validations métier R1–R5 + sécurité (toutes sorties)
   ├─ VÉRIFICATEUR INDÉPENDANT                    → verified | corrections_requested | rejected
   └─ Persistance + audit
        → 200 { status: "awaiting_human_validation", diagnostic_status, diagnostic, fécondité… }

POST /methodology/{student_id}/{session_id}/decision
  body: { decision: "accepted"|"modified"|"refused", student_comment?, provided_information?, modified? }
   ├─ accepted + verified → `validated` (provisional=false) ; refused → `blocked`
   └─ modified → contrôles M1–M7 puis re-vérification
```

---

## 5. Modèle de données

| Objet | Champs principaux | Remarques |
|---|---|---|
| `DossierAnalysis` | `phenomene`, `visee`, `nature_du_travail`, `elements_disponibles[]`, `elements_manquants[]`, `contradictions[]`, `provenance` | Les éléments manquants sont **bloquants** |
| `MethodologyDiagnosis` | `approche`, `logique`, `type_recherche`, `strategie` (CategoryCode) + `collecte[]`, `analyse[]` ; `articulation` ; `coherence_question` | Six catégories **distinctes** |
| `CategoryCode` | `code`, `proposition`, `justification`, `alternatives[]`, `conditions[]`, `limites[]` | Un choix = proposition + justification + alternatives + conditions + limites |
| `diagnostic_status` | enum {provisoire, en_attente_de_validation, valide, a_reviser} | Distinct du `status` de pipeline |
| `Ambiguity` | `description`, `impact`, `clarification_question` | Alimente le human gate |
| `SourceEvidence` | `query`, `provider`, `source_id`, `title`, `url`, `used` | Clarification documentaire bornée |
| `VerificationResult` | `verified: bool`, `verifier_status` | Posé par le vérificateur uniquement |
| `StudentValidation` | `decision` ∈ {accepted, modified, refused}, `comment`, `at` | Posé par l'endpoint de décision |
| `Confidence` | `overall`, `rationale` | Dérivée des preuves ; rationale qui ÉNONCE le calcul |
| `Evidence` | `llm_calls`, `network_requests`, `reformulations` | Preuve d'honnêteté |
| `MethodologyOutput` | dossier de preuve SPEC §16 + `unknowns[]`, `limits_of_this_output[]`, `questions_for_human[]`, `alternatives_overview[]`, `coherence_controls[]`, `feasibility_controls[]` | `missing_information` (bloquant) ≠ `unknowns` (non bloquant) |

---

## 6. Contrat d'entrée (SPEC §6)

| Champ | Type | Requis | Provenance |
|---|---|---|---|
| `student_id` | string | oui | fourni |
| `subject_text` | string | oui (ou amont vérifié) | fourni |
| `main_research_question` | string | oui (ou amont vérifié) | fourni |
| `discipline`, `academic_level` | string | non (mais attendus) | fourni |
| `research_problem`, `validated_problematic`, `literature_review` | string | non | fourni / amont |
| `general_objective` / `specific_objectives[]`, `hypotheses[]` | string / array | non | fourni / amont |
| `country`, `geographical_area`, `study_period`, `target_population`, `research_context` | string | non | fourni |
| `available_data`, `field_access`, `available_resources`, `existing_methodology` | string | non | fourni (déterminants pour la faisabilité) |
| `previous_answers` | array | non | réponses antérieures |
| `student_constraints`, `university_instructions`, `supervisor_instructions` | string | non | fourni (données non fiables) |
| `upstream_subject/problem/problematic/question/objectives/hypotheses` | object | non | acceptés si `validation.verified = true` |
| `constraints` | string | non | bornes de session |

Taille maximale : 40000 caractères. Un amont non vérifié ⇒ `422` / `MISSING_INFORMATION`.

---

## 7. Contrat de sortie (SPEC §16)

```json
{
  "agent": "methodology_diagnostic_agent",
  "version": "1.0",
  "status": "needs_clarification | ready_for_verification | verification_failed | awaiting_human_validation | blocked | validated",
  "research_id": "<student_id>/<session_id>",
  "generated_at": "…",
  "diagnostic_status": "provisoire | en_attente_de_validation | valide | a_reviser",
  "provisional": true,
  "subject": "…", "main_research_question": "…", "secondary_research_questions": [],
  "general_objective": "…", "specific_objectives": [], "hypotheses_examined": [], "resume": "…",
  "analysis": { "phenomene": "…", "visee": "…", "nature_du_travail": "…",
                "elements_disponibles": [], "elements_manquants": [], "contradictions": [],
                "provenance": "provided" },
  "diagnosis": {
    "approche":       { "code": "quantitative", "proposition": "…", "justification": "…",
                        "alternatives": [], "conditions": [], "limites": [] },
    "logique":        { "code": "hypothetico_deductive", "proposition": "…", "justification": "…",
                        "alternatives": [], "conditions": [], "limites": [] },
    "type_recherche": { "code": "explicative", "proposition": "…", "justification": "…",
                        "alternatives": [], "conditions": [], "limites": [] },
    "strategie":      { "code": "enquete", "proposition": "…", "justification": "…",
                        "alternatives": [], "conditions": [], "limites": [] },
    "collecte": [ { "code": "", "proposition": "…", "justification": "…",
                    "alternatives": [], "conditions": [], "limites": [] } ],
    "analyse":  [ { "code": "", "proposition": "…", "justification": "…",
                    "alternatives": [], "conditions": [], "limites": [] } ],
    "articulation": "…", "coherence_question": "…"
  },
  "alternatives_overview": [], "coherence_controls": [], "feasibility_controls": [],
  "missing_information": [], "ambiguities": [], "tools_and_documents": [],
  "questions_for_human": [], "source_evidence": [],
  "verification_result": { "verified": false, "verifier_status": "pending" },
  "student_validation": { "decision": null, "comment": "", "at": null },
  "confidence": { "overall": 0.5, "rationale": "…calcul…" },
  "clarification_questions": [], "limits_of_this_output": [], "unknowns": [],
  "evidence": { "llm_calls": 0, "network_requests": 0, "reformulations": 0 }
}
```

Aucun champ de l'étape suivante n'est produit comme « validé » : la sortie transmet un diagnostic
argumenté sans rédiger la méthodologie finale. Pas de fusion avec la question, les objectifs ni les
hypothèses.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mitigation dans cet agent |
|---|---|
| LLM01 — Prompt injection | Consignes, contexte, littérature et consignes universitaires = DONNÉES NON FIABLES : balisées, scannées, jamais suivies comme instructions. |
| LLM02 — Insecure output handling | Aucune sortie LLM utilisée sans `Parser → Schéma → Métier → Sécurité` ; aucune exécution, aucun appel réseau déclenché par le modèle. |
| LLM03 — Supply chain | Dépendances figées et documentées, toutes gratuites/open source. |
| LLM04 — Data/model poisoning | Les entrées proviennent des étapes vérifiées (`validation.verified` exigé). |
| LLM05 — Improper output handling | Sorties structurées uniquement ; aucune donnée ni référence inventée. |
| LLM06 — Excessive agency | Moindre privilège ; périmètre réseau limité à la clarification (liste blanche, borné). |
| LLM07 — System prompt leakage + misinformation | Zéro hallucination ; cas de causalité niée corrigés (M4) ; contrôles codés. |
| LLM08 — Vector/embedding weaknesses | Aucune base vectorielle en V1. |
| LLM09 — Misinformation | Distinction approche/logique/type/stratégie + causalité interdite sans dispositif + diagnostic provisoire déclaré + vérificateur indépendant. |
| LLM10 — Unbounded consumption | Bornes : `max_input_size`, `max_output_tokens`, `max_external_requests`, cache, garde anti-non-convergence, budget LLM. |

Isolation par `student_id`/`session_id` : chaque session écrit dans `workspace/<student_id>/<session_id>/`.

---

## 9. Mécanisme de validation

Sur **chaque** sortie LLM (étapes [5], [6]) : Parser (re-tentative si troncature) → Schéma (pydantic) →
Métier (contrôles codés M1–M7 puis R1–R5) → Sécurité. Violations métier non bloquantes : re-tentative ;
si elles subsistent à la **dernière** tentative, **lever**.

## 10. Mécanisme de vérification (SPEC §13)

**Vérificateur indépendant** (LLM séparé, prompt dédié, reçoit tout le dossier + la production) —
contrôles **C1–C13** :

| Code | Contrôle |
|---|---|
| C1 | Sujet, question et objectifs pris en compte ; la méthode permet de répondre à la question. |
| C2 | Les six catégories sont DISTINCTES (approche, logique, type, stratégie, collecte, analyse). |
| C3 | Chaque choix important justifié par le sujet PRÉCIS (et non par la seule discipline). |
| C4 | Alternatives pertinentes exposées ; aucune méthode imposée. |
| C5 | Aucune causalité sans dispositif adéquat ; association, explication et causalité non confondues. |
| C6 | Cohérence approche ↔ méthodes d'analyse. |
| C7 | Faisabilité examinée (terrain, temps, budget, données) ; limites déclarées. |
| C8 | Les hypothèses du dossier peuvent être examinées par la méthodologie proposée. |
| C9 | Aucune information inventée (donnée, référence, ressource, accès au terrain, résultat). |
| C10 | Aucune méthodologie finale rédigée : c'est un diagnostic, pas la section méthodologie. |
| C11 | Le diagnostic provisoire est DÉCLARÉ provisoire ; les informations manquantes signalées. |
| C12 | Rapport compréhensible ; dossier de preuve (outils/documents réellement consultés) honnête. |
| C13 | Honnêteté : limites, incertitudes, questions à valider déclarées ; aucun auto-`verified`/`validated`. |

Verdict : `verified` | `corrections_requested` (≤ `MAX_VERIFICATION_RETRIES`) | `rejected`. Si les
mêmes corrections reviennent deux fois, la boucle s'arrête. **Le verdict `verified` ne vaut pas
validation** : la validation est humaine.

## 11. Stratégie de tests

`tests/methodologie/` (49 tests, hors réseau) : règles déterministes (M1–M7, causalité niée, cohérence
approche ↔ collecte), campagne (nominal, provisoire, échec, corrections), décision (acceptée / modifiée /
refusée), sécurité, API, chaîne amont. Module d'aide `methodologie_helpers.py`. Puis test réel (voir
« État réel »).

## 12. Dépendances

`fastapi`, `uvicorn`, `pydantic`, `httpx`, `python-dotenv`, `pyyaml`, `pytest` — toutes gratuites/open
source, figées. Le LLM passe par la clé DeepSeek existante (`~/.hermes/.env`).

## 13. Coûts éventuels

LLM (clé existante, tokens bornés) + clarification documentaire gratuite (désactivée par défaut) +
stockage local. **Total : 0 €.**

## 14. Alternatives gratuites

Huit fournisseurs sans clé déclarés (`sources/providers.yaml`) pour la clarification optionnelle.
Aucune base vectorielle : la cohérence du dossier se contróle par règles codées.

## 15. Limites connues

1. **Dépendance forte à l'amont** : sans sujet ni question (vérifiés), pas de diagnostic →
   `needs_clarification`.
2. **Provisoire fréquent** : dès qu'une information manque (données, accès, ressources), le diagnostic
   reste provisoire et déclaré — c'est voulu.
3. **Neutralité = détection déterministe partielle** : une causalité implicite subtile peut échapper →
   l'humain reste le dernier rempart.
4. **Clarification documentaire partielle** : `not_found` = « non trouvé dans ces sources ».
5. **Qualité = proposition** : le diagnostic reste à valider par l'étudiant et son encadreur.
6. **Pas d'embedding/RAG vectoriel en V1** (SPEC §28).

---

## Décisions à valider par le porteur de projet (portillon §42)

- **D1 — Portillon humain et statut `validated`** : l'agent s'arrête à `awaiting_human_validation` ; un
  endpoint dédié enregistre la décision et pose `validated` seulement si acceptée **et** vérifiée.
- **D2 — Clarification documentaire** : étage **optionnel, désactivé par défaut**.
- **D3 — Six catégories** : énumérations canoniques fixes (`approche`, `logique`, `type_recherche`,
  `strategie`), la valeur `autre` restant possible et justifiée.
- **D4 — Causalité** : interdite par contrôle codé (M4) sauf dispositif expérimental (stratégie =
  `experimentation`) ; une causalité **niée** ne déclenche pas la règle.
- **D5 — Séparation `missing_information` / `unknowns`** : manques **bloquants** vs inconnues **non
  bloquantes**, deux listes distinctes par conception (règle R3). **Ne pas fusionner** — divergence
  signalée au porteur, non tranchée.
- **D6 — Interface** : route `POST /methodology/analyze`, port **8080**, `run-methodologie.sh`, profil
  Hermes `agent-methodologie`.
- **D7 — Chaîne amont** : l'agent consomme les sorties des agents 1–7 (`upstream_*`), acceptées seulement
  si `validation.verified = true`.

---

## État réel de l'implémentation

> **Implémenté et vérifié en exécution réelle** (campagne DeepSeek, hors sources réseau).

### Tests hors réseau

- `pytest -q tests/methodologie` → **49 tests**, tous verts.
- Suite complète du dépôt (`pytest -q`) → **390 tests**, hors réseau.

### Résultats en exécution réelle (modèle DeepSeek `deepseek-flash`)

Sonde : `/root/.hermes/cache/scratch/e2e_methodologie.py` (hors dépôt ; dossier complet — sujet, question,
objectifs, hypothèses, données/terrain/contraintes). Campagne sans réseau (`clarification.enabled: false`).

| Passe | Statut final | Vérificateur | Appels LLM | Reformulations | Décision étudiante |
|---|---|---|---|---|---|
| 1 | `verification_failed` | échec M4 (causalité DENIÉE comptée à tort) | 3 | 0 | — |
| 2 | `verification_failed` | corrections non levées (champs jamais remplis) | 3 | 0 | — |
| 3 | `awaiting_human_validation` | **`verified` (13/13)** | 3 | 0 | `accepted` → `validated` |

Sortie type observée (passe finale) — approche `mixte` (à dominante quantitative), logique
`hypothetico_deductive`, type `explicative`, stratégie `enquete` ; collecte questionnaire + entretiens
semi-directifs ; analyse descriptive, bivariée (associations) et thématique ; 2 hypothèses examinées ;
diagnostic `provisoire` (7 inconnues déclarées), confiance 0,50 avec calcul explicité ; 0 correction,
signalements conservés.

### Correctifs issus de l'exécution réelle

- **Chaîne A7 → A8 (bug réel trouvé et corrigé)** : les sorties réelles des agents 5-7 portent la
  vérification dans `verification_result`, alors que l'entrée de l'agent 8 n'acceptait que `validation`
  (clé des agents 1-4) → toute sortie réelle des agents 5-7 était déclarée « non vérifiée »
  (`MISSING_INFORMATION`). L'entrée accepte désormais les deux formes ; 2 tests de non-régression, dont
  l'ingestion du fichier réel `hypotheses_output.json`.
- **Cohérence approche ↔ collecte (M5 étendu)** : le vérificateur a relevé « un volet entretiens est
  listé alors que l'approche est déclarée quantitative mono-méthode ». M5 contrôle désormais aussi les
  techniques de **collecte** : une approche mono-méthode ne peut pas mêler collecte qualitative et
  quantitative → il faut déclarer l'approche **« mixte »**. Prompt P2 aligné.
- **Libellés de cohérence lisibles par l'étudiant** : `coherence_controls` exposait des codes internes
  (« M1–M3 : contrôle déterministe ») — signalé par le vérificateur comme « peu lisibles ». Reformulés en
  français clair, sans code interne.
- **M4 — causalité niée (faux positif)** : `causal_hits` cherchait « causalite » en sous-chaîne, donc une
  phrase qui **écarte** la causalité (« sans prétendre à une causalité (aucun dispositif expérimental) »)
  déclenchait la règle ; le modèle ne pouvait pas « corriger » une phrase juste → la campagne levait.
  Corrigé par une fenêtre de NÉGATION mesurée en MOTS (4 avant / 3 après).
- **Champs jamais remplis** : `unknowns` et `alternatives_overview` existaient dans le schéma sans source
  (ni contrat du modèle, ni pipeline). `unknowns` ajouté au contrat P2 et au prompt ; `alternatives_overview`
  obtenu par AGRÉGATION déterministe des alternatives déjà proposées.
- **`provisional` incohérent** : restait `False` face à un résumé qui annonçait un « diagnostic
  provisoire » → rendu provisoire dès qu'une inconnue est déclarée.
- **Rationale de confiance** : annonçait « 0 information manquante » en contradiction avec les inconnues et
  donnait un `overall` nu → annonce désormais les inconnues ET le calcul terme à terme.

### Limites laissées assumées (signalées, non bloquantes)

Le vérificateur émet des **signalements** (jamais des corrections bloquantes dans la passe finale) :
séparation `missing_information`/`unknowns` (deux listes par conception, règle R3), `clarification_questions`
vs `questions_for_human`, faisabilité d'une régression multiple avec un simple tableur, rattachement de
`analysis.contradictions` aux limites. Ces divergences relèvent du **choix de conception** : elles sont
signalées au porteur, pas tranchées par l'agent.
