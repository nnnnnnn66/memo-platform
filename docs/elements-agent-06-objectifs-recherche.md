# Éléments de l'Agent Objectifs de recherche (`research_objectives_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté et vérifié en exécution réelle** (voir la section « État réel » de
> `docs/architecture-agent-06-objectifs-recherche-v1.md`).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Objectifs de recherche |
| Technical ID | `research_objectives_agent` |
| Version | `1.0` |
| Étape du parcours | 6 — Objectifs |
| Paquet | `src/research_objectives_agent/` (autonome ; aucun agent existant modifié) |
| Port de service | 8060 (`run-objectifs.sh`) |
| Profil Hermes | `agent-objectifs` (`~/.hermes/profiles/agent-objectifs/`) ; alias `agent-objectifs` |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-objectifs/SOUL.md` | Rôle étape 6, objectif, interdits, chemins |
| Context | `.../agent-objectifs/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-objectifs/memories/MEMORY.md`, `memories/USER.md` | Neutralité, anti-présupposé, anti-fusion |
| Knowledge | `.../agent-objectifs/knowledge/README.md` | Verbes d'action, distinctions, human gate |
| Skills | `.../agent-objectifs/skills/agent-objectifs/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-objectifs/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (recherche publique sans clé) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-objectifs.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/research_objectives_agent/__init__.py` + prompt `p1_analysis_system.md` § rôle | CRÉÉ |
| Mission | `docs/spec-agent-06-objectifs-recherche.md` § 3 | Déposée |
| Goal | SPEC § 4 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-06-objectifs-recherche-v1.md`, `config/settings-objectifs.yaml` | CRÉÉ |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-06-objectifs-recherche.md`, (`sources/providers.yaml`) | CRÉÉ |
| RAG | Aucune base vectorielle en V1 ; clarification documentaire = API publiques (`sources/`) | CRÉÉ |
| Tools | `pipeline/` (input, sécurité, P1–P3, contrôles déterministes, validations, vérificateur, orchestrateur) | CRÉÉ |
| Tool spécifique | `analysis/objective_rules.py` (verbes, neutralité, redondance, délimitation) + `sources/adapters/*.py` | CRÉÉ |
| Permissions | `core/limits.py`, `core/security_rules.py` | CRÉÉ — READ session + RESEARCH public, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{question_analysis,objectives_proposal,objectives_output}.json` + `workspace/objectifs-cache.db` | CRÉÉ |
| Skills | `llm/prompts/{p1_analysis,p2_general,p3_specific,verifier}_system.md` | CRÉÉ |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-objectifs.yaml` (+ `sources/providers.yaml` si clarification activée) | CRÉÉ |
| Logs | `core/logging.py` + `workspace/audit-objectifs.db` | CRÉÉ |
| Données de mission | entrées étudiantes + snapshots amont (question de recherche vérifiée) + réponses précédentes | CRÉÉ |
| Stop condition | `core/limits.py` (appels LLM, requêtes réseau, taille), `core/errors.py`, garde anti-non-convergence | CRÉÉ |
| Validation | `schema_validation` → `business_validation` (neutralité, anti-présupposé, anti-fusion, statuts) → `security_validation` | CRÉÉ |
| Evidence | `tests/objectifs/`, journal d'audit, sortie de session, section « État réel » de l'architecture | CRÉÉ |
| Integration | `api/routes.py` (`POST /objectives/analyze`, `POST /objectives/{student_id}/{session_id}/decision`, `GET /objectives/{student_id}/{session_id}`, `GET /health`), `run-objectifs.sh` | CRÉÉ |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_question` **vérifié** accepté seulement si `validation.verified` ; `main_research_question` OU amont vérifié requis ; `objectives_draft`, `student_constraints`, `university_instructions`, `supervisor_instructions` = données non fiables |
| Analyse | `schemas/analysis.py` | `QuestionAnalysis` : phénomène, action attendue, dimensions, périmètre, ambiguïtés, provenance |
| Objectifs | `schemas/objectives.py` | `general_objective` (str), `specific_objectives` (list[str]), alignement, faisabilité, ambiguïtés |
| Décision étudiante | `schemas/decision.py` | `decision` ∈ {accepted, modified, refused} + commentaire + objectifs modifiés ; pose `student_validation` |
| Sortie | `schemas/output.py` | Les 15 champs de la SPEC §16 ; `status` dans l'enum |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles codés C1–C13 |

## Bornes par défaut

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 40000 | entrées étudiantes + snapshots amont |
| `max_output_tokens` | 32000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_llm_calls` | 20 | P1 + P2 + P3 + vérificateur + re-tentatives + reformulations |
| `max_external_requests` | 24 | clarification documentaire bornée (0 si désactivée) |
| `max_clarification_queries` | 3 | requêtes de clarification de concept |
| `cache_ttl_hours` | 336 | cache clarification (14 j) |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais fusionner Sujet / Problème / Problématique / Question de recherche / Objectif / Hypothèse.
- Ne jamais écrire un objectif qui présuppose un résultat (« démontrer/prouver/montrer que »).
- Ne jamais écrire un objectif qui tient lieu d'hypothèse ni une activité administrative.
- Ne jamais ajouter une zone géographique, une période ou une population non fournie.
- Ne jamais imposer une méthodologie, un échantillonnage ou une technique de collecte.
- Ne jamais attribuer soi-même le statut `validated` (réservé à la décision étudiante).
- Ne jamais s'auto-attribuer `verified` (réservé au vérificateur indépendant).

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/objectifs/` (34 tests : neutralité, campagne, décision, sécurité, API, chaîne amont) |
| Contrôles déterministes seuls | test : objectif à présupposé refusé (O2), activité refusée (O3), redondance détectée (O6), année inventée signalée (O8) |
| Test réel complet | script hors dépôt + section « État réel » de l'architecture |
| Traces | `workspace/audit-objectifs.db`, artefacts par session |
