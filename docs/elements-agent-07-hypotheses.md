# Éléments de l'Agent Hypothèses de recherche (`research_hypotheses_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté et vérifié en exécution réelle** (voir la section « État réel » de
> `docs/architecture-agent-07-hypotheses-v1.md`).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Hypothèses de recherche |
| Technical ID | `research_hypotheses_agent` |
| Version | `1.0` |
| Étape du parcours | 7 — Hypothèses |
| Paquet | `src/research_hypotheses_agent/` (autonome ; aucun agent existant modifié) |
| Port de service | 8070 (`run-hypotheses.sh`) |
| Profil Hermes | `agent-hypotheses` (`~/.hermes/profiles/agent-hypotheses/`) ; alias `agent-hypotheses` |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-hypotheses/SOUL.md` | Rôle étape 7, objectif, interdits, chemins |
| Context | `.../agent-hypotheses/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-hypotheses/memories/MEMORY.md`, `memories/USER.md` | Pas d'hypothèses forcées, neutralité, distinction |
| Knowledge | `.../agent-hypotheses/knowledge/README.md` | Définitions, décision de pertinence, human gate |
| Skills | `.../agent-hypotheses/skills/agent-hypotheses/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-hypotheses/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (recherche publique sans clé) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-hypotheses.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/research_hypotheses_agent/__init__.py` + prompt `p1_analysis_system.md` § rôle | CRÉÉ |
| Mission | `docs/spec-agent-07-hypotheses.md` § 3 | Déposée |
| Goal | SPEC § 4 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-07-hypotheses-v1.md`, `config/settings-hypotheses.yaml` | CRÉÉ |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-07-hypotheses.md`, (`sources/providers.yaml`) | CRÉÉ |
| RAG | Aucune base vectorielle en V1 ; clarification documentaire = API publiques (`sources/`) | CRÉÉ |
| Tools | `pipeline/` (input, sécurité, P1–P3, contrôles déterministes, validations, vérificateur, orchestrateur) | CRÉÉ |
| Tool spécifique | `analysis/hypothesis_rules.py` (distinctions, causalité, examinabilité) + `sources/adapters/*.py` | CRÉÉ |
| Permissions | `core/limits.py`, `core/security_rules.py` | CRÉÉ — READ session + RESEARCH public, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{analysis,hypotheses_proposal,hypotheses_output}.json` + `workspace/hypotheses-cache.db` | CRÉÉ |
| Skills | `llm/prompts/{p1_analysis,p2_decision,p3_formulation,verifier}_system.md` | CRÉÉ |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-hypotheses.yaml` (+ `sources/providers.yaml` si clarification activée) | CRÉÉ |
| Logs | `core/logging.py` + `workspace/audit-hypotheses.db` | CRÉÉ |
| Données de mission | entrées étudiantes + snapshots amont (objectifs vérifiés) + réponses précédentes | CRÉÉ |
| Stop condition | `core/limits.py` (appels LLM, requêtes réseau, taille), `core/errors.py`, garde anti-non-convergence | CRÉÉ |
| Validation | `schema_validation` → `business_validation` (décision cohérente, statuts, anti-fusion) → `security_validation` | CRÉÉ |
| Evidence | `tests/hypotheses/`, journal d'audit, sortie de session, section « État réel » de l'architecture | CRÉÉ |
| Integration | `api/routes.py` (`POST /hypotheses/analyze`, `POST /hypotheses/{student_id}/{session_id}/decision`, `GET /hypotheses/{student_id}/{session_id}`, `GET /health`), `run-hypotheses.sh` | CRÉÉ |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_objectives` **vérifié** accepté seulement si `validation.verified` ; question + objectifs requis (champ direct ou amont) ; `theoretical_framework`, `existing_hypotheses`, `student_constraints`, `university_instructions`, `supervisor_instructions` = données non fiables |
| Analyse | `schemas/analysis.py` | Phénomène, action attendue, nature du travail, ambiguïtés bloquantes, provenance |
| Décision | `schemas/stages.py` | `hypotheses_decision` ∈ {HYPOTHESES_RECOMMENDED, HYPOTHESES_NOT_REQUIRED, HYPOTHESES_REQUIRE_CLARIFICATION} + justification + questions |
| Hypothèses | `schemas/hypotheses.py` | `Hypothesis` (id, formulation, linked_to, concepts_variables, justification, sources, required_data, limits) ; alignement ; support ; preuves requises |
| Décision étudiante | `schemas/decision.py` | `decision` ∈ {accepted, modified, refused} + commentaire + décision/hypothèses modifiées ; pose `student_validation` |
| Sortie | `schemas/output.py` | Les champs de la SPEC §16 ; `status` dans l'enum |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles codés C1–C13 |

## Bornes par défaut

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 40000 | entrées étudiantes + snapshots amont |
| `max_output_tokens` | 32000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_llm_calls` | 20 | P1 + P2 (+ P3) + vérificateur + re-tentatives + reformulations |
| `max_external_requests` | 24 | clarification documentaire bornée (0 si désactivée) |
| `max_clarification_queries` | 3 | requêtes de clarification de concept |
| `cache_ttl_hours` | 336 | cache clarification (14 j) |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais fusionner Sujet / Problème / Problématique / Question / Objectif / Hypothèse.
- Ne jamais imposer des hypothèses pour remplir un chapitre (pas d'hypothèses forcées).
- Ne jamais écrire une hypothèse qui est une question, un objectif ou un fait établi.
- Ne jamais poser une causalité non établie (préférer une association).
- Ne jamais inventer variable, relation, source, auteur, statistique, théorie ou résultat.
- Ne jamais imposer une méthodologie, un échantillonnage ou une technique de collecte.
- Ne jamais attribuer soi-même le statut `validated` (réservé à la décision étudiante).
- Ne jamais s'auto-attribuer `verified` (réservé au vérificateur indépendant).

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/hypotheses/` (36 tests : règles, campagne, décision, sécurité, API, chaîne amont) |
| Contrôles déterministes seuls | hypothèse à présupposé de fait refusée (H3), causalité non établie refusée (H4), décision incohérente signalée (H1), redondance (H7), anti-fusion (H8) |
| Test réel complet | script hors dépôt + section « État réel » de l'architecture |
| Traces | `workspace/audit-hypotheses.db`, artefacts par session |
