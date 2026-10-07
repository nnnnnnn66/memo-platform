# Éléments d'un AGENT Z — référentiel de cadrage

> Transcrit du document fourni par le porteur de projet (« Element-AgentZ »).
> **Règle permanente** : dès qu'un agent est confié, on lui donne **ses éléments propres**,
> on ne redemande pas où les mettre ni à quoi ils servent. Chaque agent possède son cadre
> autonome : ce document définit la liste des éléments, `docs/templates/elements-agent-template.md`
> fournit le squelette, et `docs/elements-agent-0X-*.md` contient la fiche remplie de chaque agent.

## 1. La grille d'origine (Element AGENT Z → dans Hermes, concrètement)

| Élément | Dans Hermes, concrètement |
|---|---|
| **Purpose / identité** | `SOUL.md` / instructions de l'agent |
| **Mission** | instructions / contexte de projet |
| **Goal** | instructions + mission donnée |
| **Context** | `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, fichiers référencés |
| **Knowledge** | fichiers de connaissance, contexte, skills ou source externe |
| **RAG** | à construire avec une source/retrieval adaptée ; ce n'est **pas** automatiquement « le RAG d'Hermes » |
| **Tools** | toolsets Hermes |
| **Tool spécifique** | toolset activé / MCP / skill selon le cas |
| **Permissions** | configuration / outils / environnement OS + approbations ; **pas** un simple champ `permissions:` universel |
| **Memory** | `~/.hermes/memories/`, `MEMORY.md`, `USER.md` |
| **Skills** | `~/.hermes/skills/` |
| **API keys** | `~/.hermes/.env` |
| **Configuration** | `~/.hermes/config.yaml` |
| **Logs** | `~/.hermes/logs/` |
| **Données de mission** | fichiers du projet / DB / API / sources |
| **Stop condition** | instruction / skill / workflow + logique de l'agent |
| **Validation** | instruction + outil / test + critères |
| **Evidence** | fichiers / logs / tests / traces |
| **Integration** | MCP / API / CLI / service externe |

## 2. Correspondance pour CE projet (la plateforme, pas Hermes)

Rappel de cadrage (SPEC §3, AGENTS.md) : **Hermes est l'environnement de construction, pas
l'interface étudiante** et pas le runtime de la plateforme. Les agents de la plateforme sont des
services Python + FastAPI dans `/root/memo-platform`. La colonne « Hermes » reste donc utilisée
pour ce qui relève réellement de Hermes (build, secrets, configuration de l'outil, skills,
mémoire, logs de build) ; le reste se matérialise dans le dépôt, **par agent**.

| Élément | Dans Hermes (build) | Dans le projet, par agent |
|---|---|---|
| Purpose / identité | `SOUL.md` global | `src/<agent>/` (en-tête de paquet) + 1ʳᵉ section du prompt système : rôle et interdits |
| Mission | instructions | `docs/spec-agent-XX-*.md` (SPEC reçue) + section « MISSION » du prompt |
| Goal | instructions + mission | critères de succès de la SPEC + grille de `status` du prompt |
| Context | `AGENTS.md` (cwd-only), docs référencés | `AGENTS.md`, `README.md`, `docs/*.md`, `config/settings-<agent>.yaml` |
| Knowledge | fichiers de connaissance, skills | `docs/` (SPEC, architecture) + `llm/prompts/*.md` + `sources/providers.yaml` |
| RAG | source/retrieval adaptée (pas celui d'Hermes) | étage déterministe `src/<agent>/sources/` : API officielles, cache SQLite, **aucune base vectorielle en V1** |
| Tools | toolsets Hermes | services du pipeline : API FastAPI, client LLM, étage sources, validations, vérificateur |
| Tool spécifique | toolset activé / MCP / skill | adaptateurs `sources/adapters/*.py` (un par fournisseur) ; pas d'MCP en V1 |
| Permissions | config/outils/OS + approbations | `core/limits.py` + `core/security_rules.py` + matrice READ/WRITE/DELETE/DEPLOY/SEND de la SPEC ; `delete/deploy/send = false` |
| Memory | `~/.hermes/memories/`, `MEMORY.md` | artefacts de session `workspace/<student_id>/<session_id>/*.json` + cache ; isolation par étudiant |
| Skills | `~/.hermes/skills/` | prompts réutilisables `src/<agent>/llm/prompts/*.md` (rôle, vérificateur) |
| API keys | `~/.hermes/.env` | lues via `core/config.py` (`api_key_env`), **jamais** dans le code, la config ou les logs |
| Configuration | `~/.hermes/config.yaml` | `config/settings-<agent>.yaml` (propre à l'agent : LLM, bornes, chemins, sources, sécurité) |
| Logs | `~/.hermes/logs/` | `core/logging.py` (filtré) + journal d'audit SQLite `workspace/audit-<agent>.db` |
| Données de mission | fichiers du projet / DB / API | entrées étudiantes, documents, `workspace/sources-cache.db` (réponses des fournisseurs) |
| Stop condition | instruction / skill / workflow | `core/limits.py` (bornes) + `core/errors.py` (8 états d'erreur) + garde anti-non-convergence |
| Validation | instruction + outil / test + critères | `pipeline/schema_validation.py` → `business_validation.py` → `security_validation.py` + `tests/` |
| Evidence | fichiers / logs / tests / traces | `tests/`, journal d'audit, sorties de session, `docs/architecture-*.md` (§ « État réel ») |
| Integration | MCP / API / CLI / service externe | `src/<agent>/api/routes.py` (HTTP) + `run-<agent>.sh` ; liaison inter-agents par payload vérifié, pas d'orchestrateur global (§44) |

## 3. Ce que « donner ses éléments à un agent » veut dire ici

Pour chaque nouvel agent, on crée et on renseigne **les 19 éléments** :

1. une fiche d'éléments remplie : `docs/elements-agent-0X-<nom>.md` ;
2. le document de référence reçu : `docs/spec-agent-0X-<nom>.md` ;
3. l'architecture 15 points validée : `docs/architecture-agent-0X-<nom>-v1.md` ;
4. le paquet autonome `src/<agent>/` (config propre, bornes, client LLM, prompts, pipeline,
   vérificateur, API, storage) — **sans modifier les agents existants** ;
5. la configuration propre `config/settings-<agent>.yaml` ;
6. les tests `tests/<agent>/` + le test réel sur modèle ;
7. les artefacts d'exécution isolés : `workspace/audit-<agent>.db` (+ cache propre si l'agent
   fait de la recherche) ;
8. le script de lancement `run-<agent>.sh` avec son port dédié ;
9. son **profil Hermes propre** `~/.hermes/profiles/<profil>/` : `SOUL.md` (identité),
   `.hermes.md` (contexte projet), `memories/MEMORY.md` + `memories/USER.md` (mémoire),
   `knowledge/README.md` (connaissance + retrieval), `skills/<profil>/SKILL.md` (méthode de
   l'agent). Créé par `scripts/nouveau-profil-agent.sh <profil> "<description>" <paquet>`, qui
   enregistre le profil (`hermes profile create` — obligatoire) et écrit le squelette à compléter.

Aucun élément n'est laissé implicite : un élément absent est écrit « à créer » dans la fiche,
avec la raison.

## 4. Les deux colonnes, concrètement

- **Profil Hermes** = le cadre de conception de l'agent : identité (`SOUL.md`), contexte
  (`.hermes.md`), mémoire (`memories/`), connaissance (`knowledge/`), méthode (`skills/`),
  configuration du profil (`config.yaml`, jamais édité à la main), secrets (`~/.hermes/.env`,
  hérités de l'environnement — jamais dupliqués), logs (`~/.hermes/logs/`).
- **Paquet Python** = le runtime que verra l'étudiant : `src/<agent>/`, `config/settings-<agent>.yaml`,
  `workspace/audit-<agent>.db`. Hermes n'est jamais visible de l'étudiant (SPEC §3).

Les deux colonnes sont créées ensemble, à chaque nouvel agent. Le profil ne modifie jamais le
dépôt ; le paquet ne dépend jamais du profil.
