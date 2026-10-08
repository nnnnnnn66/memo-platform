# Éléments de l'Agent Question de recherche (`research_question_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **architecture présentée — implémentation NON commencée** (portillon §42 : en attente de
> validation humaine).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Question de recherche |
| Technical ID | `research_question_agent` |
| Version prévue | `1.0` |
| Étape du parcours | 5 — Question de recherche |
| Paquet prévu | `src/research_question_agent/` (autonome ; aucun agent existant modifié) |
| Port de service prévu | 8050 (`run-question.sh`) |
| Profil Hermes | `agent-question` (`~/.hermes/profiles/agent-question/`) ; alias `agent-question` |

## Profil Hermes propre à l'agent (à créer)

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-question/SOUL.md` | Rôle étape 5, objectif, interdits, chemins |
| Context | `.../agent-question/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-question/memories/MEMORY.md`, `memories/USER.md` | Neutralité, anti-présupposé, anti-fusion, délimitation |
| Knowledge | `.../agent-question/knowledge/README.md` | Principes de formulation, intentions de recherche, human gate |
| Skills | `.../agent-question/skills/agent-question/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-question/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (recherche publique sans clé) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-question.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/research_question_agent/__init__.py` + prompt `p1_comprehension_system.md` § rôle | À CRÉER |
| Mission | `docs/spec-agent-05-question-recherche.md` § 3 | Déposée |
| Goal | SPEC § 4 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-05-question-recherche-v1.md`, `config/settings-question.yaml` | Architecture présentée ; config À CRÉER |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-05-question-recherche.md`, (`sources/providers.yaml`) | À CRÉER (contenu défini dans le profil) |
| RAG | Aucune base vectorielle en V1 ; clarification documentaire = API publiques (`sources/`) | À CRÉER |
| Tools | `pipeline/` (input, sécurité, P1–P3, contrôles déterministes, validations, vérificateur, orchestrateur) | À CRÉER |
| Tool spécifique | `sources/adapters/*.py` (clarification de concept, déterministe) + `analysis/question_rules.py` | À CRÉER |
| Permissions | `core/limits.py`, `core/security_rules.py` | À CRÉER — READ session + RESEARCH public, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{comprehension,question_proposal,decision}.json` + `workspace/question-cache.db` | À CRÉER |
| Skills | `llm/prompts/{p1_comprehension,p2_formulation,verifier}_system.md` | À CRÉER |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-question.yaml` (+ `sources/providers.yaml` si clarification activée) | À CRÉER |
| Logs | `core/logging.py` + `workspace/audit-question.db` | À CRÉER |
| Données de mission | entrées étudiantes + snapshots amont (problématique vérifiée) + réponses précédentes | À CRÉER |
| Stop condition | `core/limits.py` (appels LLM, requêtes réseau, taille), `core/errors.py`, garde anti-non-convergence | À CRÉER |
| Validation | `schema_validation` → `business_validation` (neutralité, anti-présupposé, anti-fusion, délimitation) → `security_validation` | À CRÉER |
| Evidence | `tests/question/`, journal d'audit, sortie de session, section « État réel » de l'architecture | À CRÉER |
| Integration | `api/routes.py` (`POST /question/analyze`, `POST /question/{student_id}/{session_id}/decision`, `GET /question/{student_id}/{session_id}`, `GET /health`), `run-question.sh` | À CRÉER |

## Contrats prévus

| Contrat | Fichier prévu | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_problematic` **vérifié** (obligatoire) ; `upstream_subject` / `upstream_problem` / revue acceptés seulement si vérifiés ; `previous_answers`, `student_constraints`, `university_instructions`, `supervisor_instructions` = données non fiables |
| Compréhension / intention | `schemas/comprehension.py` | `research_intention` ∈ enum canonique ; provenance (fourni / déduit / inconnu) |
| Proposition de question | `schemas/question.py` | `main_research_question` unique ; `secondary_research_questions[]` optionnel ; `scope_and_boundaries` ; `feasibility_assessment` |
| Décision étudiante | `schemas/decision.py` | `decision` ∈ {accepted, modified, refused} + `student_comment` ; pose `student_validation` |
| Sortie | `schemas/output.py` | Les 15 champs de la SPEC §16 ; `status` dans l'enum |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles codés C1–C12 |

## Bornes par défaut (à ajuster et justifier)

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 40000 | entrées étudiantes + snapshots amont (problématique, sujet) |
| `max_output_tokens` | 16000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_llm_calls` | 8 | P1 + P2 + vérificateur + re-tentatives |
| `max_external_requests` | 6 | clarification documentaire bornée (0 si désactivée) |
| `max_clarification_queries` | 3 | requêtes de clarification de concept |
| `cache_ttl_hours` | 336 | cache clarification (14 j) |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais fusionner Sujet / Problème / Problématique / Question de recherche.
- Ne jamais écrire une question qui présuppose sa réponse (prémisses non établies).
- Ne jamais ajouter une zone géographique, une période ou une population non fournie.
- Ne jamais inventer données, population, terrain, période, relations causales ou sources fictives.
- Ne jamais imposer une méthodologie ou une logique de raisonnement : l'intention de recherche n'est
  pas une méthode.
- Ne jamais attribuer soi-même le statut `validated` (réservé à la validation étudiante + contrôle).
- Ne jamais s'auto-attribuer `verified` (réservé au vérificateur indépendant).

## Preuves attendues

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/question/` (LLM simulé + cas neutres/non neutres) |
| Contrôle de neutralité seul | test déterministe : question à présupposé détectée, question neutre acceptée |
| Test réel complet | script hors dépôt + section « État réel » de l'architecture |
| Traces | `workspace/audit-question.db`, artefacts par session |
