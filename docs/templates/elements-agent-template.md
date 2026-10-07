# Éléments de l'agent <NOM> (`<agent_id>`)

> Fiche à remplir pour CHAQUE nouvel agent. Un élément non encore créé s'écrit « À CRÉER » avec
> la raison. Référentiel : `docs/elements-agent-z.md`. Copier ce fichier en
> `docs/elements-agent-0X-<nom>.md` et remplacer tous les chevrons.

## Identité

| Champ | Valeur |
|---|---|
| Nom | |
| Technical ID | `<agent_id>` (minuscules, underscores) |
| Version | `1.0` |
| Étape du parcours | (1 Sujet, 2 Problème, 3 Revue de littérature, …) |
| Paquet | `src/<agent_id>/` |
| Port de service | `80XX` |

## Les 19 éléments

| Élément | Emplacement concret | Contenu / état |
|---|---|---|
| Purpose / identité | `src/<agent_id>/__init__.py`, prompt système § rôle | |
| Mission | `docs/spec-agent-0X-<nom>.md` § MISSION | |
| Goal | SPEC § OBJECTIVE + grille `status` du prompt | |
| Context | `AGENTS.md`, `README.md`, `config/settings-<agent>.yaml` | |
| Knowledge | `llm/prompts/*.md`, `docs/*.md`, (`sources/providers.yaml`) | |
| RAG | (`src/<agent_id>/sources/`) | Aucune base vectorielle en V1 ; retrieval = API officielles |
| Tools | modules du `pipeline/` | |
| Tool spécifique | `sources/adapters/*.py` ou outil dédié | |
| Permissions | `core/limits.py`, `core/security_rules.py`, matrice SPEC | READ oui / WRITE workspace / DELETE-DEPLOY-SEND non |
| Memory | `workspace/<student_id>/<session_id>/` | Isolation par étudiant |
| Skills | `llm/prompts/` (rôle + vérificateur) | |
| API keys | `~/.hermes/.env` via `core/config.py` | Jamais dans le code/la config/les logs |
| Configuration | `config/settings-<agent>.yaml` | Propre à l'agent |
| Logs | `core/logging.py` + `workspace/audit-<agent>.db` | Filtré (aucun secret) |
| Données de mission | entrées étudiantes, documents, (`sources-cache.db`) | |
| Stop condition | `core/limits.py`, `core/errors.py`, garde anti-non-convergence | |
| Validation | `pipeline/schema_validation.py` → `business_validation.py` → `security_validation.py` | |
| Evidence | `tests/<agent>/`, journal d'audit, sorties de session | |
| Integration | `api/routes.py`, `run-<agent>.sh`, payload amont vérifié | |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | champs, provenances (fourni / déduit / inconnu), tailles |
| Sortie | `schemas/output.py` | statuts, anti-fusion, aucun champ de l'étape suivante |
| Vérificateur | `schemas/verifier.py` | verdict + contrôles codés + format des listes |
| Source (si recherche) | `sources/source_set.py` | ancrage obligatoire, ids stables |

## Bornes par défaut (à ajuster et justifier)

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 20000 | |
| `max_output_tokens` | 16000 | modèle raisonneur : les tokens de raisonnement consomment le budget |
| `timeout` | 90 s | |
| `max_external_requests` | 10 | |
| `max_verification_retries` | 3 | |
| autres | | |

## Interdictions propres à l'étape

- Ne jamais fusionner Sujet / Problème / Problématique / Question de recherche.
- Ne rien inventer (fait, statistique, référence, lien, date) → `not_verified` ou question.
- Ne pas produire le travail de l'étudiant ni celui de l'étape suivante.
- Ne jamais s'auto-attribuer `verified` (réservé au vérificateur).

## Vérification et preuve

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/<agent>/` (LLM simulé, fixtures de fournisseurs) |
| Test réel | script hors dépôt + section « État réel » de `docs/architecture-*.md` |
| Traces | `workspace/audit-<agent>.db`, artefacts de session |
| Résultat mesuré | à reporter ici (statuts observés, verdicts, nombre d'appels, sources citées) |
