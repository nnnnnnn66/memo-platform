# Éléments de l'Agent Sujet (`subject_agent`)

> Fiche remplie selon `docs/elements-agent-z.md`. État : **implémenté et validé** (voir
> `docs/architecture-v1.md` et la section « État réel » de `docs/architecture-agent-02-probleme-v1.md`).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Sujet |
| Technical ID | `subject_agent` |
| Version | `1.0` |
| Étape du parcours | 1 — Sujet |
| Paquet | `src/subject_agent/` |
| Port de service | 8010 (`run.sh`) |
| Profil Hermes | `agent-sujet` (`~/.hermes/profiles/agent-sujet/`) ; lancement du profil : `agent-sujet` |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-sujet/SOUL.md` | Rôle étape 1, interdits, chemins, méthode |
| Context | `.../agent-sujet/.hermes.md` | Règles projet, maillon couvert, liaison avec l'étape 2 |
| Memory | `.../agent-sujet/memories/MEMORY.md`, `memories/USER.md` | Faits de l'agent, profil du porteur de projet |
| Knowledge | `.../agent-sujet/knowledge/README.md` | Sources de connaissance + absence de RAG en V1 |
| Skills | `.../agent-sujet/skills/agent-sujet/SKILL.md` | Méthode de travail propre à l'agent |
| Configuration | `.../agent-sujet/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé dupliquée dans le profil |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit.db` (service) | |

## Les 19 éléments

| Élément | Emplacement concret | Contenu / état |
|---|---|---|
| Purpose / identité | `src/subject_agent/__init__.py`, `llm/prompts/subject_system.md` § TON RÔLE | « Ni rédacteur, ni générateur : questionne, structure, délimite le sujet » |
| Mission | `docs/spec-agent-sujet-v1.md` § 3 | Clarté/délimitation/structuration du sujet |
| Goal | `docs/spec-agent-sujet-v1.md` § 4 + grille `status` du prompt | Sujet clair et exploitable par l'étape suivante |
| Context | `AGENTS.md`, `README.md`, `docs/architecture-v1.md`, `config/settings.yaml` | Contrat d'entrée `schemas/input.py` |
| Knowledge | `llm/prompts/subject_system.md` | Pas de recherche externe en V1 |
| RAG | — | **Aucun** : `max_external_requests: 0` (SPEC §28 : pas de base vectorielle) |
| Tools | `pipeline/` : input_controller, input_validation, security_layer, subject_agent, output_parser, schema_validation, business_validation, security_validation, subject_verifier, orchestrator | Pipeline de garde-fous linéaire |
| Tool spécifique | — (LLM + validations uniquement) | |
| Permissions | `core/limits.py`, `core/security_rules.py` | `read: session_only`, `write: workspace_only`, `delete/deploy/send: false` |
| Memory | `workspace/<student_id>/<session_id>/subject_output.json`, `verifier_output.json` | Isolation par `student_id`/`session_id` |
| Skills | `llm/prompts/subject_system.md` (agent), `llm/prompts/verifier_system.md` (vérificateur) | Prompts = compétences réutilisables de l'agent |
| API keys | `~/.hermes/.env` (`DEEPSEEK_API_KEY` / `GOOGLE_API_KEY`) via `core/config.py` | Jamais dans le code, la config, les logs |
| Configuration | `config/settings.yaml` | LLM, bornes, chemins, sécurité (propre à cet agent) |
| Logs | `core/logging.py` (filtre de secrets) + `workspace/audit.db` (SQLite stdlib) | |
| Données de mission | entrées étudiantes (`SubjectRequest`), artefacts de session | |
| Stop condition | `core/limits.py`, `core/errors.py` (8 états), `MAX_VERIFICATION_RETRIES` | Arrêt propre, pas de boucle infinie |
| Validation | `schema_validation` → `business_validation` (anti-fusion, fidélité) → `security_validation` | 1 re-tentative puis `blocked` |
| Evidence | `tests/functional/` (1–5, 14), `tests/security/` (6–13), `workspace/audit.db` | 22 tests, test réel OK |
| Integration | `api/routes.py` : `POST /subject/analyze`, `GET /subject/{student_id}/{session_id}`, `GET /health` | Sortie `verified` consommable par l'Agent Problème via `upstream_subject` |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` (`SubjectRequest`) | `subject_text` obligatoire, `student_id` pour l'isolation |
| Sortie | `schemas/output.py` (`SubjectOutput`, SPEC §10) | Aucun champ problème/problématique/question (anti-fusion) ; `validation.verified` réservé au vérificateur |
| Vérificateur | `schemas/verifier.py` | 11 contrôles C1–C11 ; `corrections`/`flags` normalisés en chaînes |

## Bornes en vigueur

`max_input_size: 20000` · `max_output_tokens: 4000` · `max_tool_calls: 0` ·
`max_agent_turns: 6` · `max_verification_retries: 3` · `timeout: 30 s` ·
`max_external_requests: 0` · `max_search_results: 5`

## Interdictions propres à l'étape

- Ne jamais produire problème / problématique / question de recherche / objectifs / hypothèses.
- Ne rien inventer ; information non fournie et non vérifiée = inconnue.
- Ne jamais s'auto-attribuer `verified`.

## Preuves mesurées

| Preuve | Résultat |
|---|---|
| Tests hors réseau | 22/22 (fonctionnels + sécurité, LLM simulé) |
| Test réel (DeepSeek) | sujet précis → `ready_for_verification` puis verdict vérificateur ; sujets vague/large → `needs_clarification` |
| Traces | `workspace/audit.db`, artefacts par session |
