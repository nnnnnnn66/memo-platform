# Architecture V1 — Agent Sujet (`subject_agent` 1.0)

> Présentation exigée par la SPEC §42. **Aucune implémentation n'a été faite.**
> Ce document attend la validation humaine avant toute ligne de code.
> Référentiel : SPECIFICATION DÉFINITIVE — AGENT SUJET V1 (voir `spec-agent-sujet-v1.md`).

---

## 1. Architecture

Le traitement est un **pipeline linéaire de garde-fous** : rien ne court-circuite une étape,
et la sortie d'un LLM n'est jamais transmise telle quelle (§10, §25).

```
ÉTUDIANT
   │
   ▼
[1] Input Controller        ── reçoit la requête HTTP, attache student_id/session_id
   │
   ▼
[2] Input Validation        ── schéma d'entrée + tailles + champs obligatoires (§8)
   │
   ▼
[3] Security Layer          ── détection injection / secrets / instructions cachées (§21,24,43)
   │                            sépare : instructions système | règles sécu | données user
   ▼
[4] Subject Agent (LLM)     ── analyse méthodologique + questionnement (§5–9)
   │
   ▼
[5] Output Parser           ── extraction du JSON de la réponse LLM
   │
   ▼
[6] Schema Validation       ── modèle Pydantic strict (§10)
   │
   ▼
[7] Business Validation     ── cohérence méthodologique, anti-fusion, fidélité
   │
   ▼
[8] Security Validation     ── pas de fuite, pas d'exécution, contenu sûr
   │
   ▼
[9] Subject Verifier (LLM)  ── vérificateur indépendant (§34) — sortie retraitée par 5→8
   │
   ▼
[10] Validated Subject      ── statut `verified` posé uniquement par le vérificateur
```

Principes non négociables :
- **Moindre privilège** (§26) : l'agent lit la session courante, écrit dans son espace, rien d'autre.
- **Séparation stricte** (§21, §24) : toute donnée étudiante (sujet, contexte, documents) est
  traitée comme **données non fiables**, jamais comme instruction.
- **Double validation** : le vérificateur est un appel **séparé et indépendant** ; l'agent ne
  s'auto-attribue jamais `verified` (§11, §34).
- **Économie** (§16, §40) : 0 € par défaut, ressources existantes d'abord.

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── README.md
├── requirements.txt
├── .env.example
├── run.sh
├── config/
│   └── settings.yaml              # limites, seuils, sélection du modèle, chemins
├── docs/
│   ├── spec-agent-sujet-v1.md     # SPEC définitive (référentiel)
│   ├── architecture-v1.md         # ce document
│   └── agent-01-sujet.md          # ancienne note de conception (superseded)
├── src/
│   └── subject_agent/
│       ├── __init__.py
│       ├── main.py                # app FastAPI + montage des routes
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py          # endpoints HTTP
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── input_controller.py
│       │   ├── input_validation.py
│       │   ├── security_layer.py
│       │   ├── subject_agent.py
│       │   ├── output_parser.py
│       │   ├── schema_validation.py
│       │   ├── business_validation.py
│       │   ├── security_validation.py
│       │   └── subject_verifier.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py          # client LLM OpenAI-compatible + timeouts/retries
│       │   └── prompts/
│       │       ├── subject_system.md
│       │       └── verifier_system.md
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── input.py           # contrat d'entrée
│       │   ├── output.py          # contrat de sortie (§10)
│       │   └── verifier.py        # sortie du vérificateur
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py          # chargement config/settings.yaml + .env
│       │   ├── limits.py          # constantes de bornage (§30)
│       │   ├── errors.py          # états d'erreur (§33)
│       │   ├── security_rules.py  # motifs d'injection, règles §21–31
│       │   ├── logging.py         # journalisation sûre (§32)
│       │   └── sessions.py        # isolation student_id/session_id (§31)
│       └── storage/
│           ├── __init__.py
│           ├── workspace.py       # artefacts JSON par session
│           └── audit.py           # journal d'audit (SQLite stdlib)
├── workspace/                     # données par session (hors code, non versionné)
│   └── <student_id>/<session_id>/
└── tests/
    ├── conftest.py
    ├── functional/
    │   ├── test_01_sujet_clair.py
    │   ├── test_02_sujet_vague.py
    │   ├── test_03_sujet_trop_large.py
    │   ├── test_04_infos_manquantes.py
    │   └── test_05_reformulation_fidele.py
    └── security/
        ├── test_06_prompt_injection.py
        ├── test_07_extraction_secret.py
        ├── test_08_injection_document.py
        ├── test_09_sortie_invalide.py
        ├── test_10_commande_systeme.py
        ├── test_11_hallucination.py
        ├── test_12_consommation.py
        └── test_13_isolation.py
```

---

## 3. Rôle de chaque fichier

| Fichier | Rôle |
|---|---|
| `main.py` | Instancie FastAPI, monte les routes, charge la config au démarrage. |
| `api/routes.py` | Endpoints : `POST /subject/analyze`, `GET /subject/{session_id}`, `GET /health`. Aucune logique métier. |
| `pipeline/input_controller.py` | Reçoit la requête, extrait `student_id`/`session_id`, crée la session si absente, attache le contexte. |
| `pipeline/input_validation.py` | Valide le contrat d'entrée (§8) : `subject_text` obligatoire, tailles sous `MAX_INPUT_SIZE`. |
| `pipeline/security_layer.py` | Détecte injections/secrets/instructions cachées dans les entrées ; **enveloppe** les données utilisateur comme données non fiables (balisage explicite). |
| `llm/client.py` | Client OpenAI-compatible : provider, modèle, timeout, retries bornés, comptage de consommation. |
| `llm/prompts/subject_system.md` | Prompt système de l'agent : rôle, interdits, processus §9, règles d'entrée/sortie. |
| `llm/prompts/verifier_system.md` | Prompt système du vérificateur (§34), indépendant de celui de l'agent. |
| `pipeline/subject_agent.py` | Orchestre l'appel LLM de l'agent avec le prompt système + entrées balisées. |
| `pipeline/output_parser.py` | Extrait le JSON de la réponse LLM (blocs balisés, texte parasite) ; échec si absent. |
| `pipeline/schema_validation.py` | Valide contre le modèle Pydantic de sortie (§10). |
| `pipeline/business_validation.py` | Règles métier : fidélité, anti-fusion, cohérence statut/complétude, traçabilité des sources. |
| `pipeline/security_validation.py` | Contrôle de sûreté de la sortie : pas de fuite de prompt/secret, pas de contenu interdit. |
| `pipeline/subject_verifier.py` | Appel LLM indépendant appliquant les 11 contrôles (§34) ; seul habilité à poser `verified`. |
| `schemas/input.py` | Modèle Pydantic du contrat d'entrée. |
| `schemas/output.py` | Modèle Pydantic du contrat de sortie (§10) + enums de statut/source. |
| `schemas/verifier.py` | Modèle Pydantic de la sortie du vérificateur. |
| `core/config.py` | Lit `config/settings.yaml` + `.env` ; **n'expose jamais** les secrets. |
| `core/limits.py` | Constantes de bornage §30 (valeurs par défaut, surchargeables). |
| `core/errors.py` | Enum des états d'erreur §33 + exceptions typées. |
| `core/security_rules.py` | Motifs et règles centralisés : injection, fuite, permissions §26. |
| `core/logging.py` | Journalisation **filtrée** (aucun secret) §32. |
| `core/sessions.py` | Isolation : toute opération porte `student_id`+`session_id` ; vérifie l'appartenance. |
| `storage/workspace.py` | Lecture/écriture des artefacts d'une session dans `workspace/<student>/<session>/`. |
| `storage/audit.py` | Journal d'audit persistant (SQLite stdlib) : statut, tentatives, erreurs, sources. |
| `tests/*` | Tests fonctionnels (1–5) et de sécurité (6–13). |

---

## 4. Flux des données

```
POST /subject/analyze
  body: {student_id, session_id?, subject_text, student_context?, discipline?, ...}
   │
   ├─ Input Controller ─► crée/ouvre session (student_id, session_id)
   ├─ Input Validation ─► requête conforme ? sinon → 422 INVALID_INPUT
   ├─ Security Layer ───► balise les données user comme NON FIABLES
   │                      bloque/annote si injection manifeste
   ├─ Subject Agent ────► LLM(system_prompt, données_balisées) → texte
   ├─ Output Parser ────► JSON extrait ? sinon → OUTPUT_SCHEMA_ERROR
   ├─ Schema Validation ► Pydantic OK ? sinon → OUTPUT_SCHEMA_ERROR (1 retry LLM)
   ├─ Business Validation ► règles métier OK ? sinon → corrections / 1 retry
   ├─ Security Validation ► sortie sûre ? sinon → SECURITY_VIOLATION
   │
   ├─ Statut provisoire : needs_clarification | ready_for_verification | blocked
   │     (si needs_clarification → on retourne questions_for_student, FIN)
   │
   ├─ Subject Verifier ──► appel LLM INDÉPENDANT (contrôles §34)
   │     verdict = verified | corrections_requested | rejected
   │     → si corrections_requested : re-boucle agent (≤ MAX_VERIFICATION_RETRIES)
   │     → si verified : statut final `verified` (posé par le vérificateur)
   │
   └─ Workspace (écriture) + Audit (écriture) + réponse HTTP (sortie validée)
```

Le même pipeline `Parser → Schema → Business → Security` s'applique **aussi** à la sortie
du vérificateur avant de la considérer comme valable.

---

## 5. Modèle de données

**Entités principales**

```
Session
  session_id      str (uuid4)
  student_id      str (opaque)      # isolation §31
  created_at      datetime
  status          enum(session_status)

SubjectRequest        # voir §6
SubjectOutput         # voir §7 — cœur du contrat
SourceRecord
  source          str
  title           str | null
  url             str | null
  publication_date date | null
  access_date     date | null
  information_used str
  source_type     enum(user | external | model_inference)
  confidence      float [0..1]
  verification_status enum(verified | not_verified)
VerifierOutput
  verdict         enum(verified | corrections_requested | rejected)
  controls        [ {code, resultat, detail} ]   # 11 contrôles §34
  corrections     [str]
  flags           [str]                          # sécurité / fidélité
AuditLog
  session_id, agent_id, timestamp, version, status,
  errors[], validation_result, attempts, consumption_approx, source_ids[]
Limits             # voir §30 — chargé depuis config/settings.yaml
```

**Enums**

```
STATUS           = needs_clarification | ready_for_verification | blocked | verified
SOURCE_TYPE      = user | external | model_inference
VERIFICATION     = verified | not_verified
ERROR_STATE      = INVALID_INPUT | MISSING_INFORMATION | OUTPUT_SCHEMA_ERROR |
                   SECURITY_VIOLATION | TOOL_ERROR | TIMEOUT | RESOURCE_LIMIT |
                   VERIFICATION_FAILED
```

**Stockage V1** : artefacts JSON par session sous `workspace/<student_id>/<session_id>/`,
+ un journal d'audit SQLite (module `sqlite3` de la stdlib, sans dépendance payante).
Pas de base vectorielle (§28).

---

## 6. Contrat d'entrée (§8)

| Champ | Type | Obligatoire | Contrainte |
|---|---|---|---|
| `student_id` | str | oui (isolation) | opaque, non exposé dans les logs |
| `session_id` | str(uuid) | non | créé si absent |
| `subject_text` | str | **oui** | non vide, ≤ `MAX_INPUT_SIZE` |
| `student_context` | str | non | ≤ `MAX_INPUT_SIZE` |
| `discipline` | str | non | |
| `academic_level` | str | non | ex. "Master 2" |
| `country` | str | non | |
| `institution` | str | non | |
| `previous_answers` | list | non | réponses aux questions précédentes |
| `additional_constraints` | str | non | |

Chaque champ porte une **provenance** : `fourni` | `déduit` | `inconnu` (§8). Une information
`inconnu` ne devient jamais un fait.

---

## 7. Contrat de sortie (§10)

Schéma JSON contraint (Pydantic, `extra=forbid`) :

```json
{
  "agent": "subject_agent",
  "version": "1.0",
  "status": "needs_clarification | ready_for_verification | blocked",
  "subject": { "original": "", "reformulated": "" },
  "research_context": {
    "domain": "", "object_of_study": "", "population": "",
    "geographical_scope": "", "temporal_scope": "", "phenomenon": ""
  },
  "key_concepts": [],
  "initial_justification": "",
  "feasibility": { "status": "unknown|ok|concerning", "concerns": [] },
  "missing_information": [],
  "questions_for_student": [],
  "identified_ambiguities": [],
  "identified_limits": [],
  "evidence": [
    { "source": "", "title": "", "url": "", "publication_date": "",
      "access_date": "", "information_used": "",
      "source_type": "user|external|model_inference",
      "confidence": 0, "verification_status": "verified|not_verified" }
  ],
  "confidence": { "overall": 0 },
  "validation": { "verified": false, "verifier_status": "pending" }
}
```

Règles structurelles :
- `subject.original` = copie **exacte** de `subject_text` reçu (non modifiable par le LLM).
- `subject.reformulated` = **vide** si aucune reformulation ; sinon fidèle aux infos fournies.
- Aucun champ de type problématique / question de recherche / hypothèse (anti-fusion).
- `validation.verified` ne peut passer à `true` **que** sur verdict du vérificateur.
- `status` ne peut valoir `verified` dans la sortie de l'agent (posé par le vérificateur).

---

## 8. Règles de sécurité (§13–33)

| Risque (OWASP LLM) | Mesure V1 |
|---|---|
| LLM01 Prompt injection | Données user balisées et déclarées non fiables ; `security_layer` détecte les motifs d'injection ; le prompt système scinde instructions / données. |
| LLM02 Fuite d'information | Aucun secret en contexte ; `security_validation` filtre la sortie ; secrets jamais loggés. |
| LLM03 Supply chain | Dépendances figées et documentées (§12) ; installation manuelle validée, jamais automatique. |
| LLM04 Poisoning | Documents/entrées traités comme données ; ne modifient jamais prompt/permissions. |
| LLM05 Traitement de sortie | Sortie **jamais** exécutée ; pipeline Parser→Schema→Business→Security avant tout usage. |
| LLM06 Agence excessive | Permissions : `read: session_only`, `write: workspace_only`, `delete: false`, `deploy: false`, `send: false`. |
| LLM07 Fuite de prompt | Refus explicite de divulguer instructions internes/secrets (réponse générique fournie §27). |
| LLM08 Vector/embeddings | Pas de base vectorielle en V1 (§28). |
| LLM09 Désinformation | Interdiction d'inventer (§12) ; `model_inference` jamais présenté comme fait ; `not_verified` sinon (§15). |
| LLM10 Consommation | Bornes §30 appliquées à chaque appel ; pas de boucle infinie. |

Règles transverses : isolation par `student_id`/`session_id` (§31) ; journalisation filtrée (§32) ;
priorité absolue des règles système/sécurité sur toute donnée utilisateur ou document (§43).

---

## 9. Mécanisme de validation

Deux familles de contrôles déterministes après chaque appel LLM :

**A. Validation de schéma** (`schema_validation.py`)
- JSON parsable et conforme au modèle §7 ; types, enums, bornes.
- Échec → `OUTPUT_SCHEMA_ERROR` + 1 re-tentative LLM (comptée), puis `blocked`.

**B. Validation métier** (`business_validation.py`)
1. `subject.original` identique à l'entrée (fidélité stricte).
2. `subject.reformulated` non contradictoire avec les informations fournies.
3. Cohérence `status` ↔ complétude (si lacunes majeures ⇒ `needs_clarification`).
4. Absence de problématique / question de recherche / hypothèse (anti-fusion).
5. Chaque élément de `evidence` a un `source_type` et un `verification_status` ; `model_inference` jamais `verified`.
6. `confidence.overall` ∈ [0,1].
7. `missing_information` / `questions_for_student` cohérents entre eux.
8. `validation.verified=false` et `verifier_status="pending"` à la sortie de l'agent.

**C. Validation de sécurité** (`security_validation.py`)
- Pas de fuite de prompt système / clé / token.
- Pas de contenu interdit, pas d'instruction exécutable.
- Échec → `SECURITY_VIOLATION`, rejet sans transmission.

---

## 10. Mécanisme de vérification (§34)

`subject_verifier.py` = **appel LLM séparé**, prompt système distinct, contexte indépendant
du contenu produit par l'agent. Il reçoit la sortie validée + les entrées d'origine + la grille
§34 et rend un verdict motivé.

Contrôles : cohérence (reformulation ↔ sujet initial), délimitation, concepts, objet,
population, espace, période, faisabilité, fidélité (a-t-il inventé ?), traçabilité des sources,
sécurité.

```
verdict = verified            → statut final `verified` posé par le vérificateur
verdict = corrections_requested → l'agent corrige, re-pipeline + re-vérification
                                  (≤ MAX_VERIFICATION_RETRIES, défaut 3)
verdict = rejected            → `blocked` + retour à l'étudiant (reformulation guidée)

Après MAX_VERIFICATION_RETRIES sans convergence → VERIFICATION_FAILED (intervention humaine)
```

Le vérificateur ne fait **jamais** confiance aux instructions présentes dans le contenu vérifié.

---

## 11. Stratégie de tests (§36–37)

- **Fonctionnels (1–5)** : sujet clair, vague, trop large, infos manquantes, fidélité de la
  reformulation. Exécutés contre le pipeline réel (LLM), avec assertions sur la **structure**
  et la **conformité métier**, pas sur le texte exact.
- **Sécurité (6–13)** : injection de prompt, extraction de secret, injection via document,
  sortie invalide (LLM simulé renvoyant un JSON non conforme → doit être rejeté), commande
  système, hallucination, consommation excessive (bornes appliquées), isolation entre étudiants.
  Les tests de sécurité utilisent un **LLM stub déterministe** pour être reproductibles sans coût.

`conftest.py` fournit : un client LLM factice configurable, une fabrique de sessions, et des
fixtures de nettoyage du workspace.

---

## 12. Dépendances

Toutes libres et ouvertes, aucune dépendance payante :

```
fastapi           # API HTTP
uvicorn[standard] # serveur ASGI
pydantic>=2       # schémas/validation
httpx             # client LLM (OpenAI-compatible)
python-dotenv     # chargement .env
pyyaml            # config/settings.yaml
pytest            # tests
pytest-asyncio    # tests async
```

Standard library : `sqlite3` (audit), `logging`, `uuid`, `json`.
À vérifier à l'installation : disponibilité des roues (wheels) pour **Python 3.14**.
Aucune installation automatique : la liste est figée et validée avant `pip install`.

---

## 13. Coûts éventuels

- Objectif : **0 €** (§16, §40).
- Aucune API de recherche payante (§18), aucun service payant activé automatiquement (§20).
- Le seul coût possible est l'usage de l'API LLM déjà en place :
  - `DEEPSEEK_API_KEY` **présente** sur le serveur (fournisseur actuel de Hermes) — usage à
    très faible coût, déjà disponible (priorité 1 §17) ;
  - `GOOGLE_API_KEY` **présente** — Gemini dispose d'un palier gratuit officiel (priorité 2 §17).
- Aucun dépassement automatique de palier / pay-as-you-go (§20).

---

## 14. Alternatives gratuites

Par ordre de préférence (§17, §40) :
1. **Ressources déjà disponibles** : réutiliser un fournisseur/ modèle déjà configuré
   (DeepSeek actuellement configuré dans Hermes).
2. **Offre gratuite officielle** : Gemini (clé Google déjà présente) dans ses limites gratuites.
3. **Open source local** : serveur possible (4 vCPU / 7,8 Go RAM, sans GPU) → seulement un
   **petit** modèle (ex. ~3B paramètres quantifié) via Ollama. Coût 0 € mais qualité
   méthodologique moindre et latence/simplicité dégradées — solution de **dernier recours** (V1).
4. Recherche externe : aucune API payante ; en V1, l'agent **questionne l'étudiant** ou marque
   `not_verified` plutôt que d'appeler une source payante.

---

## 15. Limites connues

1. La détection d'injection par motifs est **heuristique** : elle ne couvre pas toutes les
   formulations ; l'atténuation repose surtout sur la séparation stricte instructions/données.
2. Le vérificateur est **lui aussi un LLM** : sa fiabilité n'est pas absolue. Mesures :
   contexte indépendant, grille explicite, sortie elle-même validée, boucle bornée.
3. **Pas de RAG** en V1 (§28) : les faits externes restent limités ; l'agent privilégie la
   question à l'étudiant et le marquage `not_verified`.
4. **Python 3.14** : compatibilité des dépendances à confirmer à l'installation.
5. Stockage fichier + SQLite mono-nœud : **pas** conçu pour une charge concurrente élevée ;
   suffisant pour le prototype.
6. **Pas d'authentification multi-utilisateurs** en V1 au-delà de l'isolation par
   `student_id`/`session_id` (l'auth relève de l'interface finale, hors périmètre §4).
7. Qualité de sortie dépendante du modèle LLM retenu (petit modèle local ⇒ qualité moindre).

---

## Décisions à valider avant implémentation

1. **Fournisseur LLM V1** — recommander : DeepSeek (déjà configuré, quelques centimes).
   Alternative gratuite : Gemini (clé Google présente). Local : dernier recours.
2. **Vérificateur** — même modèle que l'agent, ou modèle distinct pour une indépendance réelle ?
3. **Valeurs par défaut des bornes** (§30) : proposition
   `MAX_INPUT_SIZE=20000 car.`, `MAX_OUTPUT_TOKENS=2000`, `MAX_TOOL_CALLS=0`,
   `MAX_AGENT_TURNS=6`, `MAX_VERIFICATION_RETRIES=3`, `TIMEOUT=30 s`,
   `MAX_EXTERNAL_REQUESTS=0`, `MAX_SEARCH_RESULTS=5`.
4. **Stockage V1** — artefacts JSON par session + audit SQLite (stdlib) : d'accord ?
5. **Recherche externe V1** — aucune : l'agent questionne ou marque `not_verified`. Confirmer.
6. **Report de la SPEC** — ma note `agent-01-sujet.md` est superseded par votre SPEC ; dois-je
   la supprimer pour éviter la confusion ?
