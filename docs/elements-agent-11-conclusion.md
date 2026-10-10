# Éléments de l'Agent Conclusion (`research_conclusion_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté et vérifié en exécution réelle** — voir la section « État réel » de
> `docs/architecture-agent-11-conclusion-v1.md`. Dernier agent du parcours (étape 11).

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Conclusion |
| Technical ID | `research_conclusion_agent` |
| Version | `1.0` |
| Étape du parcours | 11 — Conclusion (dernière) |
| Paquet | `src/research_conclusion_agent/` (autonome ; aucun agent existant modifié) |
| Port de service | 8110 (`run-conclusion.sh`) |
| Profil Hermes | `agent-conclusion` (`~/.hermes/profiles/agent-conclusion/`) |
| Prédécesseur | Agent 10 — Résultats et analyse (`research_results_analysis_agent`, port 8100) |
| Vérificateur associé | `conclusion_verifier` (contrôles C1–C13) |
| Successeur | Aucun (fin du parcours) |

**Frontière avec l'agent 10.**

| | Agent 10 — Résultats et analyse | Agent 11 — Conclusion |
|---|---|---|
| Question posée | *Que disent les données recueillies ?* | *Qu'en retenir, et que peut-on en conclure ?* |
| Produit | Résultats calculés, interprétations, limites, synthèse | Réponse à la question, bilan objectifs/hypothèses, apports, limites, perspectives |
| Nature | CONSTAT par objectif | SYNTHÈSE générale, en citant les résultats par identifiant |
| Interdit de l'autre | Ne jamais rédiger la conclusion | **Ne jamais produire de résultat nouveau** |

**Le principe qui gouverne cet agent : aucun résultat nouveau.** Toute affirmation centrale cite le
résultat de l'étape 10 qui la justifie (contrôle K1) et aucun chiffre ne peut sortir des valeurs
réellement calculées (contrôle K2). Sans résultats vérifiés, la production se limite à un plan (K8).

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-conclusion/SOUL.md` | Rôle étape 11, mission, frontière avec l'étape 10, interdits, chemins |
| Context | `.../agent-conclusion/.hermes.md` | Règles projet, maillon couvert, liaisons amont |
| Memory | `.../agent-conclusion/memories/MEMORY.md` | Aucun résultat nouveau, traçabilité, pièges K1–K9 |
| Knowledge | `.../agent-conclusion/knowledge/README.md` | Traçabilité, liste blanche numérique, prompts |
| Skills | `.../agent-conclusion/skills/agent-conclusion/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-conclusion/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (aucun réseau) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-conclusion.db` (service) | Aucun contenu de conclusion journalisé |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/research_conclusion_agent/__init__.py` + prompt `p1_synthesis_system.md` § rôle | CRÉÉ |
| Mission | `docs/spec-agent-11-conclusion.md` § 3 | Déposée |
| Goal | SPEC § 4 et § 13 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-11-conclusion-v1.md`, `config/settings-conclusion.yaml` | CRÉÉ |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-11-conclusion.md` | CRÉÉ |
| RAG | Aucune base vectorielle ; aucun accès réseau | CRÉÉ |
| Tools | `pipeline/` (entrée, P1–P3, contrôles K1–K9, validations T1–T6, vérificateur, orchestrateur) | CRÉÉ |
| Tool spécifique | `analysis/conclusion_rules.py` (K1–K9), `analysis/numeric_guard.py` (liste blanche, K2) | CRÉÉ |
| Permissions | `core/limits.py`, `core/security_rules.py` | CRÉÉ — READ dossier + amont vérifié, WRITE workspace, DELETE/DEPLOY non, SEND vérificateur seulement |
| Memory | `workspace/<student_id>/<session_id>/{conclusion_request,conclusion_draft,conclusion_output}.json` | CRÉÉ |
| Skills | `llm/prompts/{p1_synthesis,p2_plan,p3_writing,verifier}_system.md` | CRÉÉ |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-conclusion.yaml` | CRÉÉ |
| Logs | `core/logging.py` + `workspace/audit-conclusion.db` | CRÉÉ |
| Données de mission | dossier complet des étapes 1 à 10 + résultats VÉRIFIÉS de l'étape 10 + consignes | CRÉÉ |
| Stop condition | `core/limits.py`, `core/errors.py`, garde anti-non-convergence, STOP CONDITIONS SPEC §14 (résultats absents ⇒ plan seulement) | CRÉÉ |
| Validation | `schema_validation` → `business_validation` (T1–T6) → `conclusion_checks` (K1–K9) → `security_validation` | CRÉÉ |
| Evidence | `tests/conclusion/`, journal d'audit, section « État réel » de l'architecture | CRÉÉ |
| Integration | `api/routes.py` (`POST /conclusion/write`, `POST /conclusion/{student}/{session}/decision`, `GET /conclusion/{student}/{session}`, `GET /health`), `run-conclusion.sh` | CRÉÉ |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_*` accepté seulement si vérifié — **`validation.verified` (1-4) ET `verification_result.verified` (5-10)** ; **résultats de l'étape 10 requis et validés** ; consignes = données non fiables |
| Synthèse | `schemas/synthesis.py` | Réponse à la question (étayage + portée), bilan des objectifs (4 statuts), bilan des hypothèses (statut REPRIS de l'étape 10), incohérences |
| Plan | `schemas/plan.py` | `fonction` de chaque rubrique obligatoire ; rubriques écartées justifiées ; adaptation aux consignes |
| Rédaction | `schemas/draft.py` | `niveau` (constat / interprétation / perspective), `justification` obligatoire, `resultats` (identifiants cités) |
| Décision étudiante | `schemas/decision.py` | `accepted` / `modified` / `refused` + commentaire |
| Sortie | `schemas/output.py` | Dossier de preuve SPEC §16 ; `status` ; `document_status` (brouillon, à corriger, vérifié, en attente de validation, validé, à réviser) |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles C1–C13 |

## Bornes par défaut

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 80000 | dossier complet + résultats de l'étape 10 |
| `max_output_tokens` | 32000 | modèle raisonneur |
| `timeout` | 90 s | |
| `max_llm_calls` | 20 | P1 + P2 + P3 + vérificateur + re-tentatives + reformulations |
| `max_agent_turns` | 8 | |
| `max_external_requests` | 0 | aucun réseau |
| `max_verification_retries` | 3 | |

## Interdictions propres à l'étape

- Ne jamais fabriquer de résultats, de données, de citations, d'entretiens ou de conclusions (§10.1).
- Ne jamais introduire un résultat nouveau dans la conclusion (§10.8).
- Ne jamais présenter une association comme une causalité ni généraliser au-delà des données (§10.4).
- Ne jamais imposer d'hypothèses ni en exiger quand il n'y en a pas (§10.5).
- Ne jamais contredire le statut d'une hypothèse établi à l'étape 10 (K3).
- Ne jamais présenter une hypothèse comme « confirmée » ou « démontrée » (K5).
- Ne jamais inventer de référence bibliographique (§10.9, K6).
- Ne jamais reproduire de données personnelles ou confidentielles (§10.11, T4).
- Ne jamais présenter une consigne d'établissement inventée (aucune consigne fournie ⇒ usage courant).
- Ne jamais s'auto-attribuer `verified` ni `validated` (§10.13).

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/conclusion/` (règles K1–K9, campagne avec et sans résultats, décision, sécurité, API, chaîne amont) |
| Contrôles déterministes seuls | chiffre inventé refusé (K2), affirmation non traçable refusée (K1), statut d'hypothèse contredisant l'étape 10 refusé (K3), causalité écartée ≠ affirmée (K4), hypothèse « confirmée » refusée (K5), référence absente refusée (K6), conclusion sans résultats refusée (K8) |
| Test réel complet | `scripts/e2e_chaine.py depuis=11` (modèle réel, réseau désactivé) |
| Traces | `workspace/audit-conclusion.db`, artefacts par session |
