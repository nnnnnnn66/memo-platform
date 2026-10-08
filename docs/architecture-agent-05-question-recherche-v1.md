# Architecture V1 — Agent Question de recherche (`research_question_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points). **Implémentation faite et vérifiée en exécution
> réelle le 2026-10-09** : campagne réelle (modèle DeepSeek) jusqu'au verdict du vérificateur —
> `awaiting_human_validation`, vérificateur `verified` (12/12 contrôles), puis décision étudiante
> `validated`. Suite : `pytest -q` = 269 tests, hors réseau.
> Référentiel : `docs/spec-agent-05-question-recherche.md` (SPEC reçue).
> Éléments de l'agent : `docs/elements-agent-05-question-recherche.md` (profil Hermes
> `agent-question` + paquet `src/research_question_agent/`). **Cadre autonome** : aucun agent
> existant n'est modifié et aucun code n'est partagé avec eux.
> ⚠️ Architecture à contresigner par le porteur de projet.

---

## 1. Architecture

Un **pipeline de formulation de question** en étapes, chacune suivie d'une validation déterministe,
d'un **contrôle de neutralité** codé (pas seulement demandé au modèle) et d'un **portillon humain**
obligatoire. Principe conservé des agents précédents : *aucune sortie LLM utilisée avant
Parser → Schéma → Métier → Sécurité*, et *le modèle ne déclenche jamais lui-même une requête réseau*.

```
ÉTUDIANT (sujet validé, problème, problématique validée, contraintes, consignes)
   │
   ▼
[1] Input Controller          ── student_id/session_id + snapshots amont (sujet, problème, problématique)
[2] Input Validation          ── contrat d'entrée, tailles, champs obligatoires
[3] Security Layer            ── entrées étudiantes + consignes = DONNÉES NON FIABLES (balisage + scan)
   │
   ▼
[4] PRÉ-CADRAGE (déterministe) ── problématique VALIDÉE présente et vérifiée ? délimitation de base ?
   │     non → status `needs_clarification` + questions ciblées, AUCUNE formulation lancée
   │     oui → suite
   ▼
[5] LLM P1 — COMPRÉHENSION DE LA PROBLÉMATIQUE : phénomène, objet central, population/zone/période
   │        (si connues), ce qui reste à examiner + provenance (fourni / déduit / inconnu)
[6] LLM P2 — INTENTION DE RECHERCHE : décrire | comprendre | explorer | expliquer | comparer |
   │        mesurer | évaluer | examiner_evolution | identifier_facteurs … + justification
   │        INTENTION ≠ MÉTHODE (aucune approche/logique de raisonnement imposée)
[7] CONTRÔLE D'INTENTION (déterministe) ── l'intention découle-t-elle bien de la problématique ?
   │     plusieurs intentions possibles et divergentes → question de clarification (human gate)
[8] LLM P3 — FORMULATION : question principale (unique) + questions secondaires ÉVENTUELLES
   │        + rationale de formulation + périmètre/limites + évaluation de faisabilité
[9] CONTRÔLES DÉTERMINISTES DE FORMULATION ── neutralité (présupposés, réponse suggérée), question
   │        double, question trop large, délimitation ajoutée sans source, anti-fusion (≠ problématique,
   │        ≠ sujet), non-décision méthodologique
[10] CLARIFICATION DOCUMENTAIRE (déterministe, OPTIONNELLE, bornée) ── vérifier un concept/terme
   │        ambigu via API publiques gratuites sans clé ; jamais déclenchée par le modèle.
   │        Désactivée par défaut (0 requête) ; activable en configuration.
[11] Parser → Schéma → Métier → Sécurité   (sur CHAQUE sortie LLM des étapes [5], [6], [8])
   ▼
[12] VÉRIFICATEUR INDÉPENDANT (LLM séparé) ── contrôles C1–C12 ; sortie elle-même validée
   │     verified | corrections_requested (≤ MAX_VERIFICATION_RETRIES) | rejected
   │     → pose `verification_result` (jamais `validated`)
   ▼
[13] PORTILLON HUMAIN — status `awaiting_human_validation`
   │     l'étudiant ACCEPTE / MODIFIE / REFUSE + commentaire  (endpoint de décision)
   ▼
[14] DÉCISION ÉTUDIANTE → pose `student_validation` ; si acceptée ET vérifiée → status `validated`
[15] Persistance + audit + réponse HTTP (transmission à l'Agent Objectifs)
```

Points non négociables :
- **Moindre privilège** : `read: session_only` + recherche publique autorisée, `write:
  workspace_only`, `delete/deploy/send: false`.
- **Neutralité structurelle** : un contrôle codé cherche les présupposés (« pourquoi X est-il
  inefficace ? » sans inefficacité établie) ; un présupposé non établi déclenche une reformulation
  neutre ou une question de clarification — jamais une validation silencieuse.
- **Anti-fusion** : la question de recherche reste un champ distinct de la problématique et du
  sujet ; l'agent ne réécrit pas la problématique et ne crée pas un nouveau problème.
- **Intention ≠ méthode** : aucune logique (inductive/déductive) ni technique n'est décidée ici ; ce
  choix appartient aux étapes 8–9.
- **Honnêteté** : une délimitation indispensable absente, une information manquante ou un échec de
  clarification sont **déclarés** (`missing_information`, `ambiguities`), jamais comblés d'office.
- **0 €** : clarification documentaire sur fournisseurs gratuits sans clé uniquement (voir §13).

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings-question.yaml            # propre à l'agent (LLM, bornes, chemins, clarification)
├── docs/
│   ├── spec-agent-05-question-recherche.md              # SPEC reçue (déposée)
│   ├── architecture-agent-05-question-recherche-v1.md   # ce document
│   └── elements-agent-05-question-recherche.md          # fiche des 19 éléments
├── src/research_question_agent/          # paquet AUTONOME
│   ├── main.py                           # app FastAPI (lifespan, state)
│   ├── api/routes.py                     # POST /question/analyze, POST .../decision, GET ..., /health
│   ├── pipeline/
│   │   ├── input_controller.py           # session + snapshots amont
│   │   ├── input_validation.py           # contrat d'entrée, tailles
│   │   ├── prerequisites.py              # pré-cadrage SPEC §5/§12 (étape [4], déterministe)
│   │   ├── security_layer.py             # balisage + scan des entrées ET des consignes
│   │   ├── campaign.py                   # orchestrateur, points de reprise
│   │   ├── comprehension_stage.py        # LLM P1 (compréhension de la problématique)
│   │   ├── intention_stage.py            # LLM P2 (intention de recherche)
│   │   ├── intention_check.py            # étape [7] : cohérence intention ↔ problématique (déterministe)
│   │   ├── formulation_stage.py          # LLM P3 (question principale + secondaires + rationale)
│   │   ├── formulation_checks.py         # étape [9] : neutralité, double, largeur, délimitation, fusion
│   │   ├── clarification_stage.py        # étape [10] : clarification documentaire (déterministe, optionnelle)
│   │   ├── decision_stage.py             # étape [13-14] : décision étudiante → student_validation
│   │   ├── output_parser.py
│   │   ├── schema_validation.py
│   │   ├── business_validation.py        # orchestration des contrôles déterministes
│   │   ├── security_validation.py
│   │   └── verifier.py                   # vérificateur indépendant
│   ├── analysis/
│   │   ├── intent.py                     # enum canonique des intentions + rattachement
│   │   └── question_rules.py             # règles codées : neutralité, présupposés, délimitation
│   ├── sources/
│   │   ├── providers.yaml                # fournisseurs + hôtes autorisés (clarification)
│   │   ├── registry.py                   # sélection des fournisseurs + liste blanche
│   │   ├── http.py                       # client borné (timeout, taille, requêtes polies)
│   │   ├── cache.py                      # cache SQLite des requêtes (14 j)
│   │   └── adapters/                     # adaptateurs gratuits sans clé (repris en autonome)
│   │       └── openalex.py crossref.py hal.py theses_fr.py openaire.py datacite.py doaj.py europepmc.py
│   ├── schemas/
│   │   ├── input.py comprehension.py question.py decision.py output.py verifier.py
│   ├── core/
│   │   ├── config.py limits.py errors.py logging.py sessions.py security_rules.py
│   ├── storage/
│   │   ├── workspace.py                  # artefacts par session
│   │   └── audit.py                      # journal d'audit (SQLite)
│   └── llm/
│       ├── client.py                     # client LLM (clé héritée, budget, re-tentative)
│       └── prompts/
│           ├── p1_comprehension_system.md p2_intention_system.md p3_formulation_system.md
│           └── verifier_system.md
├── run-question.sh                       # port 8050
├── workspace/                            # audit-question.db, question-cache.db, <student>/<session>/
└── tests/question/                       # fonctionnels, neutralité, anti-fusion, clarification, human gate
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `pipeline/prerequisites.py` | Vérifie les prérequis (SPEC §5, §12) : sujet validé et **problématique validée + vérifiée** (`upstream_problematic.validation.verified = true`). Manque essentiel → `needs_clarification`, aucune formulation lancée. |
| `pipeline/comprehension_stage.py` | LLM P1 : dégage le phénomène, l'objet central, la population/zone/période (si connues) et ce qui reste à examiner, avec provenance (fourni / déduit / inconnu). |
| `pipeline/intention_stage.py` | LLM P2 : identifie l'intention de recherche dans l'enum canonique et la justifie **à partir de la problématique** ; ne décide jamais d'une méthode. |
| `pipeline/intention_check.py` | Contrôle déterministe : l'intention est-elle étayée par la problématique ? Plusieurs intentions divergentes possibles → question de clarification (human gate). |
| `pipeline/formulation_stage.py` | LLM P3 : rédige la question principale (unique) et, seulement si utile, des questions secondaires ; produit le rationale, le périmètre/limites et l'évaluation de faisabilité. |
| `analysis/question_rules.py` | Cœur anti-présupposé : détection codée des formulations qui supposent leur réponse (« pourquoi X est-il inefficace ? »), des questions doubles, des questions trop larges et des délimitations ajoutées sans source. |
| `pipeline/formulation_checks.py` | Applique `question_rules` + les contrôles anti-fusion (question ≠ problématique ≠ sujet) et non-décision méthodologique ; déclenche reformulation ou correction. |
| `pipeline/clarification_stage.py` | Étape optionnelle (désactivée par défaut) : vérifie un concept/terme ambigu via API publiques gratuites sans clé. **Aucun appel piloté par le modèle** ; un échec réseau est **déclaré**, jamais interprété comme une absence. |
| `pipeline/decision_stage.py` | Portillon humain : enregistre la décision de l'étudiant (acceptée / modifiée / refusée) et pose `student_validation` ; seule une décision acceptée **après** vérification donne `validated`. |
| `analysis/intent.py` | Enum canonique des intentions (décrire, comprendre, explorer, expliquer, comparer, mesurer, évaluer, examiner_evolution, identifier_facteurs) + normalisation (alias, casse, accents). |
| `sources/providers.yaml` | Fournisseurs de clarification déclarés en configuration (hôte autorisé). Ajouter un fournisseur gratuit = éditer ce fichier. |
| `pipeline/business_validation.py` | Orchestre les contrôles codés : neutralité, anti-présupposé, anti-fusion, délimitation, non-décision méthodologique, `status` honnête. |

---

## 4. Flux des données

```
POST /question/analyze
  body: { student_id, session_id?, subject_text, research_problem, research_problem_statement?,
          discipline, academic_level?, country?, geographical_area?, study_period?,
          target_population?, research_context?, literature_review?, research_question_draft?,
          student_constraints?, university_instructions?, supervisor_instructions?,
          previous_answers?, language_prefs?, upstream_subject?, upstream_problem?,
          upstream_problematic (OBLIGATOIRE, vérifié), constraints? }
   │
   ├─ Input Controller → session ; snapshots amont acceptés SEULEMENT si `validation.verified`
   ├─ Input Validation → 422 INVALID_INPUT si non conforme
   ├─ Security Layer   → balisage non fiable (consignes, observations, consignes universitaires)
   ├─ Pré-cadrage      → problématique non vérifiée / prérequis manquants ?
   │                     → 200 `needs_clarification` + questions, FIN
   │
   ├─ LLM P1 → compréhension                  → Parser → Schéma → Métier → Sécurité
   ├─ LLM P2 → intention de recherche          → Parser → Schéma → Métier
   ├─ Contrôle d'intention (déterministe)      → cohérente / ambiguë → clarification
   ├─ LLM P3 → question principale + secondaires → Parser → Schéma → Métier
   ├─ Contrôles de formulation (déterministes) → neutralité, double, largeur, délimitation, fusion
   ├─ Clarification documentaire (optionnelle) → concept vérifié ou `unavailable` (déclaré)
   ├─ Sécurité (toutes sorties)                → rien d'exécutable, aucune URL arbitraire
   ├─ VÉRIFICATEUR INDÉPENDANT                  → verified | corrections_requested | rejected
   └─ Persistance + audit
        → 200 { status: "awaiting_human_validation", question proposée, rationale, ambiguïtés, vérif. }

POST /question/{student_id}/{session_id}/decision
  body: { decision: "accepted"|"modified"|"refused", student_comment?, modified_question? }
   ├─ vérifie que la sortie précédente est `verified` et `awaiting_human_validation`
   ├─ pose `student_validation`
   └─ accepted + verified → `validated` ; modified → nouvelle formulation relancée ; refused → `blocked`
```

---

## 5. Modèle de données

| Objet | Champs principaux | Remarques |
|---|---|---|
| `Comprehension` | `phenomene`, `objet_central`, `population`, `zone`, `periode`, `reste_a_examiner`, `provenance` | `provenance` ∈ {provided, inferred, unknown} ; rien d'inventé |
| `ResearchIntention` | `intention` ∈ enum canonique, `justification`, `alternatives[]` | Intention ≠ méthode ; alternatives signalent une ambiguïté |
| `ResearchQuestion` | `main` (unique), `secondary[]`, `status` | Champ **distinct** de la problématique et du sujet |
| `FormulationRationale` | `texte`, `rattachement_problematique` | Le lien explicite question ↔ problématique |
| `ScopeAndBoundaries` | `geo`, `temps`, `population`, `added_without_source: bool` | Une délimitation ajoutée sans source est **déclarée** |
| `FeasibilityAssessment` | `verdict` ∈ {feasible, uncertain, not_feasible}, `raisons[]`, `manques[]` | dépend des contraintes/terrain connus |
| `MissingInformation` | `[]` | Informations indispensables non fournies |
| `Ambiguity` | `description`, `impact`, `clarification_question` | Alimente le human gate |
| `SourceEvidence` | `query`, `provider`, `source_id`, `url`, `used` | Si clarification documentaire utilisée |
| `VerificationResult` | `verified: bool`, `checks[]`, `limitations[]` | Posé par le vérificateur uniquement |
| `StudentValidation` | `decision` ∈ {accepted, modified, refused}, `comment`, `at` | Posé par l'endpoint de décision |
| `Confidence` | `overall`, `rationale` | Dérivée des preuves (clarté, cohérence, faisabilité) |
| `Evidence` | compteurs : appels LLM, requêtes réseau, corrections | Preuve d'honnêteté |

---

## 6. Contrat d'entrée (SPEC §6)

| Champ | Type | Requis | Provenance |
|---|---|---|---|
| `student_id` | string | oui | fourni |
| `session_id` | string | non (généré) | fourni |
| `subject_text` | string | oui (ou `upstream_subject` vérifié) | fourni |
| `research_problem` | string | oui | fourni |
| `research_problem_statement` | string | non | fourni |
| `discipline` | string | oui | fourni |
| `academic_level` | enum | non (défaut Master) | fourni |
| `country` / `geographical_area` / `study_period` | string | non | fourni |
| `target_population` | string | non | fourni |
| `research_context` | string | non | fourni |
| `literature_review` | object/string | non | fourni ou `upstream_literature` |
| `research_question_draft` | string | non | fourni (question provisoire de l'étudiant) |
| `student_constraints` / `university_instructions` / `supervisor_instructions` | string | non | fourni (données non fiables) |
| `previous_answers` | array | non | réponses antérieures de l'étudiant |
| `language_prefs` | object | non | fourni |
| `upstream_subject` / `upstream_problem` | object | non | acceptés si `validation.verified = true` |
| `upstream_problematic` | object | **oui** | problématique validée + `validation.verified = true` |
| `constraints` | object | non | bornes de session |

Taille maximale : 40000 caractères. Un `upstream_problematic` non vérifié ⇒ `422` ou
`needs_clarification` (jamais de formulation non fondée).

---

## 7. Contrat de sortie (SPEC §16)

```json
{
  "status": "needs_clarification | ready_for_verification | verification_failed | awaiting_human_validation | blocked | validated",
  "subject": "...",
  "validated_problematic": { "text": "...", "verified": true },
  "comprehension": { "phenomene": "...", "objet_central": "...", "population": "", "zone": "",
                     "periode": "", "reste_a_examiner": "...", "provenance": "provided" },
  "research_intention": { "intention": "expliquer", "justification": "...", "alternatives": [] },
  "main_research_question": "...",
  "secondary_research_questions": [],
  "formulation_rationale": "...",
  "scope_and_boundaries": { "geo": "", "temps": "", "population": "", "added_without_source": false },
  "feasibility_assessment": { "verdict": "uncertain", "raisons": [], "manques": [] },
  "missing_information": [],
  "ambiguities": [ { "description": "...", "impact": "...", "clarification_question": "..." } ],
  "source_evidence": [],
  "verification_result": { "verified": false, "checks": [], "limitations": [] },
  "student_validation": { "decision": null, "comment": "", "at": null },
  "confidence": { "overall": 0.0, "rationale": "..." },
  "evidence": { "llm_calls": 0, "network_requests": 0, "reformulations": 0 }
}
```

Aucun champ de l'étape suivante n'est produit comme « validé » : la sortie transmet la question
validée à l'Agent Objectifs sans imposer de méthodologie ni anticiper de résultats. Pas de fusion avec
le sujet, le problème ni la problématique.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mitigation dans cet agent |
|---|---|
| LLM01 — Prompt injection | Consignes, observations et consignes universitaires/cadre traitées comme DONNÉES NON FIABLES : balisées, scannées (motifs d'injection), jamais suivies comme instructions. |
| LLM02 — Insecure output handling | Aucune sortie LLM utilisée sans `Parser → Schéma → Métier → Sécurité` ; aucune exécution, aucun appel réseau déclenché par le modèle. |
| LLM03 — Supply chain | Dépendances figées et documentées, toutes gratuites/open source ; aucune installation automatique. |
| LLM04 — Data/model poisoning | Les entrées proviennent des étapes vérifiées ; aucun contenu non vérifié n'entre dans la formulation. |
| LLM05 — Improper output handling | Sorties structurées uniquement ; aucune référence bibliographique inventée (les sources viennent du corpus amont). |
| LLM06 — Excessive agency | Moindre privilège : `read session_only`, `write workspace_only`, `delete/deploy/send = false` ; périmètre réseau limité à la clarification (liste blanche). |
| LLM07 — System prompt leakage + **misinformation** | Zéro hallucination : aucun présupposé, aucune population/période/zone inventée ; contrôle de neutralité codé. |
| LLM08 — Vector/embedding weaknesses | Aucune base vectorielle en V1 (pas d'embedding) : surface supprimée. |
| LLM09 — Misinformation | Contrôle de neutralité déterministe + déclaration des ambiguïtés et des manques + vérificateur indépendant. |
| LLM10 — Unbounded consumption | Bornes : `max_input_size`, `max_output_tokens`, `max_external_requests`, `max_clarification_queries`, cache, garde anti-non-convergence, budget LLM par campagne. |

Isolation par `student_id`/`session_id` : chaque session écrit dans
`workspace/<student_id>/<session_id>/` et rien d'autre.

---

## 9. Mécanisme de validation

Sur **chaque** sortie LLM (étapes [5], [6], [8]) :

1. **Parser** — extraction JSON stricte ; en cas de troncature (modèle raisonneur), **re-tentative**
   avec consigne de concision (budget large : `max_output_tokens` 16000).
2. **Schéma** — validation pydantic : types, énumérations (intention, verdict de faisabilité),
   champs requis.
3. **Métier** — contrôles codés :
   - neutralité / anti-présupposé (`question_rules`) ;
   - question principale **unique** et non double ;
   - délmititation : aucune zone/période/population ajoutée sans source (sinon déclarée) ;
   - anti-fusion : question ≠ problématique ≠ sujet (textes distincts) ;
   - non-décision méthodologique (aucune logique/technique imposée) ;
   - `status` honnête ; `research_intention` dans l'enum canonique.
4. **Sécurité** — aucun contenu exécutable, aucune URL arbitraire, aucune tentative d'injection
   propagée depuis les consignes.

Violations métier non bloquantes : re-tentative ; si des violations subsistent à la **dernière**
tentative, **lever** (jamais de sortie non conforme transmise au vérificateur).

---

## 10. Mécanisme de vérification (SPEC §13)

**Vérificateur indépendant** (LLM séparé, prompt dédié, reçoit toutes les données étudiantes + la
production) — contrôles **C1–C12** :

| Code | Contrôle |
|---|---|
| C1 | La question découle de la problématique validée (rattachement explicite, non fusionnée). |
| C2 | Le sujet et ses limites sont respectés ; aucun nouvel enjeu majeur ajouté. |
| C3 | L'intention de recherche est correctement identifiée et étayée par la problématique. |
| C4 | La formulation est claire, précise, délimitée et compréhensible. |
| C5 | Neutralité : aucun présupposé ni réponse suggérée ; question ni suggestive ni double. |
| C6 | Faisabilité examinée au regard des ressources, du terrain et des contraintes connus. |
| C7 | Questions secondaires (si présentes) utiles, cohérentes, sans créer un nouveau sujet. |
| C8 | Aucune information inventée (population, terrain, période, causalité, conclusion). |
| C9 | Délimitations non ajoutées sans source ; toute délimitation manquante est `declared`. |
| C10 | Aucune méthodologie ni logique de raisonnement imposée (intention ≠ méthode). |
| C11 | Format : listes de chaînes normalisées, statuts dans l'enum, `verification_status = not_verified` par défaut ; ambiguïtés documentées. |
| C12 | Honnêteté : ambiguïtés et manques déclarés ; aucun auto-`verified` ; l'agent n'attribue pas `validated`. |

Verdict : `verified` | `corrections_requested` (≤ `MAX_VERIFICATION_RETRIES`) | `rejected`.
Si les mêmes corrections reviennent deux fois, la boucle s'arrête (pas de consommation de tours).
La sortie du vérificateur est elle-même validée en schéma/métier (format des listes normalisé
défensivement). **Le verdict `verified` ne vaut pas validation** : la validation est humaine
(§ 1, étapes [13-14]).

---

## 11. Stratégie de tests

| Niveau | Contenu |
|---|---|
| Unitaire / fonctionnel hors réseau | `tests/question/` : LLM simulé (JSON conformes **et** JSON dégradés). Compréhension, intention, formulation, contrôles, faisabilité. |
| Neutralité / anti-présupposé | Question neutre acceptée ; question à présupposé (« pourquoi X est-il inefficace ? ») détectée et refusée ; question double détectée. |
| Anti-fusion | Question ≠ problématique ≠ sujet ; aucune réécriture de la problématique. |
| Délimitation | Zone/période/population ajoutée sans source → déclarée ; délimitation indispensable absente → question de clarification. |
| Clarification documentaire | Fournisseurs simulés : `found`, `not_found`, `unavailable` (échec réseau déclaré). Hôtes hors liste blanche refusés. |
| Human gate | Décision `accepted` (→ `validated` si vérifié), `modified` (→ reformulation), `refused` (→ `blocked`). |
| Sécurité | Injection dans des consignes non suivie ; sortie exécutable rejetée ; isolation par session. |
| Intégration | `POST /question/analyze` bout en bout avec `upstream_problematic` vérifié ; `needs_clarification` sans problématique vérifiée. |
| **Réel** | Modèle réel + problématique réelle (issue d'une campagne de l'étape 4) → jusqu'au verdict du vérificateur, puis décision étudiante simulée. Script hors dépôt, résultats reportés dans la section « État réel ». |

Nommage : module d'aide `tests/question/question_helpers.py` (pas `helpers.py` — collision avec
`tests/helpers.py`).

---

## 12. Dépendances

Toutes **gratuites / open source**, figées et documentées (aucune installation automatique) :
`fastapi`, `uvicorn`, `pydantic`, `httpx`, `pyyaml`, `pytest` (tests). Aucune clé tierce : la
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
  Ajouter/retirer un fournisseur = éditer `sources/providers.yaml`. La fonctionnalité est
  **optionnelle** : elle sert à lever une ambiguïté terminologique, pas à produire un état des savoirs
  (rôle de l'étape 3).
- Aucune base vectorielle : la comparaison sujet / problème / problématique / question se fait par
  contrôles codés (recouvrement terminologique, motifs de présupposé), sans embedding.
- Si la clé OpenAlex gratuite existe (`OPENALEX_API_KEY`, déjà posée), elle est lue et transmise en
  en-tête `Authorization` (jamais dans l'URL) ; sinon les sept autres fournisseurs suffisent.

---

## 15. Limites connues

1. **Dépendance forte à l'amont** : sans problématique **validée et vérifiée**, l'agent ne peut pas
   formuler → `needs_clarification` (choix assumé : mieux vaut ne rien produire que produire hors
   cadre).
2. **Neutralité = détection déterministe partielle** : le contrôle des présupposés repose sur des
   motifs codés + le vérificateur LLM ; une présupposition implicite subtile peut échapper → l'humain
   reste le dernier rempart (portillon obligatoire).
3. **Faisabilité limitée à l'information fournie** : si le terrain, la population ou les ressources
   ne sont pas connus, la faisabilité reste `uncertain` et déclarée — jamais supposée.
4. **Clarification documentaire partielle** : `not_found` signifie « non trouvé dans ces sources »,
   jamais « inexistant » ; toujours déclaré.
5. **Qualité = proposition** : la question reste une proposition à valider par l'étudiant et son
   directeur ; l'agent n'a jamais raison contre eux.
6. **Pas d'embedding/RAG vectoriel en V1** (SPEC §28) : accès à l'information par règles codées et
   API publiques, pas par similarité sémantique.

---

## Décisions à valider par le porteur de projet (portillon §42)

- **D1 — Portillon humain et statut `validated`.** La SPEC §12 fait de la validation étudiante un
  préalable obligatoire et §16 interdit à l'agent de s'auto-attribuer `validated`. Proposition :
  l'agent s'arrête à `awaiting_human_validation` ; un endpoint dédié
  (`POST /question/{student_id}/{session_id}/decision`) enregistre la décision de l'étudiant
  (acceptée / modifiée / refusée) et, si acceptée **et** vérifiée, pose `validated`. Alternative :
  la validation humaine reste hors API (gérée par l'orchestrateur d'étapes).
- **D2 — Clarification documentaire.** La SPEC §8/§11 l'autorise « lorsque nécessaire ». Proposition :
  étage **optionnel, désactivé par défaut** (0 requête), activable en configuration, borné, à
  fournisseurs gratuits sans clé. Alternative : l'activer par défaut.
- **D3 — Enum des intentions.** La SPEC §7 liste 9 intentions. Proposition : enum canonique
  `{decrire, comprendre, explorer, expliquer, comparer, mesurer, evaluer, examiner_evolution,
  identifier_facteurs}` (plus l'ajout « autre » si aucune ne convient), normalisé (casse/accents).
- **D4 — Interface.** Route `POST /question/analyze`, port **8050**, `run-question.sh`, profil Hermes
  `agent-question`.
- **D5 — Faisabilité : seuils.** Proposition : la faisabilité est un jugement documenté
  (`feasible` / `uncertain` / `not_feasible`) fondé seulement sur les contraintes connues, sans
  introduire de ressource non fournie.
