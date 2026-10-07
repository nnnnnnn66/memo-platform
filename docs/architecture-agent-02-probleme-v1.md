# Architecture V1 — Agent Problème de recherche (`research_problem_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points).
> **Statut : VALIDÉE par le porteur de projet puis IMPLÉMENTÉE.** Voir en fin de document la
> section « État réel de l'implémentation » (ce qui a été construit et ce que le test réel a
> imposé de corriger).
> Référentiel : SPEC — AGENT PROBLÈME DE RECHERCHE (§1–16) → `docs/spec-agent-02-probleme.md`.
> S'appuie sur l'héritage méthodologique de l'Agent Sujet V1 (`docs/architecture-v1.md`), déjà
> implémenté et testé — mais **sans mutualisation de code** (voir décision arbitrée ci-dessous).

## 0. Arbitrages déjà rendus par le porteur de projet

1. **Cadre propre à chaque agent.** L'Agent Problème possède son propre paquet autonome
   (`src/research_problem_agent/`), sa propre configuration, ses propres bornes, ses propres
   prompts, son propre vérificateur. **Aucun paquet partagé `src/common/`** : les garde-fous
   communs sont **dupliqués** dans le paquet de l'agent. L'Agent Sujet n'est **pas** modifié.
   Conséquence assumée : duplication contrôlée, deux agents indépendants, aucun couplage.
2. **Tout fournisseur utile à l'objectif.** L'agent utilise **tous les fournisseurs gratuits et
   sans clé** qui lui permettent d'atteindre son objectif (étayer le problème de recherche), et
   non un sous-ensemble restrictif. La liste est **déclarée en configuration** : ajouter un
   fournisseur gratuit ne demande aucune modification du pipeline. La liste blanche d'hôtes reste
   obligatoire (anti-SSRF), mais elle est **extensible par configuration**, pas figée dans le code.

---

## 1. Architecture

Même principe que l'Agent Sujet — **pipeline linéaire de garde-fous, rien ne court-circuite une
étape, aucune sortie LLM utilisée telle quelle** — auquel s'ajoute, exigence propre à cet agent,
un **étage de recherche documentaire déterministe** (SPEC §7, §8, §9.3, §16.C).

```
ÉTUDIANT (sujet + contexte)
   │
   ▼
[1] Input Controller        ── requête HTTP, student_id/session_id, snapshot du sujet amont
[2] Input Validation        ── contrat d'entrée (§6), tailles, champs obligatoires
[3] Security Layer          ── injection/secrets/instructions cachées (§10, §11, §13)
   │
   ▼
[4] Agent (LLM) — PHASE 1  ── analyse du sujet : phénomène, population, contexte, espace,
   │                            période, concepts + `search_intents` (requêtes bornées)
[5] Output Parser → [6] Schema Validation → [7] Business Validation
   │                            (anti-fusion, fidélité, requêtes non vides et bornées)
   ▼
[8] Source Retrieval (OUTIL DÉTERMINISTE, sans LLM)   ← NOUVEAU
   │   OpenAlex / Crossref / DOAJ / HAL / arXiv / DataCite (+ World Bank pour les données
   │   publiques). Aucune clé, aucun coût. Résultat = `SourceSet` à identifiants stables.
   │   Les métadonnées récupérées sont balisées comme DONNÉES NON FIABLES.
   ▼
[9] Agent (LLM) — PHASE 2  ── formulation du problème à partir des sources fournies ;
   │                            chaque affirmation externe doit pointer un `source_id` du SourceSet
[10] Output Parser → [11] Schema Validation → [12] Business Validation → [13] Security Validation
   │   (contrôle anti-hallucination : tout `source_id`/URL d'`evidence` doit exister dans le
   │    SourceSet — un faux lien est structurellement impossible à faire passer)
   ▼
[14] Verifier (LLM indépendant) ── sortie elle-même retraitée par [10]→[13]
   │
   ▼
[15] Validated Problem      ── statut `verified` posé UNIQUEMENT par le vérificateur
```

Principes non négociables :
- **Moindre privilège** : `read: session_only` (+ documents autorisés), `write: workspace_only`,
  `delete/deploy/send: false`.
- **Séparation stricte** : sujet, contexte, réponses et **contenus récupérés sur le web** sont des
  **données non fiables**, jamais des instructions (nouvelle surface d'attaque : LLM01/LLM04).
- **Recherche déterministe** : la liste des sources ne provient jamais du LLM ; le LLM ne fait que
  formuler ; il ne peut citer que ce qui a été réellement récupéré.
- **Autonomie de l'agent** : cadre, config, bornes, prompts et vérificateur propres à cet agent ;
  aucune dépendance de code vers un autre agent.
- **Double validation** : vérificateur indépendant, l'agent ne s'auto-attribue jamais `verified`.
- **0 €** : uniquement des API publiques sans clé + le LLM déjà configuré.

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings.yaml                     # + section `sources:` (endpoints, bornes, cache)
├── docs/
│   ├── architecture-agent-02-probleme-v1.md   # ce document
│   └── spec-agent-02-probleme.md              # SPEC fournie (à déposer pour référence)
├── src/
│   ├── subject_agent/                    # Agent Sujet V1 — NON MODIFIÉ
│   └── research_problem_agent/           # paquet AUTONOME (cadre propre à l'agent)
│       ├── main.py                       # app FastAPI
│       ├── api/routes.py                 # POST /problem/analyze, GET /problem/{session_id}, /health
│       ├── pipeline/
│       │   ├── input_controller.py
│       │   ├── input_validation.py
│       │   ├── security_layer.py          # entrées étudiant + contenus récupérés
│       │   ├── problem_agent.py           # appels LLM phase 1 et phase 2
│       │   ├── output_parser.py
│       │   ├── schema_validation.py
│       │   ├── business_validation.py     # anti-fusion, anti-hallucination, fidélité
│       │   ├── security_validation.py
│       │   └── problem_verifier.py
│       ├── llm/
│       │   ├── client.py                  # client LLM propre à l'agent
│       │   └── prompts/
│       │       ├── problem_phase1_system.md   # analyse + search_intents
│       │       ├── problem_phase2_system.md   # formulation ancrée sur le SourceSet
│       │       └── verifier_system.md
│       ├── sources/                       # ÉTAGE DE RECHERCHE — NOUVEAU, sans LLM
│       │   ├── providers.yaml             # fournisseurs + hôtes autorisés (extensible)
│       │   ├── registry.py                # charge providers.yaml, sélectionne par objectif
│       │   ├── http.py                    # client httpx borné (timeout, retries, taille max)
│       │   ├── adapters/openalex.py crossref.py doaj.py hal.py arxiv.py datacite.py
│       │   │            worldbank.py europepmc.py pubmed.py openaire.py zenodo.py
│       │   │            scielo.py eurostat.py datagouv.py                  # + ajouts par config
│       │   ├── source_set.py              # SourceRecord + SourceSet (ids stables, dédoublonnage)
│       │   └── cache.py                   # cache SQLite des requêtes (anti-abus, reproductibilité)
│       ├── schemas/input.py output.py verifier.py search_intent.py
│       ├── core/config.py limits.py errors.py logging.py sessions.py security_rules.py
│       └── storage/workspace.py audit.py
└── tests/
    ├── functional/test_15..test_21_*.py
    ├── security/test_22..test_30_*.py
    └── sources/test_*.py                  # adaptateurs hors réseau (fixtures enregistrées)
```

---

## 3. Rôle de chaque fichier (éléments nouveaux uniquement)

| Fichier | Rôle |
|---|---|
| `research_problem_agent/` | Paquet **autonome** : config, bornes, prompts, vérificateur, sécurité. Aucune dépendance vers l'Agent Sujet. |
| `sources/providers.yaml` | **Fournisseurs déclarés en configuration** : hôte autorisé, type §7, famille (publications, données publiques, dépôts, statistiques), langues, activation. Ajouter un fournisseur gratuit = éditer ce fichier, pas le code. |
| `sources/registry.py` | Charge `providers.yaml`, sélectionne les fournisseurs pertinents selon l'objectif de la requête. **Aucune URL arbitraire** n'est jamais appelée : seuls les hôtes déclarés (anti-SSRF, anti-exfiltration). |
| `sources/http.py` | Client httpx borné : timeout, retries, User-Agent identifiable, taille de réponse plafonnée, une seule famille d'hôtes. |
| `sources/adapters/*.py` | Traduction requête normalisée → API du fournisseur → `SourceRecord` normalisé. Aucun LLM. |
| `sources/source_set.py` | `SourceRecord` + `SourceSet` : identifiants stables (`S1`, `S2`…), URL canonique, type de source §7, dédoublonnage par DOI/URL, marquage `retrieved`/`not_verified`. |
| `sources/cache.py` | Cache SQLite des réponses (durée de vie configurable) : reproductibilité, respect des quotas, tests hors réseau. |
| `pipeline/problem_agent.py` | Deux appels LLM : phase 1 (analyse + requêtes), phase 2 (formulation ancrée). Le LLM ne déclenche jamais lui-même une requête réseau. |
| `pipeline/business_validation.py` | Anti-fusion (pas de problématique / question de recherche / hypothèse / plan), fidélité au sujet, **ancrage strict des sources** : tout `source_id` doit exister dans le `SourceSet`, URL identique. |
| `schemas/search_intent.py` | Contrat des `search_intents` (requête, intention, langue, nombre de résultats demandés ≤ borne). |

---

## 4. Flux des données

```
POST /problem/analyze
  body: { student_id, session_id?, subject_text, subject_context?, upstream_subject?,
          discipline?, academic_level?, country?, institution?, observations?,
          previous_answers[], additional_constraints? }
   │
   ├─ Input Controller ─► session (student_id, session_id) + snapshot sujet
   ├─ Input Validation ─► conforme ? sinon 422 INVALID_INPUT
   ├─ Security Layer ──► sujets/contexte/documents balisés NON FIABLES (+ annotations)
   │
   ├─ LLM PHASE 1 ─────► { analyse préliminaire, search_intents[≤ MAX_SEARCH_QUERIES] }
   ├─ Parser → Schéma → Métier (requêtes bornées, non vides, anti-fusion)
   │
   ├─ Source Retrieval ► pour chaque requête : ≥1 fournisseur, ≤ MAX_SOURCES_PER_QUERY,
   │                      ≤ MAX_EXTERNAL_REQUESTS appels réseau, timeout par appel,
   │                      cache, dédoublonnage → SourceSet (S1..Sn)
   │                      Si aucun résultat → on continue SANS source (jamais d'invention),
   │                      lacune déclarée + `MISSING_INFORMATION` / questions à l'étudiant
   │
   ├─ LLM PHASE 2 ─────► sortie §16 (A–H) ancrée : chaque élément externe cite un source_id
   ├─ Parser → Schéma → Métier → Sécurité
   │       contrôle d'ancrage : source_id ∈ SourceSet ET url identique, sinon rejet (1 retry LLM)
   │
   ├─ Statut provisoire : needs_clarification | ready_for_verification | blocked
   │       needs_clarification → questions_for_student + FIN
   │
   ├─ Verifier (LLM indépendant) → verified | corrections_requested | rejected
   │       corrections_requested → re-boucle phases 2 (+ sources déjà en cache) ≤ MAX_VERIFICATION_RETRIES
   │       rejected → blocked + retour guidé à l'étudiant
   │
   └─ Workspace (sortie + SourceSet) + Audit SQLite + réponse HTTP
```

Les documents fournis par l'étudiant (SPEC §8, §9.4) suivent le même chemin que les sources :
lus depuis l'espace de la session, taille plafonnée, balisés non fiables, jamais exécutés.

---

## 5. Modèle de données

```
ProblemRequest      # voir §6
ProblemOutput       # voir §7 — cœur du contrat
SourceRecord        # NOUVEAU
  source_id         str            # S1, S2… (stable dans la session)
  provider          enum(openalex|crossref|doaj|hal|arxiv|datacite|worldbank|student_document)
  source              str          # éditeur / revue / organisme
  title             str
  url               str            # canonique, issue de l'API (jamais construite par le LLM)
  doi               str | null
  publication_date  str | null
  access_date       date
  source_type       enum(institutional|scientific|university|international_org|governmental|
                         professional|secondary|student_document)   # ordre de priorité §7
  snippet           str            # extrait réellement récupéré (plafonné), balisé non fiable
  retrieved         bool           # métadonnée effectivement obtenue de l'API
  verification_status enum(verified|not_verified)  # verified = fiche réelle et accessible
SourceSet
  session_id, query_intents[], records[], providers_failed[], retrieved_at
SearchIntent
  query, purpose, language, desired_results(≤ borne)
ProblemOutput
  … (voir §7)
VerifierOutput
  verdict enum(verified|corrections_requested|rejected)
  controls[{code, resultat, detail}]  corrections[]  flags[]
AuditLog
  session_id, agent_id, timestamp, version, status, errors[], validation_result,
  attempts, verifications, external_requests, providers_used[], cache_hits, source_ids[]
```

Enums : `STATUS = needs_clarification | ready_for_verification | blocked | verified` ;
`SOURCE_DISTINCTION = fact | interpretation | unknown` (SPEC §6, §16) ;
`ERROR_STATE = INVALID_INPUT | MISSING_INFORMATION | OUTPUT_SCHEMA_ERROR | SECURITY_VIOLATION |
TOOL_ERROR | TIMEOUT | RESOURCE_LIMIT | VERIFICATION_FAILED`.

**Stockage V1** : artefacts JSON par session (`workspace/<student>/<session>/`) + audit SQLite
stdlib + cache SQLite des sources. **Pas de base vectorielle**, pas d'embeddings (cohérent V1).

---

## 6. Contrat d'entrée

| Champ | Type | Obligatoire | Contrainte |
|---|---|---|---|
| `student_id` | str | oui | opaque, jamais loggé en clair |
| `session_id` | str(uuid) | non | créé si absent |
| `subject_text` | str | **oui** | non vide, ≤ `MAX_INPUT_SIZE` |
| `subject_context` | str | non | ≤ `MAX_INPUT_SIZE` |
| `upstream_subject` | objet | non | sortie de l'Agent Sujet **cochée `verified`** ; consommée telle quelle ou refusée si non vérifiée |
| `observations` | str | non | faits rapportés par l'étudiant (traités comme déclaratifs, non vérifiés) |
| `student_documents` | list | non | documents de la session uniquement, tailles plafonnées |
| `discipline`, `academic_level`, `country`, `institution` | str | non | contexte §6 |
| `previous_answers` | list[str] | non | réponses aux questions précédentes |
| `additional_constraints` | str | non | |

**Provenance obligatoire** pour chaque information retenue : `fourni` | `déduit` | `inconnu`
(SPEC §6). Une information `inconnu` ne devient jamais un fait ; une déclaration de l'étudiant
n'est jamais promue « fait vérifié » sans source externe récupérée.

---

## 7. Contrat de sortie (SPEC §16 : preuves A–H)

```json
{
  "agent": "research_problem_agent",
  "version": "1.0",
  "status": "needs_clarification | ready_for_verification | blocked",
  "subject_reference": { "original": "", "reformulated": "" },
  "identified_problem": {                       // A
    "statement": "",                            //   problème, distinct du sujet
    "situation": "",                            //   situation problématique
    "why_problematic": "",
    "actors_concerned": [],
    "consequences": [],
    "stakes": []
  },
  "justifying_elements": [                      // B
    { "element": "", "source_id": "S1 | null", "provenance": "fourni|déduit|inconnu",
      "nature": "fact | interpretation | unknown" }
  ],
  "sources": [                                  // C
    { "source_id": "S1", "source": "", "title": "", "url": "", "doi": "",
      "publication_date": "", "access_date": "", "information_used": "",
      "source_type": "scientific", "confidence": 0.0,
      "verification_status": "verified | not_verified" }
  ],
  "unknown_information": [],                    // D
  "gaps": [],                                   // E
  "remaining_questions": [],                     // F (questions à l'étudiant)
  "provisional_formulation": "",                 // G (provisoire, fidèle, transparente)
  "delimitation": { "population": "", "geographical_scope": "", "temporal_scope": "",
                    "context": "" },
  "search_queries_used": [],
  "confidence": { "overall": 0.0, "rationale": "" },   // H
  "validation": { "verified": false, "verifier_status": "pending" }
}
```

Règles structurelles :
- `subject_reference.original` = copie **exacte** du sujet reçu (non modifiable par le LLM).
- **Aucun champ** de type problématique complète, question de recherche, hypothèse, plan ou
  rédaction de mémoire (SPEC §10 contraintes 14–16) : ces clés n'existent pas dans le schéma ;
  leur apparition déclenche un rejet métier.
- Tout `source_id` non nul d'`evidence`/`sources` doit exister dans le `SourceSet` de la session,
  avec URL identique → **un lien fabriqué ne peut pas franchir la validation**.
- `validation.verified = true` uniquement sur verdict du vérificateur.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mesure V1 |
|---|---|
| LLM01 Injection (entrées **et contenus web récupérés**) | Tout est balisé données non fiables ; `security_layer` scanne les entrées étudiant **et** les titres/résumés récupérés avant de les remettre au LLM ; les instructions du prompt système priment sur tout contenu (§10) |
| LLM02 Fuite d'information | Aucun secret en contexte ; `security_validation` filtre la sortie ; logs filtrés |
| LLM03 Supply chain | Dépendances figées ; fournisseurs déclarés en **configuration** (`providers.yaml`) ; aucun paquet ajouté depuis une source non vérifiée ; aucune installation automatique |
| LLM04 Poisoning | Sources traitées comme données, sans effet sur prompt/permissions ; pas d'écriture dans la config depuis un contenu récupéré |
| LLM05 Traitement de sortie | Sortie jamais exécutée : Parser→Schéma→Métier→Sécurité avant tout usage, y compris pour le vérificateur |
| LLM06 Agence excessive | Permissions minimales ; **le LLM ne déclenche jamais lui-même de requête réseau** : il propose des requêtes, l'outil les exécute sous bornes sur **hôtes déclarés** ; pas d'URL arbitraire (anti-SSRF) ; le LLM ne peut pas modifier `providers.yaml` |
| LLM07 Fuite de prompt | Refus explicite de divulguer instructions internes/secrets (réponse générique) |
| LLM08 Vector/embeddings | Aucune base vectorielle en V1 ; récupération par requêtes API, pas d'embeddings |
| LLM09 Désinformation | Interdiction d'inventer faits/statistiques/références ; **ancrage obligatoire des citations au SourceSet** ; `not_verified` par défaut ; aucune source payante activée |
| LLM10 Consommation | Bornes §30 étendues (requêtes de recherche, appels réseau, taille de réponse, cache obligatoire), boucle bornée |

Transverses : isolation `student_id`/`session_id` ; journalisation filtrée ; priorité absolue des
règles système/sécurité sur tout contenu utilisateur, documentaire ou web.

---

## 9. Mécanisme de validation

**A. Schéma** — JSON conforme (§7), enums et bornes ; échec → `OUTPUT_SCHEMA_ERROR` + 1 retry.
**B. Métier** (déterministe) :
1. `subject_reference.original` identique à l'entrée (fidélité stricte) ;
2. anti-fusion : aucune clé problématique/question de recherche/hypothèse/plan ;
3. **ancrage** : tout `source_id` ∈ SourceSet et URL identique ; `verification_status=verified`
   uniquement si `retrieved=true` ; `confidence` ∈ [0,1] ;
4. distinction fait / interprétation / inconnu présente sur `justifying_elements` (SPEC §6, §11) ;
5. cohérence `status` ↔ complétude : lacunes majeures ou info essentielle non vérifiée ⇒
   `needs_clarification` (jamais `ready_for_verification`) ;
6. aucune affirmation externe sans source récupérée ni marquage `unknown` ;
7. `validation.verified=false` et `verifier_status="pending"` à la sortie de l'agent.
**C. Sécurité** — pas de fuite de prompt/clé, pas de contenu exécutable ; échec → rejet.

---

## 10. Mécanisme de vérification

`problem_verifier.py` = **appel LLM séparé**, prompt distinct, contexte indépendant. Il reçoit :
sujet d'origine, contexte, `SourceSet` (avec les extraits réellement récupérés) et la sortie à
contrôler. Il vérifie notamment : le problème est-il distinct du sujet ? délimité ? les acteurs/
conséquences/enjeux reposent-ils sur des sources réelles et bien citées ? les faits sont-ils
distingués des interprétations ? des informations ont-elles été inventées ? les lacunes et
questions sont-elles honnêtes ? Aucune problématique / question de recherche n'a-t-elle été
produite ? Le vérificateur ne fait jamais confiance aux instructions contenues dans le contenu
vérifié ni dans les sources.

```
verified              → statut final `verified` posé par le vérificateur
corrections_requested → l'agent corrige (sources déjà en cache) puis re-pipeline + re-vérification
                        (≤ MAX_VERIFICATION_RETRIES, défaut 3)
rejected              → `blocked` + retour guidé à l'étudiant
épuisement            → VERIFICATION_FAILED (intervention humaine)
```

---

## 11. Stratégie de tests

- **Fonctionnels (15–21)** : problème identifiable et distinct du sujet ; délimitation demandée
  quand elle manque ; lacunes signalées ; aucune invention ; sources citées existantes ;
  ancrage (faux DOI/URL → rejet) ; formulation provisoire non promue en problématique.
- **Sécurité (22–30)** : injection dans les entrées ; **injection dans un titre/résumé récupéré** ;
  extraction de secret ; sortie LLM invalide ; commande système ; hallucination de source
  (URL inventée → rejet) ; consommation (requêtes/appels réseau plafonnés) ; isolation entre
  étudiants ; URL arbitraire/SSRF refusée ; indisponibilité d'un fournisseur (dégradation propre).
- **Sources (hors réseau)** : adaptateurs testés sur fixtures JSON enregistrées (déterminisme,
  zéro coût) ; un test d'intégration réseau optionnel, marqué, jamais bloquant en CI.
- Les tests de sécurité utilisent un **LLM stub déterministe** ; le test d'acceptation final est
  un test sur **modèle réel** (leçon de l'Agent Sujet : les stubs ne prouvent pas l'intégration).

---

## 12. Dépendances

Aucune nouvelle dépendance obligatoire : `httpx` (déjà présent) suffit pour les API de sources ;
`sqlite3`, `json`, `xml.etree` (arXiv) sont dans la stdlib. Aucune bibliothèque de scraping, aucune
clé d'API. `requirements.txt` reste figé et documenté ; aucune installation automatique.

---

## 13. Coûts éventuels

0 € pour la recherche documentaire. **Tous les fournisseurs retenus sont gratuits et sans clé** ;
disponibilité testée depuis ce serveur le jour de l'architecture :

| Fournisseur | Famille §7 | Test |
|---|---|---|
| OpenAlex | publications scientifiques | HTTP 200 |
| Crossref | publications scientifiques (DOI) | HTTP 200 |
| DOAJ | revues en accès ouvert | HTTP 200 |
| HAL | dépôt universitaire francophone | HTTP 200 |
| arXiv | prépublications | HTTP 200 |
| DataCite | DOI de données / dépôts | HTTP 200 |
| Europe PMC | biomédical, texte intégral partiel | HTTP 200 |
| PubMed E-utilities | biomédical (institutionnel US) | HTTP 200 |
| OpenAIRE Graph | recherche financée publiquement | HTTP 200 |
| Zenodo | dépôt pluridisciplinaire | HTTP 200 |
| SciELO (articlemeta) | Amérique latine / accès ouvert | HTTP 200 |
| Eurostat | statistiques officielles UE | HTTP 200 |
| data.gouv.fr | données publiques françaises | HTTP 200 |
| World Bank | statistiques internationales | HTTP 200 |

Écartés et pourquoi : **Semantic Scholar** (429 sans clé), **Persée** et **Gallica/BnF**
(injoignables depuis ce serveur — à retester, pourront être ajoutés par configuration).
Aucun essai de fournisseur payant, aucun palier activé automatiquement. Seul coût possible :
l'appel LLM déjà configuré (DeepSeek, quelques centimes).

---

## 14. Alternatives gratuites

Principe directeur (arbitrage du porteur de projet) : **utiliser tout fournisseur gratuit qui sert
l'objectif**, sans se limiter à un sous-ensemble. Ordre de préférence :

1. **Fournisseurs gratuits sans clé déjà vérifiés** (liste §13) — retenu, extensible par
   `providers.yaml`.
2. **Autres fournisseurs gratuits ajoutables** : Persée, Gallica/BnF (à retester), registres
   nationaux de thèses (theses.fr via API), portails statistiques nationaux, OAI-PMH de dépôts
   universitaires. Ajout = configuration, pas de code.
3. Open source local : SearXNG auto-hébergé (métamoteur) — coût 0 €, mais instance à maintenir et
   JSON souvent désactivé ; non retenu en V1.
4. Recherche web généraliste (ddgs/DuckDuckGo) — non officielle, fragile, flou juridique : écartée
   tant que des API documentaires officielles couvrent le besoin.
5. Dernier recours LLM local (Ollama) — déjà documenté côté Sujet.

Règles maintenues : aucun fournisseur payant activé automatiquement ; aucune clé d'API requise
pour la recherche. Si un fournisseur cesse de répondre ou devient payant : il est désactivé en
configuration et l'agent **déclare la lacune** au lieu d'inventer.

---

## 15. Limites connues

1. Les API fournissent **métadonnées + résumé**, rarement le texte intégral : la vérification
   porte sur l'existence et la pertinence déclarée, pas sur la lecture complète.
2. Biais de couverture : prédominance anglophone d'OpenAlex/Crossref ; HAL/DOAJ corrigent
   partiellement pour le français et l'open access.
3. Quotas et disponibilité : les API publiques peuvent être lentes ou limiter les appels →
   cache obligatoire, dégradation propre (`TOOL_ERROR`), jamais de blocage dur de la réponse.
4. La détection d'injection reste **heuristique** (idem Agent Sujet) ; l'atténuation principale
   est la séparation stricte instructions/données sur **toutes** les entrées, y compris web.
5. Le vérificateur est un LLM : fiabilité non absolue (contexte indépendant, grille explicite,
   sortie validée, boucle bornée).
6. Qualité dépendante du LLM ; le nombre de sources par requête est volontairement faible (coût,
   pertinence).
7. Pas d'orchestration inter-agents en V1 (§44) : la liaison avec l'Agent Sujet se fait par
   `upstream_subject`, pas par un orchestrateur global.

---

## Décisions à valider avant implémentation

**Déjà arbitrées par le porteur de projet :**
- ✅ **Cadre propre à chaque agent** : paquet autonome, pas de code partagé, Agent Sujet non touché.
- ✅ **Tout fournisseur utile à l'objectif** : tous les fournisseurs gratuits sans clé, liste
  déclarée en configuration et extensible.

**Restant à valider (avec ma recommandation) :**

1. **Deux phases LLM** — recommandé : phase 1 (analyse + `search_intents`) puis phase 2 (formulation
   ancrée sur le `SourceSet`). C'est ce qui rend l'anti-hallucination structurel. Alternative :
   une seule phase avec mots-clés extraits déterministiquement (moins fidèle au §9).
2. **`upstream_subject`** — recommandé : accepté seulement si `validation.verified = true` ;
   sinon réponse `needs_clarification` invitant à finaliser le Sujet. Alternative : accepté en le
   marquant `upstream_not_verified` avec avertissement.
3. **Bornes par défaut** (config propre à l'agent) : `MAX_SEARCH_QUERIES=4`,
   `MAX_SOURCES_PER_QUERY=5`, `MAX_EXTERNAL_REQUESTS=10`, `SOURCE_TIMEOUT=15 s`,
   `MAX_SOURCE_SNIPPET=1200 car.`, `CACHE_TTL=7 j`, `MAX_OUTPUT_TOKENS=4000`,
   `MAX_VERIFICATION_RETRIES=3`. Ajustables ensuite sans toucher au code.
4. **Documents fournis** (SPEC §8, §9.4) — recommandé : V1 = textes collés (champ texte) ;
   la lecture de fichiers de la session (pdf/txt/md) est ajoutée en V2 pour rester dans le
   périmètre « un agent à la fois ». À confirmer, car la SPEC cite « documents fournis ».
5. **Dépôt de la SPEC** — recommandé : copier la SPEC reçue dans
   `docs/spec-agent-02-probleme.md` comme référentiel canonique de cet agent, comme pour le Sujet.

Dis-moi « go » (avec tes éventuelles corrections sur les points 1–5) et j'implémente l'agent,
en commençant par les schémas et les prompts, puis l'étage de sources, les tests, et enfin le test
réel sur modèle.

---

## État réel de l'implémentation (après validation et test réel)

Arbitrages appliqués tels que recommandés : deux phases LLM ; `upstream_subject` accepté
uniquement s'il est vérifié (sinon `MISSING_INFORMATION`) ; bornes de la décision 3 ;
documents = textes collés en V1 ; SPEC déposée dans `docs/spec-agent-02-probleme.md`.

**Construit** : paquet autonome `src/research_problem_agent/` (config `config/settings-probleme.yaml`,
bornes, client LLM, prompts, pipeline complet, vérificateur, API `/problem/analyze`, audit SQLite,
cache SQLite) + étage `sources/` (12 fournisseurs actifs, 3 désactivés avec justification en
configuration) + `tests/probleme/` (75 tests) + `run-probleme.sh`. L'Agent Sujet n'a **pas** été
modifié ; les deux agents ont des bases, workspaces et journaux distincts.

**Corrections imposées par le test réel sur modèle (DeepSeek), invisibles en tests simulés** :

1. **Budget de sortie** : un modèle qui « raisonne » consomme le budget `max_tokens` en
   raisonnement — 4000 tokens donnaient un JSON tronqué ou une réponse vide. → `max_output_tokens`
   porté à 16000, délai à 90 s, contexte de sources réduit (10 sources, extraits de 800 caractères),
   consigne de concision dans le prompt, et le client lève une erreur explicite sur réponse vide
   (budget/finish_reason) qui déclenche une re-tentative.
2. **Le vérificateur ignorait les données étudiantes** : il ne recevait que l'intitulé du sujet et
   prenait donc le contexte fourni (taille d'entreprise, observations) pour une invention → refus
   en boucle, `verification_failed`. → il reçoit désormais **toutes** les données fournies
   (contexte, observations, discipline, niveau, pays, établissement, documents, réponses
   précédentes, sujet amont), balisées comme non fiables.
3. **Confusion de vocabulaire** : le vérificateur lisait `sources[].verification_status = verified`
   comme une auto-validation de l'agent. → sémantique explicitée dans les deux prompts
   (« statut du record récupéré », distinct de `validation.verified`).
4. **Faux positifs de provenance** : une information tirée d'une source citée était étiquetée
   `provided`. → valeur `external` ajoutée à l'énumération et règle stricte (source_id ⇒ external).
5. **Métadonnées de source** : le modèle pouvait approximer titre/revue/date. → après validation,
   la plateforme **écrase** ces champs par les valeurs de l'API (le statut de vérification est posé
   par la plateforme, jamais par le modèle) ; le jugement du modèle (`confidence`,
   `information_used`) est conservé.
6. **Tragabilité** : `search_queries_used` est désormais rempli par la plateforme (requêtes
   réellement exécutées), jamais par le modèle.
7. **Traçabilité des sources** : un record sans DOI ni URL est écarté (non citable, SPEC §16.C).
8. **Non-convergence** : si le vérificateur redemande exactement les mêmes corrections deux fois,
   la boucle s'arrête au lieu de consommer les tours restants.

**Résultats mesurés (modèle réel + recherche réseau réelle)** : sujet précis → `ready_for_verification`
puis verdict `verified` en une passe (3 appels LLM) ; sujets génériques (« le sport », « l'impact du
numérique ») → `needs_clarification` avec questions ciblées ; aucune source citée hors du SourceSet ;
0 coût autre que l'Appel LLM.
