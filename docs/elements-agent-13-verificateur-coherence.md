# Éléments de l'Agent 13 — Vérificateur global de cohérence (`research_coherence_verifier`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté et vérifié en exécution réelle** — voir la section « État réel » de
> `docs/architecture-agent-13-verificateur-coherence-v1.md`.
> Spécificité : cet agent **ne produit aucun contenu du mémoire**. Il audite la cohérence TRANSVERSALE
> du dossier complet (étapes 1 à 11) et déclare explicitement **ce qu'il ne peut pas vérifier**.

## Identité

| Champ | Valeur |
|---|---|
| Nom | Vérificateur global de cohérence |
| Technical ID | `research_coherence_verifier` |
| Version | `1.0` |
| Étape | 13 (l'étape 12 reste réservée, non attribuée) |
| Paquet | `src/research_coherence_verifier/` (autonome ; aucun agent existant modifié) |
| Port de service | 8130 (`run-coherence.sh`) |
| Profil Hermes | `agent-coherence` (`~/.hermes/profiles/agent-coherence/`) |
| Entrée | dossier COMPLET des étapes 1 à 11 |
| Contrôleur associé | `coherence_verifier` (contrôles C1–C13 : l'audit lui-même est contrôlé) |
| Successeur | Aucun (l'audit alimente l'étudiant et son directeur de mémoire) |

**Différence avec les autres agents.** Les agents 1 à 11 **produisent** une partie du mémoire ; celui-ci
**audite l'ensemble**. Chaque étape prise seule peut être irréprochable alors que l'enchaînement ne tient
pas : c'est exactement ce que cet agent recherche.

| | Agents 1 → 11 | Agent 13 |
|---|---|---|
| Objet | une partie du mémoire | l'ENCHAÎNEMENT des parties |
| Produit | contenu | constats hiérarchisés + recommandations + portée |
| Modifie le dossier | oui, son étape | **jamais** : il signale |

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-coherence/SOUL.md` | Rôle d'audit transversal, mission, interdits, chemins |
| Context | `.../agent-coherence/.hermes.md` | Règles projet, maillon couvert, entrée totale |
| Memory | `.../agent-coherence/memories/MEMORY.md` | Constats fondés seulement, portée déclarée, pièges X1–X12 |
| Knowledge | `.../agent-coherence/knowledge/README.md` | Types de ruptures, non-vérifiable, prompts |
| Skills | `.../agent-coherence/skills/agent-coherence/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-coherence/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (aucun réseau) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-coherence.db` (service) | Aucun contenu de dossier journalisé |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/research_coherence_verifier/__init__.py` + prompt `p1_audit_system.md` § rôle | CRÉÉ |
| Mission | `docs/spec-agent-13-verificateur-coherence.md` § 3 | Déposée |
| Goal | SPEC § 4 et § 13 + grille de verdicts du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-13-verificateur-coherence-v1.md`, `config/settings-coherence.yaml` | CRÉÉ |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-13-verificateur-coherence.md` | CRÉÉ |
| RAG | Aucune base vectorielle ; aucun accès réseau (le dossier suffit) | CRÉÉ |
| Tools | `pipeline/` (dossier, faits transversaux, audit, rapport, contrôle, orchestrateur) | CRÉÉ |
| Tool spécifique | `analysis/coherence_rules.py` (X1–X12), `analysis/fusion.py` (détection de fusion), `analysis/numeric_guard.py` | CRÉÉ |
| Permissions | `core/limits.py`, `core/security_rules.py` | CRÉÉ — READ dossier, WRITE rapport ; DELETE/DEPLOY non ; **aucune écriture dans les étapes** |
| Memory | `workspace/<student_id>/<session_id>/{coherence_request,coherence_audit,coherence_report}.json` | CRÉÉ |
| Skills | `llm/prompts/{p1_audit,p2_report,verifier}_system.md` | CRÉÉ |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-coherence.yaml` | CRÉÉ |
| Logs | `core/logging.py` + `workspace/audit-coherence.db` | CRÉÉ |
| Données de mission | dossier COMPLET étapes 1 à 11 + consignes éventuelles | CRÉÉ |
| Stop condition | `core/limits.py`, `core/errors.py`, `prerequisites.py` (moins de deux étapes exploitables ⇒ `needs_clarification`) | CRÉÉ |
| Validation | `schema_validation` → `business_validation` (T1–T6) → `coherence_checks` (X1–X12) → `security_validation` | CRÉÉ |
| Evidence | `tests/coherence/`, journal d'audit, section « État réel » de l'architecture | CRÉÉ |
| Integration | `api/routes.py` (`POST /coherence/audit`, `POST /coherence/{student}/{session}/decision`, `GET /coherence/{student}/{session}`, `GET /health`), `run-coherence.sh` | CRÉÉ |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | Dossier 1 → 11, lu sous sa forme RÉELLE ; `validation.verified` (étapes 1-4) et `verification_result.verified` (5-11) acceptés ; consignes = données non fiables |
| Audit | `schemas/audit.py` | `Finding` : code, axe, sévérité (bloqueur / majeur / mineur), éléments concernés, preuve, recommandation ; `ElementNonVerifiable` : ce qui n'a pas pu être examiné et pourquoi |
| Rapport | `schemas/report.py` | Synthèse, constats hiérarchisés, portée déclarée, recommandations, verdict |
| Décision étudiante | `schemas/decision.py` | `accepted` / `modified` / `refused` + commentaire |
| Sortie | `schemas/output.py` | Dossier de preuve SPEC §16 ; `status` ; `document_status` |
| Contrôleur | `schemas/verifier.py` | Verdict + contrôles C1–C13 |

## Bornes par défaut

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 200000 | dossier COMPLET des onze étapes |
| `max_output_tokens` | 32000 | modèle raisonneur |
| `timeout` | 120 s | audit d'un dossier volumineux |
| `max_llm_calls` | 14 | P1 (audit transversal) + P2 (rapport) + contrôleur + re-tentatives |
| `max_agent_turns` | 8 | |
| `max_external_requests` | 0 | aucun réseau |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais inventer un constat : sans preuve dans le dossier, il n'existe pas.
- Ne jamais modifier une étape du dossier (ni la corriger, ni la réécrire).
- Ne jamais juger hors compétence : style, orthographe, plagiat, éthique de terrain, règles locales non
  fournies ⇒ déclarés **non vérifiables**.
- Ne jamais omettre la déclaration de portée dans le rapport.
- Ne jamais confondre rupture démontrable, fragilité et élément non vérifié.
- Ne jamais recopier de données personnelles dans le rapport.
- Ne jamais s'auto-attribuer « contrôlé » ou « validé ».

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/coherence/` (règles X1–X12 éprouvées dans les deux sens, audit complet, portillon, sécurité, API, dossier réel) |
| Contrôles déterministes seuls | fusion sujet=problème=problématique détectée ; objectif sans résultat détecté ; référence orpheline de la conclusion détectée ; statut d'hypothèse contradictoire détecté |
| Test réel complet | `scripts/e2e_chaine.py depuis=11` puis audit du dossier complet |
| Traces | `workspace/audit-coherence.db`, artefacts par session |
