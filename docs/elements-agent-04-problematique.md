# Éléments de l'Agent Problématique & Construction Théorique (`problematization_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **architecture présentée — implémentation NON commencée** (portillon §42 : en attente de
> validation humaine).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Problématique & Construction Théorique |
| Technical ID | `problematization_agent` |
| Version prévue | `1.0` |
| Étape du parcours | 4 — Problématique |
| Paquet prévu | `src/problematization_agent/` (autonome ; aucun agent existant modifié) |
| Port de service prévu | 8040 (`run-problematique.sh`) |
| Profil Hermes | `agent-problematique` (`~/.hermes/profiles/agent-problematique/`) ; alias `agent-problematique` |

## Profil Hermes propre à l'agent (créé)

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-problematique/SOUL.md` | Rôle étape 4, objectif, interdits, chemins |
| Context | `.../agent-problematique/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-problematique/memories/MEMORY.md`, `memories/USER.md` | Gap, ancrage, alignement, invariants |
| Knowledge | `.../agent-problematique/knowledge/README.md` | Cadres de problématisation, types de gap, ancrage, gap check |
| Skills | `.../agent-problematique/skills/agent-problematique/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-problematique/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé dupliquée ; le gap check n'utilise aucune clé |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-problematique.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/problematization_agent/__init__.py` + prompt `p1_problem_mapping_system.md` § rôle | À CRÉER |
| Mission | `docs/spec-agent-04-problematique.md` § 3 | Déposée |
| Goal | SPEC § 4 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-04-problematique-v1.md`, `config/settings-problematique.yaml` | Architecture présentée ; config À CRÉER |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-04-problematique.md`, `sources/providers.yaml` | À CRÉER (contenu défini dans le profil) |
| RAG | `anchoring/` (index + ancrage verbatim du corpus amont) + `sources/` (gap check déterministe) | À CRÉER ; aucune base vectorielle |
| Tools | `pipeline/` (input, sécurité, P1–P5, ancrage, gap check, alignement, validations, vérificateur, orchestrateur) | À CRÉER |
| Tool spécifique | `sources/adapters/*.py` (gap check académique) + `anchoring/quote_anchoring.py` | À CRÉER |
| Permissions | `core/limits.py`, `core/security_rules.py`, `sources/registry.py` (hôtes en liste blanche) | À CRÉER — READ session + RESEARCH public, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{problem_mapping,confrontation,gap,note,alignment}.json` + `workspace/gap-check-cache.db` | À CRÉER |
| Skills | `llm/prompts/{p1_problem_mapping,p2_confrontation,p3_gap,p4_justification,p5_question_objectives,verifier}_system.md` | À CRÉER |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise pour le gap check |
| Configuration | `config/settings-problematique.yaml` (+ `sources/providers.yaml`) | À CRÉER ; ajout d'un fournisseur = configuration |
| Logs | `core/logging.py` + `workspace/audit-problematique.db` | À CRÉER |
| Données de mission | entrées étudiantes, corpus amont (documents + textes lus), `gap-check-cache.db` | À CRÉER |
| Stop condition | `core/limits.py` (appels LLM, requêtes réseau, taille), `core/errors.py`, garde anti-non-convergence | À CRÉER |
| Validation | `schema_validation` → `business_validation` (ancrage, anti-fusion, cohérence gap/alignement) → `security_validation` | À CRÉER |
| Evidence | `tests/problematique/`, journal d'audit, note produite par session, section « État réel » de l'architecture | À CRÉER |
| Integration | `api/routes.py` (`POST /problematique/analyze`, `GET /problematique/{student_id}/{session_id}`, `GET /health`), `run-problematique.sh` | À CRÉER |

## Contrats prévus

| Contrat | Fichier prévu | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | Prérequis SPEC §5 (sujet, discipline, problème de terrain) + `upstream_literature` **vérifié** (obligatoire) ; `upstream_subject` / `upstream_problem` acceptés seulement si vérifiés |
| Cartographie (P1) | `schemas/problem.py` | `phenomene`, `population`, `zone`, `dysfonctionnement` + provenance (fourni / déduit / inconnu) |
| Gap | `schemas/gap.py` | `type` ∈ {contextuelle, conceptuelle, empirique, methodologique} + `evidence[]` (doc_id + citation ancrée) |
| Sortie | `schemas/output.py` | `problem_mapping`, `literature_confrontation`, `gap`, `justification`, `problematique_note`, `research_question`, `objectives`, `methodological_alignment`, `bibliography`, `evidence`, `validation` |
| Question de recherche | `schemas/question.py` | Champ **distinct** de la problématique, `status = "proposed"` (proposition de transition) |
| Alignement | `schemas/alignment.py` | `logic` ∈ {inductive, deductive, hypothetico-deductive, abductive} + type/approche/techniques + cohérence amont |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles codés L1–L12 |

## Bornes par défaut (à ajuster et justifier)

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 60000 | le corpus amont (extraits + métadonnées) entre dans l'entrée |
| `max_output_tokens` | 16000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_documents_read` | 60 | lecture/ancrage bornés au corpus amont |
| `max_verbatim_chars` | 600 | une citation au-delà est refusée (ancrage plus sûr) |
| `min_anchoring_rate` | 1.0 | toute citation non ancrée est retirée (pas seulement un taux plancher) |
| `max_external_requests` | 20 | gap check borné |
| `max_gap_check_queries` | 4 | requêtes de vérification du gap |
| `cache_ttl_hours` | 336 | cache gap check (14 j) |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Zéro hallucination (LLM07) : aucune référence, statistique, date ou lacune inventée ; aucun propos
  attribué à tort à un ouvrage.
- Aucune source citée hors des documents réellement fournis par la revue de littérature ; toute
  citation doit être un fragment verbatim **présent dans le texte** (sinon retirée).
- Aucun `doc_id` renuméroté : les identifiants sont ceux, stables, du corpus amont.
- Ne jamais fusionner Sujet / Problème / Problématique / Question de recherche / Objectifs.
- Ne jamais livrer la question de recherche ou les objectifs comme **validés** : ce sont des
  propositions de transition (`status = "proposed"`).
- Ne jamais imposer une logique quantitative/déductive contre ce que montre la littérature.
- Ne jamais s'auto-attribuer `verified` (réservé au vérificateur indépendant).

## Preuves attendues

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/problematique/` (LLM simulé + corpus de fixtures + ancrage + gap check simulé) |
| Ancrage verbatim seul | test sur corpus réel : citation réelle acceptée, citation inventée **courte** refusée |
| Test réel complet | script hors dépôt + section « État réel » de l'architecture |
| Traces | `workspace/audit-problematique.db`, `gap-check-cache.db`, artefacts par session |
