# Éléments de l'Agent Problème de recherche (`research_problem_agent`)

> Fiche remplie selon `docs/elements-agent-z.md`. État : **implémenté et validé** (voir
> `docs/architecture-agent-02-probleme-v1.md`, section « État réel de l'implémentation »).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Problème de recherche |
| Technical ID | `research_problem_agent` |
| Version | `1.0` |
| Étape du parcours | 2 — Problème de recherche |
| Paquet | `src/research_problem_agent/` (autonome ; l'Agent Sujet n'est pas modifié) |
| Port de service | 8020 (`run-probleme.sh`) |
| Profil Hermes | `agent-probleme` (`~/.hermes/profiles/agent-probleme/`) ; lancement du profil : `agent-probleme` |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-probleme/SOUL.md` | Rôle étape 2, ancrage des sources, interdits |
| Context | `.../agent-probleme/.hermes.md` | Règles projet, liaison avec l'Agent Sujet (`upstream_subject` vérifié) |
| Memory | `.../agent-probleme/memories/MEMORY.md`, `memories/USER.md` | Faits de l'agent (fournisseurs, bornes, pièges) |
| Knowledge | `.../agent-probleme/knowledge/README.md` | Priorités de sources SPEC §7 + retrieval déterministe |
| Skills | `.../agent-probleme/skills/agent-probleme/SKILL.md` | Méthode : ajouter un fournisseur, ancrage, tests |
| Configuration | `.../agent-probleme/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé dupliquée ; la recherche n'en utilise aucune |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-probleme.db` (service) | |

## Les 19 éléments

| Élément | Emplacement concret | Contenu / état |
|---|---|---|
| Purpose / identité | `src/research_problem_agent/__init__.py`, `llm/prompts/problem_phase1_system.md`, `problem_phase2_system.md` | « Formule le PROBLÈME, provisoire et fidèle ; ni problématique ni question de recherche » |
| Mission | `docs/spec-agent-02-probleme.md` § 3 | Identifier, analyser, délimiter, formuler le problème |
| Goal | SPEC § 4 + grille `status` de `problem_phase2_system.md` | Formulation documentée, délimitée, transparente sur les incertitudes |
| Context | `AGENTS.md`, `docs/architecture-agent-02-probleme-v1.md`, `config/settings-probleme.yaml` | Peut recevoir `upstream_subject` **vérifié** de l'Agent Sujet |
| Knowledge | `llm/prompts/*.md` + 12 fournisseurs déclarés dans `sources/providers.yaml` | Sources prioritaires de la SPEC §7 |
| RAG | `src/research_problem_agent/sources/` | Retrieval **déterministe** (API officielles gratuites, cache SQLite). Pas de base vectorielle, pas d'embeddings en V1 |
| Tools | `pipeline/` : input_controller, input_validation, security_layer, problem_agent, **sources_stage**, output_parser, schema_validation, business_validation, security_validation, problem_verifier, orchestrator | Deux phases LLM encadrant l'étage de recherche |
| Tool spécifique | `sources/adapters/{openalex,crossref,europepmc,doaj,pubmed,hal,arxiv,openaire,zenodo,datacite,datagouv,dataeuropa}.py` | Un adaptateur par fournisseur ; 3 fournisseurs désactivés avec justification en config |
| Permissions | `core/limits.py`, `core/security_rules.py`, `sources/registry.py` (hôtes en liste blanche) | READ session + sources publiques ; WRITE workspace ; DELETE/DEPLOY/SEND non ; aucune URL arbitraire (anti-SSRF) |
| Memory | `workspace/<student_id>/<session_id>/problem_output.json`, `verifier_output.json`, `sources.json` + `workspace/sources-cache.db` | Isolation par étudiant ; cache = mémoire de recherche |
| Skills | `llm/prompts/problem_phase1_system.md` (analyse + requêtes), `problem_phase2_system.md` (formulation ancrée), `verifier_system.md` | |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise pour la recherche (fournisseurs sans clé) |
| Configuration | `config/settings-probleme.yaml` (+ `sources/providers.yaml`) | Ajouter un fournisseur = configuration, pas de code |
| Logs | `core/logging.py` + `workspace/audit-probleme.db` (statut, tentatives, requêtes réseau, cache, fournisseurs, sources) | |
| Données de mission | entrées étudiantes, documents collés, `sources-cache.db` (réponses réelles des fournisseurs) | |
| Stop condition | `core/limits.py` (max_tool_calls, max_external_requests, source_timeout), `core/errors.py`, garde anti-non-convergence de la boucle de vérification | |
| Validation | `schema_validation` → `business_validation` (anti-fusion, fidélité, **ancrage strict des sources**) → `security_validation` ; puis vérificateur indépendant V1–V11 | |
| Evidence | `tests/probleme/` (75 tests), `workspace/audit-probleme.db`, section « État réel » de l'architecture | Test réel : sujet précis → `verified` en une passe |
| Integration | `api/routes.py` : `POST /problem/analyze`, `GET /problem/{student_id}/{session_id}`, `GET /health` | Liaison Agent Sujet → Agent Problème par payload vérifié (pas d'orchestrateur global, §44) |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` (`ProblemRequest`) | `subject_text` obligatoire ; `upstream_subject` refusé s'il n'est pas `verified` |
| Phase 1 | `schemas/search_intent.py` (`Phase1Output`, `SearchIntent`) | ≤ 4 requêtes, `kind` ∈ {publications, statistics, repository, any} |
| Sortie | `schemas/output.py` (`ProblemOutput`, SPEC §16 A–H) | `sources[]` ancrées au `SourceSet` ; `provenance = external` dès qu'un `source_id` est cité |
| Source | `sources/source_set.py` | Ids stables S1…Sn, dédoublonnage DOI+URL, record sans DOI ni URL écarté |
| Vérificateur | `schemas/verifier.py` | 11 contrôles V1–V11 ; format des listes strict + normalisation |

## Bornes en vigueur

`max_input_size: 20000` · `max_output_tokens: 16000` · `max_tool_calls: 6` ·
`max_agent_turns: 6` · `max_verification_retries: 3` · `timeout: 90 s` ·
`max_external_requests: 10` · `max_search_results: 5` · `max_search_queries: 4` ·
`source_timeout: 20 s` · `max_source_snippet: 800` · `cache_ttl_hours: 168` ·
`max_providers_per_intent: 3` · `max_sources_total: 10`

## Interdictions propres à l'étape

- Ne jamais produire la problématique, la question de recherche, les objectifs, les hypothèses,
  la méthodologie ni un plan de mémoire.
- Ne jamais inventer : fait, statistique, référence, lien, date → lacune déclarée ou question.
- Ne citer qu'un `source_id` réellement récupéré (un faux lien ne franchit pas la validation).
- Ne jamais présenter une déduction comme un fait ; ne jamais s'auto-attribuer `verified`.

## Preuves mesurées

| Preuve | Résultat |
|---|---|
| Tests hors réseau | 75/75 (fonctionnels 15–21, sécurité 22–30, normalisation 31, sources) ; suite entière sans réseau, 0,7 s |
| Étage de sources en réseau réel | 15 sources / 4 fournisseurs / 6 requêtes, aucun échec |
| Test réel (DeepSeek + recherche réelle) | télétravail/Abidjan → `ready_for_verification` puis `verified` en 1 passe (3 appels LLM, 4 sources citées) ; « le sport », « l'impact du numérique » → `needs_clarification` |
| Traces | `workspace/audit-probleme.db`, artefacts par session, cache de sources |
