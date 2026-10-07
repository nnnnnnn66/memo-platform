# Éléments de l'Agent Revue de littérature & Diagnostic Épistémologique (`literature_review_agent`)

> Fiche remplie selon `docs/elements-agent-z.md`. État : **architecture présentée — implémentation
> NON commencée** (portillon §42 : en attente de validation humaine).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Revue de littérature & Diagnostic Épistémologique |
| Technical ID | `literature_review_agent` |
| Version prévue | `1.0` |
| Étape du parcours | 3 — Revue de littérature |
| Paquet prévu | `src/literature_review_agent/` (autonome ; aucun agent existant modifié) |
| Port de service prévu | 8030 (`run-litterature.sh`) |
| Profil Hermes | `agent-litterature` (`~/.hermes/profiles/agent-litterature/`) ; alias `agent-litterature` |

## Profil Hermes propre à l'agent (créé)

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-litterature/SOUL.md` | Rôle étape 3, objectif documentaire, interdits, chemins |
| Context | `.../agent-litterature/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-litterature/memories/MEMORY.md`, `memories/USER.md` | Fournisseurs vérifiés, écartés et pourquoi, invariants |
| Knowledge | `.../agent-litterature/knowledge/README.md` | Priorités SPEC §7, matrice §4.4A, retrieval déterministe |
| Skills | `.../agent-litterature/skills/agent-litterature/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-litterature/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé dupliquée ; la recherche n'en utilise aucune |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-litterature.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/literature_review_agent/__init__.py` + prompt `p1_keywords_system.md` § rôle | À CRÉER |
| Mission | `docs/spec-agent-03-revue-litterature.md` § 3 | Déposée |
| Goal | SPEC § 4 + objectif documentaire (jusqu'à 60, sans quota artificiel) | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-03-revue-litterature-v1.md`, `config/settings-litterature.yaml` | Architecture présentée ; config À CRÉER |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-03-revue-litterature.md`, `sources/providers.yaml` | À CRÉER (contenu défini dans le profil) |
| RAG | `src/literature_review_agent/sources/` (retrieval déterministe, cache, liste blanche) | À CRÉER ; aucune base vectorielle |
| Tools | `pipeline/` (input, sécurité, P1, retrieval, dédup/notation, P2 par lots, P3, P4, P5, validations, vérificateur, orchestrateur) | À CRÉER |
| Tool spécifique | `sources/adapters/*.py` (14 fournisseurs + Unpaywall) | À CRÉER |
| Permissions | `core/limits.py`, `core/security_rules.py`, `sources/registry.py` (hôtes en liste blanche) | À CRÉER — READ session + RESEARCH public, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{corpus,comparison,synthesis,diagnostic}.json` + `workspace/documents-cache.db` | À CRÉER |
| Skills | `llm/prompts/{p1_keywords,p2_scoring,p3_comparison,p4_synthesis,p5_diagnosis,verifier}_system.md` | À CRÉER |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise pour la recherche |
| Configuration | `config/settings-litterature.yaml` (+ `sources/providers.yaml`) | À CRÉER ; ajout d'un fournisseur = configuration |
| Logs | `core/logging.py` + `workspace/audit-litterature.db` | À CRÉER |
| Données de mission | entrées étudiantes, documents fournis (texte), `documents-cache.db` | À CRÉER |
| Stop condition | `core/limits.py` (requêtes, documents, lots, budget), `core/errors.py` (8 états), garde anti-non-convergence | À CRÉER |
| Validation | `schema_validation` → `business_validation` (ancrage, dédup, cohérence matrice, style biblio) → `security_validation` | À CRÉER |
| Evidence | `tests/litterature/`, journal d'audit, corpus et fiches par document, section « État réel » de l'architecture | À CRÉER |
| Integration | `api/routes.py` (`POST /literature/review`, `GET /literature/{student_id}/{session_id}`, `GET /health`), `run-litterature.sh` | À CRÉER |

## Contrats prévus

| Contrat | Fichier prévu | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | Prérequis SPEC §5 (sujet, niveau, discipline, zone, style biblio) ; `upstream_subject`/`upstream_problem` acceptés seulement si vérifiés |
| Mots-clés (P1) | `schemas/keywords.py` | Arborescence concepts → mots-clés FR/EN + stratégie + cascade géographique + bornes de requêtes |
| Document | `schemas/document.py` | Métadonnées issues de l'API uniquement ; `full_text_available` ; `geographic_scope` détecté ; pertinence |
| Sortie | `schemas/output.py` | `corpus`, `comparison`, `synthesis`, `diagnosis`, `bibliography`, `evidence`, `validation` |
| Diagnostic | `schemas/diagnosis.py` | `matrix_row_id` ∈ matrice §4.4A + indicateurs → logique/type/approche/techniques + justification |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles codés L1–L12 |

## Bornes prévues (à valider)

`MAX_OUTPUT_TOKENS=16000` (leçon des modèles raisonneurs) · `TIMEOUT=90 s` ·
`MAX_TOKENS_TOTAL_CAMPAGNE` (garde-fou de coût) · `MAX_SEARCH_QUERIES=12` ·
`MAX_RESULTS_PER_QUERY=25` · `MAX_DOCUMENTS=60` (objectif) · `MIN_DOCUMENTS_USEFUL=10`
(en dessous : `corpus_sufficiency=insufficient`) · `MAX_EXTERNAL_REQUESTS=80` ·
`SOURCE_TIMEOUT=25 s` · `MAX_ABSTRACT_CHARS=1200` · `DOCUMENTS_PER_SCORING_BATCH=12` ·
`MAX_SCORING_BATCHES=6` · `CACHE_TTL_HOURS=336` (14 j) · `UNPAYWALL_MAX_LOOKUPS=60` ·
`MAX_VERIFICATION_RETRIES=3`

## Interdictions propres à l'étape

- Ne jamais inventer une référence, un auteur, un titre, une revue, une année, un DOI, un lien.
- Ne jamais compléter un quota par des documents non pertinents (60 = objectif, pas obligation).
- Le diagnostic méthodologique / épistémologique est une **proposition argumentée**, jamais une
  décision imposée à l'étudiant.
- Ne jamais produire la problématique ni la question de recherche de l'étudiant.
- Ne jamais ajouter le contexte ivoirien/africain sans justification du sujet.
- Aucun contournement de paywall ; aucune source sans auteur identifiable comme source principale.
- Ne jamais s'auto-attribuer `verified`.

## Preuves attendues

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/litterature/` (fixtures de fournisseurs, dédup, scoring, matrice, bibliographie) |
| Recherche réelle sans LLM | script de campagne sur sujet témoin (nombre de documents, fournisseurs, doublons) |
| Test réel complet | script hors dépôt + section « État réel » de l'architecture |
| Traces | `workspace/audit-litterature.db`, `documents-cache.db`, artefacts par session |
