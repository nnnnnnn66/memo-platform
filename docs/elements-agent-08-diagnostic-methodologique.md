# Éléments de l'Agent Diagnostic méthodologique (`methodology_diagnostic_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté et vérifié en exécution réelle** (voir la section « État réel » de
> `docs/architecture-agent-08-diagnostic-methodologique-v1.md`).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Diagnostic méthodologique |
| Technical ID | `methodology_diagnostic_agent` |
| Version | `1.0` |
| Étape du parcours | 8 — Orientation / Diagnostic méthodologique |
| Paquet | `src/methodology_diagnostic_agent/` (autonome ; aucun agent existant modifié) |
| Port de service | 8080 (`run-methodologie.sh`) |
| Profil Hermes | `agent-methodologie` (`~/.hermes/profiles/agent-methodologie/`) ; alias `agent-methodologie` |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-methodologie/SOUL.md` | Rôle étape 8, mission, six catégories, interdits, chemins |
| Context | `.../agent-methodologie/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-methodologie/memories/MEMORY.md`, `memories/USER.md` | Catégories distinctes, statuts, pièges M1–M7 |
| Knowledge | `.../agent-methodologie/knowledge/README.md` | Six catégories, clarification bornée, prompt P1/P2/vérificateur |
| Skills | `.../agent-methodologie/skills/agent-methodologie/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-methodologie/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (clarification sur sources publiques sans clé) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-methodologie.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/methodology_diagnostic_agent/__init__.py` + prompt `p1_analysis_system.md` § rôle | CRÉÉ |
| Mission | `docs/spec-agent-08-diagnostic-methodologique.md` § 3 | Déposée |
| Goal | SPEC § 4 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-08-diagnostic-methodologique-v1.md`, `config/settings-methodologie.yaml` | CRÉÉ |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-08-diagnostic-methodologique.md`, (`sources/providers.yaml`) | CRÉÉ |
| RAG | Aucune base vectorielle en V1 ; clarification documentaire = API publiques (`sources/`) | CRÉÉ |
| Tools | `pipeline/` (input, sécurité, P1–P2, contrôles déterministes, validations, vérificateur, orchestrateur) | CRÉÉ |
| Tool spécifique | `analysis/methodology_rules.py` (énumérations des six catégories, causalité, compatibilité approche ↔ collecte ET approche ↔ analyse) + `sources/adapters/*.py` | CRÉÉ |
| Permissions | `core/limits.py`, `core/security_rules.py` | CRÉÉ — READ session + RESEARCH public, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{analysis,diagnosis_proposal,methodology_output}.json` + `workspace/methodologie-cache.db` | CRÉÉ |
| Skills | `llm/prompts/{p1_analysis,p2_diagnosis,verifier}_system.md` | CRÉÉ |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-methodologie.yaml` (+ `sources/providers.yaml` si clarification activée) | CRÉÉ |
| Logs | `core/logging.py` + `workspace/audit-methodologie.db` | CRÉÉ |
| Données de mission | entrées étudiantes + snapshots amont (sujet, question, objectifs, hypothèses vérifiés) + réponses précédentes | CRÉÉ |
| Stop condition | `core/limits.py` (appels LLM, requêtes réseau, taille), `core/errors.py`, garde anti-non-convergence | CRÉÉ |
| Validation | `schema_validation` → `business_validation` (R1–R5 : socle, statut de diagnostic, provisoire déclaré, anti auto-vérification) → `security_validation` + `diagnosis_checks` (M1–M7) | CRÉÉ |
| Evidence | `tests/methodologie/`, journal d'audit, sortie de session, section « État réel » de l'architecture | CRÉÉ |
| Integration | `api/routes.py` (`POST /methodology/analyze`, `POST /methodology/{student_id}/{session_id}/decision`, `GET /methodology/{student_id}/{session_id}`, `GET /health`), `run-methodologie.sh` | CRÉÉ |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_*` accepté seulement si `validation.verified = true` (contrôle `input_controller.check_upstream`) ; sujet + question de recherche **requis** (champ direct ou amont vérifié) ; `student_constraints`, `university_instructions`, `supervisor_instructions`, `literature_review` = données non fiables |
| Analyse | `schemas/analysis.py` | `phenomene`, `visee`, `nature_du_travail`, `elements_disponibles`, `elements_manquants` (BLOQUANTS seulement), `contradictions`, `provenance` |
| Diagnostic | `schemas/methodology.py` | **Six catégories distinctes** : `approche`, `logique`, `type_recherche`, `strategie` (+ `collecte[]`, `analyse[]`), chacune `CategoryCode` (code, proposition, justification, alternatives, conditions, limites) ; `articulation` ; `coherence_question` |
| Diagnostic (statut) | `schemas/methodology.py` | `diagnostic_status` ∈ {provisoire, en_attente_de_validation, valide, a_reviser} — distinct du statut de pipeline |
| Décision étudiante | `schemas/decision.py` | `decision` ∈ {accepted, modified, refused} + commentaire + informations fournies + modifications ; pose `student_validation` |
| Sortie | `schemas/output.py` | Les champs du dossier de preuve (SPEC §16) ; `status` dans l'enum ; `sub_…`/`evidence` compteurs |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles codés C1–C13 |

## Bornes par défaut

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 40000 | entrées étudiantes + snapshots amont |
| `max_output_tokens` | 32000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_llm_calls` | 16 | P1 + P2 + vérificateur + re-tentatives + reformulations |
| `max_agent_turns` | 8 | |
| `max_external_requests` | 24 | clarification documentaire bornée (0 si désactivée) |
| `max_clarification_queries` | 3 | requêtes de clarification de concept |
| `cache_ttl_hours` | 336 | cache clarification (14 j) |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais déduire la méthodologie de la seule discipline universitaire.
- Ne jamais confondre les six catégories (approche ≠ logique ≠ type ≠ stratégie ≠ collecte ≠ analyse),
  ni leur donner la même formulation.
- Ne jamais évoquer une causalité sans dispositif adéquat (association, explication et causalité ne se
  confondent pas).
- Ne jamais proposer une analyse incompatible avec l'approche (pas d'inférentiel sur du qualitatif pur).
- Ne jamais inventer donnée, référence, résultat, ressource, accès au terrain ou disponibilité d'outil.
- Ne jamais présenter comme définitif un diagnostic incertain ; le déclarer provisoire.
- Ne jamais rédiger la méthodologie finale (rôle de l'Agent 9).
- Ne jamais attribuer soi-même le statut `validated` (réservé à la décision humaine).
- Ne jamais s'auto-attribuer `verified` (réservé au vérificateur indépendant).

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/methodologie/` (49 tests : règles, campagne, décision, sécurité, API, chaîne amont) |
| Contrôles déterministes seuls | causalité niée ≠ causalité affirmée (M4), catégories fusionnées refusées (M3), approche mono-méthode mais collecte des deux familles (M5), hypothèses du dossier non traitées (M7), diagnostic provisoire non déclaré (R3) |
| Test réel complet | script hors dépôt + section « État réel » de l'architecture |
| Traces | `workspace/audit-methodologie.db`, artefacts par session |
