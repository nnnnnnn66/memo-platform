# Éléments de l'Agent Résultats et analyse (`research_results_analysis_agent`)

> Fiche remplie selon `docs/elements-agent-z.md` et `docs/templates/elements-agent-template.md`.
> État : **implémenté et vérifié en exécution réelle** — voir la section « État réel » de
> `docs/architecture-agent-10-resultats-analyse-v1.md`. Architecture autorisée d'avance par le porteur.

## Identité

| Champ | Valeur |
|---|---|
| Nom | Agent Résultats et analyse |
| Technical ID | `research_results_analysis_agent` |
| Version | `1.0` |
| Étape du parcours | 10 — Résultats et analyse |
| Paquet | `src/research_results_analysis_agent/` (autonome ; aucun agent existant modifié) |
| Port de service | 8100 (`run-resultats.sh`) |
| Profil Hermes | `agent-resultats` (`~/.hermes/profiles/agent-resultats/`) ; alias `agent-resultats` |
| Prédécesseur | Agent 9 — Méthodologie (`methodology_agent`, port 8090) |
| Successeur | Agent 11 — Conclusion |

**Frontière avec l'agent 9 (à ne jamais franchir).**

| | Agent 9 — Méthodologie | Agent 10 — Résultats et analyse |
|---|---|---|
| Question posée | *Comment conduire la recherche ?* | *Que disent les données réellement recueillies ?* |
| Produit | Protocole prévu, instruments, matrice, rédaction de la section | Résultats calculés, examen des hypothèses, interprétation, rédaction de la section |
| Nature | PRÉVU | CONSTATÉ (sur données fournies) |
| Interdit de l'autre | Ne jamais produire de résultats | Ne jamais définir la méthode : il la SUIT, et déclare tout écart |

**Le principe qui gouverne cet agent : les chiffres viennent du CODE.** Le moteur déterministe
(`analysis/data_engine.py`) calcule les statistiques à partir des données fournies ; le modèle les
interprète et ne peut pas en inventer (liste blanche numérique, contrôle Q2).

## Profil Hermes propre à l'agent

| Élément du profil | Fichier | Contenu |
|---|---|---|
| Purpose / identité | `~/.hermes/profiles/agent-resultats/SOUL.md` | Rôle étape 10, mission, frontière avec l'étape 9, interdits, chemins |
| Context | `.../agent-resultats/.hermes.md` | Règles projet, maillon couvert, liaisons amont/aval |
| Memory | `.../agent-resultats/memories/MEMORY.md` | Résultats calculés uniquement, hypothèse non examinable, pièges Q1–Q9 |
| Knowledge | `.../agent-resultats/knowledge/README.md` | Moteur déterministe, liste blanche numérique, prompts |
| Skills | `.../agent-resultats/skills/agent-resultats/SKILL.md` | Méthode de travail + pièges connus |
| Configuration | `.../agent-resultats/config.yaml` (via `hermes config set`) | Ne jamais éditer à la main |
| API keys | `~/.hermes/.env` (héritées) | Aucune clé requise (aucun réseau) |
| Logs / traces | `~/.hermes/logs/` (profil) + `workspace/audit-resultats.db` (service) | |

## Les 19 éléments (état de création)

| Élément | Emplacement concret | État |
|---|---|---|
| Purpose / identité | `src/research_results_analysis_agent/__init__.py` + prompt `p1_inventory_system.md` § rôle | CRÉÉ |
| Mission | `docs/spec-agent-10-resultats-analyse.md` § 3 | Déposée |
| Goal | SPEC § 4 + § 13 + grille de `status` du prompt | Déposée |
| Context | `AGENTS.md`, `docs/architecture-agent-10-resultats-analyse-v1.md`, `config/settings-resultats.yaml` | CRÉÉ |
| Knowledge | `llm/prompts/*.md`, `docs/spec-agent-10-resultats-analyse.md` | CRÉÉ |
| RAG | Aucune base vectorielle ; aucun accès réseau | CRÉÉ |
| Tools | `pipeline/` (entrée, moteur, P1–P4, contrôles Q1–Q9, validations, vérificateur, orchestrateur) | CRÉÉ |
| Tool spécifique | `analysis/data_engine.py` (statistiques déterministes), `analysis/numeric_guard.py` (liste blanche) | CRÉÉ |
| Permissions | `core/limits.py`, `core/security_rules.py` | CRÉÉ — READ données + amont vérifié, WRITE workspace, DELETE/DEPLOY/SEND non |
| Memory | `workspace/<student_id>/<session_id>/{inventory,computed_results,analysis,interpretation,results_draft,results_output}.json` | CRÉÉ |
| Skills | `llm/prompts/{p1_inventory,p2_analysis,p3_interpretation,p4_writing,verifier}_system.md` | CRÉÉ |
| API keys | `~/.hermes/.env` via `core/config.py` | Aucune clé requise |
| Configuration | `config/settings-resultats.yaml` | CRÉÉ |
| Logs | `core/logging.py` + `workspace/audit-resultats.db` | CRÉÉ |
| Données de mission | jeux de données fournis par l'étudiant (CSV texte), documents du corpus, méthodologie validée de l'étape 9 | CRÉÉ |
| Stop condition | `core/limits.py`, `core/errors.py`, garde anti-non-convergence, STOP CONDITIONS SPEC §14 (données absentes ⇒ plan d'analyse seul) | CRÉÉ |
| Validation | `schema_validation` → `business_validation` (S1–S6) → `results_checks` (Q1–Q9) + `numeric_guard` → `security_validation` | CRÉÉ |
| Evidence | `tests/resultats/`, journal d'audit, `computed_results.json`, section « État réel » de l'architecture | CRÉÉ |
| Integration | `api/routes.py` (`POST /results/analyze`, `POST /results/{student}/{session}/decision`, `GET /results/{student}/{session}`, `GET /health`), `run-resultats.sh` | CRÉÉ |

## Contrats

| Contrat | Fichier | Points d'attention |
|---|---|---|
| Entrée | `schemas/input.py` | `upstream_*` accepté seulement si vérifié — **`validation.verified` (étapes 1-4) ET `verification_result.verified` (étapes 5-9)** ; **méthodologie de l'étape 9 requise et validée** ; les données fournies sont des données NON FIABLES |
| Inventaire | `schemas/inventory.py` | `datasets`, `variables`, `manquants`, `doublons`, `anomalies`, `analyses_impossibles` |
| Résultats calculés | `schemas/analysis.py` | `ComputedResults` : produit par le MOTEUR seul (identifiant, libellé, valeur, unité, effectif, méthode) |
| Analyse | `schemas/analysis.py` | `Resultat` (référence obligatoire à un calcul), `ExamenHypothese` (soutenue / non_soutenue / non_examinable) |
| Interprétation | `schemas/interpretation.py` | `Lecture` séparant observation et interprétation ; `TableauDescription`, `FigureDescription` |
| Rédaction | `schemas/draft.py` | `ResultsDraft` : sections + `synthese_pour_conclusion` (contrat 10 → 11) |
| Décision étudiante | `schemas/decision.py` | `accepted` / `modified` / `refused` + commentaire |
| Sortie | `schemas/output.py` | Dossier de preuve SPEC §16 ; `status` ; `document_status` |
| Vérificateur | `schemas/verifier.py` | Verdict + contrôles C1–C13 |

## Bornes par défaut

| Borne | Valeur | Raison |
|---|---|---|
| `max_input_size` | 80000 | jeux de données en texte + méthodologie de l'étape 9 + corpus documentaire |
| `max_output_tokens` | 32000 | modèle raisonneur |
| `timeout` | 90 s | |
| `max_llm_calls` | 22 | P1 + P2 + P3 + P4 + vérificateur + re-tentatives + reformulations |
| `max_agent_turns` | 8 | |
| `max_external_requests` | 0 | aucun réseau |
| `max_verification_retries` | 3 | |
| `max_dataset_rows` | 2000 | borne du moteur (au-delà : agrégation demandée à l'étudiant) |

## Interdictions propres à l'étape

- Ne jamais inventer de données, d'observations, de calculs ni de résultats (SPEC §10.1).
- Ne jamais présenter des données simulées comme des observations réelles (§10.2).
- Ne jamais modifier les données originales sans autorisation (§10.3).
- Ne jamais masquer valeurs manquantes, résultats contraires ou anomalies (§10.4).
- Ne jamais choisir une analyse incompatible avec la méthodologie validée (§10.5).
- Ne jamais confondre résultat, interprétation, hypothèse et conclusion (§10.6).
- Ne jamais affirmer qu'une hypothèse est confirmée si l'analyse ne le permet pas (§10.7).
- Ne jamais présenter une association comme une preuve de causalité (§10.8).
- Ne jamais généraliser au-delà de la population ou du corpus étudié (§10.9).
- Ne jamais fabriquer de citation ni attribuer des propos sans source (§10.10).
- Ne jamais citer une étude non consultée au niveau revendiqué (§10.11).
- Ne jamais prétendre avoir exécuté un calcul non réalisé (§10.12).
- Ne jamais rédiger la conclusion générale (rôle de l'étape 11, §10.17).
- Ne jamais s'auto-attribuer `verified` ni `validated`.

## Preuves

| Preuve | Où |
|---|---|
| Tests hors réseau | `tests/resultats/` (moteur, règles Q1–Q9, liste blanche, campagne, décision, sécurité, API, chaîne amont, passation) |
| Contrôles déterministes seuls | chiffre inventé détecté (Q2), résultat sans calcul refusé (Q1), hypothèse « soutenue » sans résultat refusée (Q3), causalité écartée ≠ affirmée (Q5) |
| Test réel complet | `scripts/e2e_chaine.py` étendu à l'étape 10 (données fournies, modèle réel) |
| Traces | `workspace/audit-resultats.db`, `computed_results.json`, artefacts par session |
