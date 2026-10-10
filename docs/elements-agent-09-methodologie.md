# Éléments de l'Agent Méthodologie (`methodology_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté, vérifié en exécution réelle et validé par le porteur** — voir la section
> « État réel » de `docs/architecture-agent-09-methodologie-v1.md`.

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Méthodologie (protocole de recherche) |
| Technical ID | `methodology_agent` |
| Version | `1.0` |
| Étape du parcours | 9 — Méthodologie (protocole détaillé + rédaction de la section) |
| Paquet | `src/methodology_agent/` (autonome ; aucun agent existant modifié) |
| Port de service | 8090 (`run-protocole.sh`) |
| Profil Hermes | `agent-methode` (`~/.hermes/profiles/agent-methode/`) ; alias `agent-methode` |
| Prédécesseur | Agent 8 — Diagnostic méthodologique (`methodology_diagnostic_agent`, port 8080) |
| Successeur | Agent 10 — Résultats et analyse (`research_results_analysis_agent`) |

**Frontière avec l'agent 8 (à ne jamais franchir dans les deux sens).**

| | Agent 8 — Diagnostic | Agent 9 — Méthodologie |
|---|---|---|
| Question posée | *Quels choix méthodologiques sont appropriés, et pourquoi ?* | *Comment conduire concrètement la recherche, avec quels outils ?* |
| Produit | Six catégories de choix (approche, logique, type, stratégie, collecte, analyse) + articulation | Protocole opérationnel : terrain, population, échantillonnage, données, techniques, instruments, matrice de cohérence, étapes de mise en œuvre + rédaction de la section |
| Livrable | Diagnostic défendable et justifié | Plan exécutable + matrice + proposition de rédaction |
| Réseau | Clarification documentaire bornée (désactivée par défaut) | Aucun réseau par défaut |
| Interdit de l'autre | Ne jamais rédiger la méthodologie finale (rôle de l'agent 9) | Ne jamais re-trancher les choix validés par l'agent 8 |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-methode/SOUL.md` | Rôle étape 9, mission, frontière avec l'étape 8, interdits, chemins |
| Context | `.../agent-methode/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-methode/memories/MEMORY.md`, `memories/USER.md` | Protocole ≠ recherche réalisée, échantillonnage non inventé, pièges P1–P9 |
| Knowledge | `.../agent-methode/knowledge/README.md` | Éléments du protocole, matrice de cohérence, qualité/éthique, prompts |
| Skills | `.../agent-methode/skills/agent-methode/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-methode/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-methode.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement prévu | État |
|---|---|---|
| Purpose / identité | `src/methodology_agent/__init__.py` + prompt `p1_protocol_system.md` § rôle | À CRÉER |
| Mission | `docs/spec-agent-09-methodologie.md` § 3 | Déposée |
| Goal | SPEC § 4 + § 13 (critères de succès) + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-09-methodologie-v1.md`, `config/settings-methode.yaml` | À CRÉER |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-09-methodologie.md` | À CRÉER |
| RAG | Aucune base vectorielle en V1 (SPEC §28) ; aucun réseau par défaut | À CRÉER |
| Tools | `pipeline/` (entrée, sécurité, P1–P4, contrôles déterministes, validations, vérificateur, orchestrateur) | À CRÉER |
| Tool spécifique | `analysis/protocol_rules.py` (vocabulaire d'échantillonnage, interdits de présupposé, cohérence collecte↔analyse issue de l'agent 8) | À CRÉER |
| Permissions | `core/limits.py`, `core/security_rules.py` | À CRÉER — READ session, WRITE workspace, DELETE/DEPLOY non, SEND vérificateur seulement |
| Memory | `workspace/<student_id>/<session_id>/{protocol,coherence_matrix,methodology_draft,methodology_output}.json` | À CRÉER |
| Skills | `llm/prompts/{p1_protocol,p2_instruments,p3_matrix,p4_writing,verifier}_system.md` | À CRÉER |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-methode.yaml` | À CRÉER |
| Logs | `core/logging.py` + `workspace/audit-methode.db` | À CRÉER |
| Données de mission | entrées étudiantes + diagnostic vérifié de l'agent 8 + snapshots amont (question, objectifs, hypothèses) + consignes académiques | À CRÉER |
| Stop condition | `core/limits.py` (appels LLM, taille), `core/errors.py`, garde anti-non-convergence, STOP CONDITIONS SPEC §14 | À CRÉER |
| Validation | `schema_validation` → `business_validation` (R1–R6) → `security_validation` + `protocol_checks` (P1–P9) | À CRÉER |
| Evidence | `tests/methode/`, journal d'audit, sortie de session, section « État réel » de l'architecture | À CRÉER |
| Integration | `api/routes.py` (`POST /methodology/protocol/analyze`, `POST /methodology/protocol/{student_id}/{session_id}/decision`, `GET /methodology/protocol/{student_id}/{session_id}`, `GET /health`), `run-protocole.sh` | À CRÉER |

## Contrats

| Contrat | Fichier prévu | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_*` accepté seulement si le vérificateur de l'amont a validé — **accepter `validation.verified` (agents 1-4) ET `verification_result.verified` (agents 5-8)**, jamais `verified: false` ; diagnostic de l'agent 8 **requis et validé** (statut `valide` / décision étudiante), sinon `MISSING_INFORMATION` |
| Analyse | `schemas/analysis.py` | discipline, éléments disponibles, éléments manquants BLOQUANTS, contradictions, provenance |
| Protocole | `schemas/protocol.py` | `terrain`, `population` (cible / accessible / unité d'analyse), `echantillonnage` (probabiliste ou non, critères inclusion/exclusion, taille + justification), `donnees`, `techniques`, `instruments`, `variables_indicatrices`, `analyse`, `qualite`, `ethique`, `limites`, `etapes_mise_en_oeuvre` |
| Matrice de cohérence | `schemas/matrix.py` | une ligne par objectif : objectif → données nécessaires → technique de collecte → méthode d'analyse → statut (`couverte` / `partielle` / `non couverte`) |
| Rédaction | `schemas/draft.py` | sous-sections retenues uniquement, marquage `prevu` / `realise` / `a_confirmer` |
| Décision étudiante | `schemas/decision.py` | `decision` ∈ {accepted, modified, refused} + commentaire + informations fournies ; pose `student_validation` |
| Sortie | `schemas/output.py` | champs du dossier de preuve (SPEC §16) ; `status` dans l'enum ; statut de document ∈ {brouillon, a_verifier, en_attente_de_validation, valide, a_reviser} |
| Vérificateur | `schemas/verifier.py` | verdict + contrôles codés C1–C13 |

## Bornes par défaut proposées

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 60000 | entrées + diagnostic de l'agent 8 + snapshots amont + consignes académiques |
| `max_output_tokens` | 32000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_llm_calls` | 20 | P1 + P2 + P3 + P4 + vérificateur + re-tentatives + reformulations |
| `max_agent_turns` | 8 | |
| `max_external_requests` | 0 | aucun réseau par défaut (réactivables par configuration) |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais choisir une méthode en fonction de la seule discipline (SPEC §10.2).
- Ne jamais confondre **protocole prévu** et **recherche déjà réalisée** (SPEC §10.3, §2) — aucune
  collecte, aucun entretien, aucune analyse présenté au passé sans preuve.
- Ne jamais inventer participants, échantillon, dates, résultats, autorisations ou données (§10.4).
- Ne jamais imposer une taille d'échantillon sans justification (§10.5) ni supposer qu'une enquête de
  terrain est nécessaire (§10.6).
- Ne jamais imposer d'hypothèses quand elles ne sont pas pertinentes (§10.7) — la décision de
  l'agent 7 fait foi.
- Ne jamais proposer une analyse incompatible avec la nature ou la qualité des données prévues (§10.8).
- Ne jamais affirmer une causalité que le dispositif ne permet pas (§10.9).
- Ne jamais présenter une consigne académique générale comme une règle de l'établissement de
  l'étudiant (§10.12, §10.13) ; si les consignes manquent, le dire.
- Ne jamais modifier silencieusement la question, les objectifs ou les hypothèses (§10.16).
- Ne jamais s'auto-attribuer `verified` ni `validated` (vérificateur indépendant + décision humaine).

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/methode/` (règles, campagne, décision, sécurité, API, chaîne amont) |
| Contrôles déterministes seuls | à définir avec le porteur (voir § Décisions de l'architecture) |
| Test réel complet | `scripts/e2e_chaine.py` étendu à l'étape 9 (modèle réel, réseau désactivé) |
| Traces | `workspace/audit-methode.db`, artefacts par session |
