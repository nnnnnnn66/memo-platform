# Architecture V1 — Agent Revue de littérature & Diagnostic Épistémologique (`literature_review_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points). **Aucune implémentation n'a été faite.**
> Ce document attend la validation humaine avant toute ligne de code.
> Référentiel : `docs/spec-agent-03-revue-litterature.md` (SPEC reçue, matrice §4.4A incluse).
> Éléments de l'agent : `docs/elements-agent-03-revue-litterature.md` (profil Hermes
> `agent-litterature` + paquet prévu). **Cadre autonome** : aucun agent existant n'est modifié et
> aucun code n'est partagé avec eux.

---

## 1. Architecture

Une **campagne documentaire** en étapes, chacune suivie d'une validation déterministe et d'un
**point de reprise persisté** (un échec tardif ne fait pas perdre la collecte déjà faite).
Le principe des agents précédents est conservé : *aucune sortie LLM utilisée avant
Parser → Schéma → Métier → Sécurité*, et *le modèle ne déclenche jamais lui-même une requête réseau*.

```
ÉTUDIANT (sujet, mots-clés, cadre, style bibliographique)
   │
   ▼
[1] Input Controller          ── student_id/session_id + snapshots amont (sujet, problème)
[2] Input Validation          ── contrat d'entrée, tailles, champs obligatoires
[3] Security Layer            ── entrées étudiantes + documents = DONNÉES NON FIABLES
   │
   ▼
[4] PRÉ-CADRAGE (déterministe) ── prérequis SPEC §5 présents ?
   │     non → status `needs_clarification` + questions précises, AUCUNE campagne lancée
   │     oui → suite
   ▼
[5] LLM P1 — CONCEPTS & MOTS-CLÉS ── arborescence (concepts → mots-clés, synonymes, variantes,
   │                                   traductions EN) + stratégie de recherche + cascade
   │                                   géographique CI → Afrique de l'Ouest → Afrique → intl
[6] Parser → Schéma → Métier        ── bornes de requêtes, langue, types, période, anti-fusion
   │
   ▼
[7] RECHERCHE DOCUMENTAIRE (OUTIL DÉTERMINISTE, sans LLM)   ← cœur du module
   │     14 fournisseurs gratuits sans clé + pagination bornée + cache + hôtes en liste blanche
   │     → Corpus brut (métadonnées réelles : auteurs, titre, revue, année, DOI, URL, résumé)
   ▼
[8] NORMALISATION & DÉDOUBLONNAGE ── clé DOI → URL canonique → titre normalisé (auteurs+année)
   │                                   + notation déterministe (recouvrement concepts, type de
   │                                   document, langue, année, géographie, accès ouvert)
   ▼
[9] ENRICHISSEMENT ACCÈS OUVERT (Unpaywall, déterministe) ── `full_text_available`, URL OA
   │
   ▼
[9bis] ACQUISITION & LECTURE DU TEXTE INTÉGRAL (OUTIL DÉTERMINISTE, sans LLM)   ← NOUVEAU
   │     Téléchargement des PDF EN ACCÈS OUVERT uniquement (jamais de paywall) :
   │       dépôt institutionnel > éditeur open access > prépublication (HAL, arXiv, Zenodo,
   │       OSF, DOAJ, Unpaywall oa_locations, fichiers des fournisseurs)
   │     Bornes : HTTPS seul, IP privées refusées, signature %PDF- vérifiée, ≤ 30 Mo, timeout 40 s,
   │       plafond de documents téléchargés et quota disque par session
   │     Stockage : workspace/<student_id>/<session_id>/documents/<doc_id>_<slug>.pdf
   │       + manifeste (sha256, taille, URL source, licence) → TÉLÉCHARGEABLE par l'étudiant
   │     Lecture : pdfminer.six (MIT) → texte par page ; découpage en sections repérées
   │       (résumé, introduction, méthode, résultats, discussion, conclusion, limites)
   │     Document scanné (pas de couche texte) : signalé `text_layer = false`, repli sur le résumé
   ▼
[10] LLM P2 — NOTATION & EXTRACTION PAR LOTS BORNÉS ── pour chaque lot de N documents :
   │        pertinence (0–1), thème, méthode, terrain, résultats, limites → JSON validé
   │        CHAQUE affirmation tirée du texte porte une CITATION VERBATIM + sa localisation
   │        (l'extraction ne porte jamais sur un document non lu)
[11] SÉLECTION FINALE ── tri par pertinence, plafond MAX_DOCUMENTS (objectif 60),
   │        `corpus_sufficiency` = sufficient | partial | insufficient  (jamais de remplissage)
   ▼
[12] LLM P3 — COMPARAISON ── convergences, divergences, limites, lacunes, regroupées par thème
[13] LLM P4 — SYNTHÈSE CRITIQUE ── état des connaissances, angles morts, questions ouvertes
   │        (la BIBLIOGRAPHIE est mise en forme par un module DÉTERMINISTE : APA 7 / ISO 690 /
   │         Vancouver, à partir des seules métadonnées vérifiées — le modèle n'écrit pas les
   │         références)
[14] LLM P5 — DIAGNOSTIC MÉTHODOLOGIQUE & ALIGNEMENT ÉPISTÉMOLOGIQUE (module expert)
   │        matrice §4.4A : indicateurs détectés → logique (inductive/déductive/hypothético-
   │        déductive/abductive) → type de recherche → approche → techniques ; justification,
   │        alternatives, alertes d'alignement sujet ↔ problème ↔ question ; PROPOSITION à valider
   ▼
[15] Parser → Schéma → Métier → Sécurité   (sur CHAQUE sortie des étapes 5 à 14)
   │        contrôle d'ancrage : toute référence citée doit exister dans le corpus réel
   ▼
[16] VÉRIFICATEUR INDÉPENDANT (LLM séparé) ── contrôles L1–L12 ; sortie elle-même validée
   │        verified | corrections_requested (≤ MAX_VERIFICATION_RETRIES) | rejected
   ▼
[17] Persistance (corpus, comparaison, synthèse, diagnostic, bibliographie) + audit + réponse HTTP
```

Points non négociables :
- **Moindre privilège** : `read: session_only` + recherche publique autorisée, `write:
  workspace_only`, `delete/deploy/send: false`.
- **Ancrage** : un document affiché vient d'une API réelle ; un lien ou un DOI fabriqué ne franchit
  pas la validation métier. Les métadonnées affichées sont **écrasées** par la vérité de l'API.
- **Honnêteté documentaire** : 60 est un objectif ; 35 documents réels sont préférables à 60 dont
  25 de remplissage ; `corpus_sufficiency` le dit explicitement.
- **Diagnostic = proposition** : la posture épistémologique et la démarche sont argumentées et
  soumises à validation de l'étudiant et de son directeur ; jamais imposées.
- **0 €** : fournisseurs gratuits sans clé uniquement (voir §13).

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings-litterature.yaml          # propre à l'agent (LLM, bornes, chemins, sources, biblio)
├── docs/
│   ├── spec-agent-03-revue-litterature.md              # SPEC reçue (déposée)
│   ├── architecture-agent-03-revue-litterature-v1.md   # ce document
│   └── elements-agent-03-revue-litterature.md          # fiche des 19 éléments
├── src/literature_review_agent/            # paquet AUTONOME
│   ├── main.py                             # app FastAPI (lifespan, state)
│   ├── api/routes.py                       # POST /literature/review, GET /literature/{st}/{sess}, /health
│   ├── pipeline/
│   │   ├── input_controller.py             # session + snapshots amont
│   │   ├── input_validation.py             # contrat d'entrée, tailles
│   │   ├── prerequisites.py                # pré-cadrage SPEC §5 (étape [4], déterministe)
│   │   ├── security_layer.py               # balisage + scan des entrées ET des contenus récupérés
│   │   ├── campaign.py                     # orchestrateur de la campagne, points de reprise
│   │   ├── keywords_stage.py               # LLM P1 (concepts, mots-clés, stratégie)
│   │   ├── retrieval_stage.py              # étape [7] : campagnes de requêtes multi-fournisseurs
│   │   ├── dedup_ranking.py                # étape [8] : normalisation, dédup, notation déterministe
│   │   ├── fulltext_stage.py               # étape [9] : Unpaywall → accès ouvert
│   │   ├── scoring_stage.py                # LLM P2 par lots + sélection finale [11]
│   │   ├── comparison_stage.py             # LLM P3
│   │   ├── synthesis_stage.py              # LLM P4 (synthèse)
│   │   ├── diagnosis_stage.py              # LLM P5 (matrice §4.4A + alignement)
│   │   ├── output_parser.py
│   │   ├── schema_validation.py
│   │   ├── business_validation.py           # ancrage, dédup, cohérence matrice, style, anti-fusion
│   │   ├── security_validation.py
│   │   └── verifier.py                      # vérificateur indépendant
│   ├── bibliography/
│   │   ├── styles.py                        # rendu APA 7 / ISO 690 / Vancouver (déterministe)
│   │   └── normalize.py                     # normalisation auteurs/année/titre/venue
│   ├── diagnosis/
│   │   └── matrix.py                        # matrice §4.4A en DONNÉES + contrôle de cohérence
│   ├── sources/
│   │   ├── providers.yaml                   # fournisseurs + hôtes autorisés (extensible)
│   │   ├── registry.py                      # sélection par famille et par cascade géographique
│   │   ├── http.py                          # client borné (timeout, taille, requêtes polies)
│   │   ├── cache.py                         # cache SQLite des requêtes (14 j)
│   │   ├── corpus.py                        # DocumentRecord + Corpus (ids stables, dédup)
│   │   ├── fulltext.py                      # Unpaywall (accès ouvert) — déterministe
│   │   └── adapters/
│   │       ├── openalex.py crossref.py doaj.py hal.py theses_fr.py arxiv.py
│   │       ├── europepmc.py pubmed.py openaire.py zenodo.py datacite.py
│   │       └── osf.py datagouv.py dataeuropa.py        # + ajouts par configuration
│   ├── schemas/
│   │   ├── input.py keywords.py document.py output.py diagnosis.py verifier.py
│   ├── core/
│   │   ├── config.py limits.py errors.py logging.py sessions.py security_rules.py
│   └── storage/
│       ├── workspace.py                    # artefacts par session
│       └── audit.py                        # journal d'audit (SQLite)
├── run-litterature.sh                      # port 8030
├── workspace/                              # audit-litterature.db, documents-cache.db, <student>/<session>/
└── tests/litterature/                      # fonctionnels, sécurité, fournisseurs, biblio, matrice
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `pipeline/prerequisites.py` | Vérifie les prérequis de la SPEC §5 (sujet exact, niveau, discipline, zone géographique, style bibliographique). Manque **essentiel** → `needs_clarification`, campagne non lancée (évite une collecte coûteuse hors cadre). Manque secondaire → valeur par défaut **déclarée** comme telle. |
| `pipeline/campaign.py` | Enchaîne les étapes, persiste un **checkpoint** après chacune (reprise possible), applique les bornes globales (requêtes, documents, lots, budget de tokens). |
| `pipeline/retrieval_stage.py` | Traduit les mots-clés et la stratégie **validés** en requêtes par fournisseur, avec pagination bornée et **cascade géographique** (CI → Afrique de l'Ouest → Afrique → international). Aucun appel piloté directement par le modèle. |
| `pipeline/dedup_ranking.py` | Dédup (DOI → URL canonique → titre+auteurs+année normalisés), fusion des métadonnées (la plus complète gagne), notation déterministe de pré-pertinence. |
| `pipeline/fulltext_stage.py` | Unpaywall sur les DOI retenus : `full_text_available`, URL OA légale. Aucun contournement de paywall. |
| `pipeline/scoring_stage.py` | Notation/extraction par **lots bornés** (P2) : pertinence, thème, méthode, terrain, résultats, limites. Puis sélection finale plafonnée et calcul de `corpus_sufficiency`. |
| `diagnosis/matrix.py` | La matrice §4.4A est stockée **en données** (8 lignes) : le diagnostic doit pointer une ligne (`matrix_row_id`) et ses indicateurs ; la validation vérifie la cohérence déclarée (logique ↔ type ↔ approche ↔ techniques) et accepte les combinaisons mixtes **si** elles sont justifiées. |
| `bibliography/styles.py` | Rendu déterministe des références (APA 7, ISO 690, Vancouver) à partir des métadonnées vérifiées : **le modèle ne rédige jamais une référence**. |
| `sources/providers.yaml` | Fournisseurs déclarés en configuration (hôte autorisé, famille, type de source, cascade, langues). Ajouter un fournisseur gratuit = éditer ce fichier. |
| `sources/http.py` | Client borné et **poli** (User-Agent identifiable, `mailto` de courtoisie pour OpenAlex/Crossref/Unpaywall, timeout, taille maximale, retries limités). |
| `pipeline/business_validation.py` | Anchrage (chaque `doc_id` cité existe dans le corpus, DOI/URL identiques), dédup effective, cohérence du diagnostic avec la matrice, style bibliographique respecté, anti-fusion (aucune problématique/question de recherche), `corpus_sufficiency` honnête. |

---

## 4. Flux des données

```
POST /literature/review
  body: { student_id, session_id?, subject_text, research_problem?, discipline, academic_level,
          country?, geographical_scope?, period?, review_type?, citation_style?, language_prefs?,
          supervisor_guidelines?, student_keywords?, student_documents?[], known_references?[],
          upstream_subject?, upstream_problem?, constraints? }
   │
   ├─ Input Controller → session ; snapshots amont acceptés SEULEMENT si `validation.verified`
   ├─ Input Validation → 422 INVALID_INPUT si non conforme
   ├─ Security Layer  → balisage non fiable (sujet, contexte, documents, consignes du directeur)
   ├─ Pré-cadrage     → manque essentiel ? → 200 `needs_clarification` + questions, FIN
   │
   ├─ LLM P1 → mots-clés + stratégie        → Parser → Schéma → Métier
   ├─ Retrieval (déterministe)              → corpus brut (checkpoint)
   ├─ Dédup + notation déterministe         → corpus dédoublonné (checkpoint)
   ├─ Unpaywall                             → accès ouvert renseigné (checkpoint)
   ├─ LLM P2 par lots (≤ 6 lots de 12)      → pertinence + extraction → schéma/métier/ sécurité
   ├─ Sélection finale (≤ 60, objectif)     → corpus retenu + `corpus_sufficiency`
   ├─ LLM P3 → comparaison                  → schéma/métier/sécurité
   ├─ LLM P4 → synthèse                     → schéma/métier/sécurité
   ├─ LLM P5 → diagnostic (matrice §4.4A)   → schéma/métier/sécurité (cohérence de matrice)
   ├─ Bibliographie (déterministe)          → rendu APA 7 / ISO 690 / Vancouver
   │
   ├─ Statut provisoire : needs_clarification | ready_for_verification | blocked
   ├─ Vérificateur indépendant (L1–L12)     → verified | corrections_requested | rejected
   └─ Persistance + audit + réponse HTTP
```

Exemple de réponse (extrait) :
```json
{
  "session_id": "…", "status": "ready_for_verification", "verifier_status": "verified",
  "corpus": { "documents_count": 47, "corpus_sufficiency": "sufficient",
              "providers_used": ["openalex","crossref","hal","theses_fr","doaj","unpaywall"],
              "duplicates_removed": 213, "by_language": {"fr": 18, "en": 26, "autre": 3},
              "by_geography": {"Côte d'Ivoire": 4, "Afrique de l'Ouest": 6, "Afrique": 5,
                               "international": 32} },
  "documents": [ { "doc_id": "D1", "authors": ["…"], "title": "…", "year": 2021,
                   "venue": "…", "doi": "10.…", "url": "https://doi.org/10.…",
                   "document_type": "article", "full_text_available": true,
                   "relevance": 0.91, "theme": "…", "method": "…", "findings": "…",
                   "limits": ["…"], "reference_apa": "…", "verification_status": "verified" } ],
  "comparison": { "themes": [ { "theme": "…", "convergences": ["…"], "divergences": ["…"],
                                "limits": ["…"], "gaps": ["…"], "doc_ids": ["D1","D7"] } ] },
  "synthesis": { "state_of_knowledge": "…", "open_questions": ["…"], "blind_spots": ["…"] },
  "diagnosis": { "matrix_row_id": "hypothesis_test", "semantic_indicators": ["Quel est l'impact de…"],
                 "reasoning_logic": "hypothetico_deductive", "research_type": "explanatory",
                 "approach": "quantitative", "techniques": ["questionnaire fermé","régression"],
                 "justification": "…", "alternatives": ["…"], "alignment_alerts": ["…"],
                 "status": "proposal_to_validate_with_student" },
  "bibliography": { "style": "apa7", "entries": ["…"], "entries_count": 47 },
  "evidence": { "queries": ["…"], "providers": [{"id":"openalex","requests":12,"results":85}],
                "cache_hits": 34, "external_requests": 61, "llm_calls": 9 },
  "validation": { "verified": true, "verifier_status": "verified" }
}
```

---

## 5. Modèle de données

```
CampaignRequest        # voir §6
Corpus
  session_id, queries[], providers_used[], providers_failed[], duplicates_removed,
  documents[], corpus_sufficiency, retrieved_at, counts (par langue, géographie, type, accès ouvert)
DocumentRecord
  doc_id            str            # D1, D2… (stable dans la session)
  provider          enum(…)        # fournisseur d'origine (openalex, crossref, hal, theses_fr, …)
  source_type       enum            # scientific | peer_reviewed | thesis | book | research_org |
                                    # university | governmental | international_org | institutional
  authors[]         str
  title             str
  year              int | null
  venue             str            # revue, université, organisme
  doi               str | null
  url               str            # canonique, issue de l'API
  language          str | null
  document_type     enum(article|thesis|book|report|dataset|preprint|other)
  abstract          str            # extrait réellement récupéré (borné)
  geographic_scope  enum(ivory_coast|west_africa|africa|international|unclear)  # détecté, signalé comme tel
  full_text_available bool          # Unpaywall
  oa_url            str | null
  relevance         float [0..1]
  theme             str
  method            str | null
  findings          str | null
  limits            []str
  reference_apa     str            # rendu déterministe
  retrieved         bool = true
  verification_status enum(verified | not_verified)
Diagnosis
  matrix_row_id, semantic_indicators[], reasoning_logic, research_type, approach, techniques[],
  justification, alternatives[], alignment_alerts[], status="proposal_to_validate_with_student"
VerifierOutput  verdict, controls[{code,resultat,detail}], corrections[], flags[]
AuditLog  session_id, agent_id, version, timestamp, status, errors[], attempts, verifications,
          llm_calls, external_requests, cache_hits, providers[], documents_count, source_ids[]
```

Enums : `STATUS = needs_clarification | ready_for_verification | blocked | verified` ;
`CORPUS_SUFFICIENCY = sufficient | partial | insufficient` ;
`ERROR_STATE = INVALID_INPUT | MISSING_INFORMATION | OUTPUT_SCHEMA_ERROR | SECURITY_VIOLATION |
TOOL_ERROR | TIMEOUT | RESOURCE_LIMIT | VERIFICATION_FAILED`.

**Stockage V1** : JSON par session dans `workspace/<student_id>/<session_id>/` (`corpus.json`,
`comparison.json`, `synthesis.json`, `diagnosis.json`, `bibliography.json`, `checkpoints/`) +
audit SQLite + cache SQLite des requêtes. **Pas de base vectorielle** (pas d'embeddings, §28
respecté) ; la « mémoire » de la session est le corpus persisté.

---

## 6. Contrat d'entrée (SPEC §5, §6)

| Champ | Type | Obligatoire | Contrainte |
|---|---|---|---|
| `student_id` | str | oui | opaque, isolation |
| `session_id` | str(uuid) | non | créé si absent |
| `subject_text` | str | **oui** | non vide, ≤ `MAX_INPUT_SIZE` |
| `research_problem` | str | non | problème validé (étape 2) s'il existe |
| `discipline` | str | **oui** (prérequis §5) | sinon `needs_clarification` |
| `academic_level` | str | **oui** (prérequis §5) | ex. « Master 2 » |
| `country` / `geographical_scope` | str | oui si le sujet est situé | détermine la cascade |
| `period` | str | non | borne temporelle de la recherche |
| `review_type` | enum(systematic|narrative|scoping) | non | défaut : `narrative` (déclaré) |
| `citation_style` | enum(apa7|iso690|vancouver) | non | défaut : `apa7` (déclaré) |
| `languages` | list[str] | non | défaut : `["fr","en"]` |
| `supervisor_guidelines` | str | non | consignes du directeur (texte) |
| `student_keywords` | list[str] | non | mots-clés déjà fournis par l'étudiant |
| `known_references` | list[str] | non | références déjà utilisées (vérifiées comme les autres) |
| `student_documents` | list[str] | non | textes collés (V1) ; lecture de fichiers = V2 |
| `upstream_subject` | objet | non | sortie Agent Sujet, **acceptée si `validation.verified = true`** |
| `upstream_problem` | objet | non | sortie Agent Problème, **acceptée si `validation.verified = true`** |
| `constraints` | str | non | contraintes de recherche |

Toute information retenue porte une **provenance** : `fourni` | `retrieved` | `inferred` | `unknown`.

---

## 7. Contrat de sortie (SPEC §4, §7, §16)

```json
{
  "agent": "literature_review_agent",
  "version": "1.0",
  "status": "needs_clarification | ready_for_verification | blocked",
  "subject_reference": { "original": "", "reformulated": "" },
  "scope": { "discipline": "", "geographical_scope": "", "period": "", "languages": [],
             "cascade": ["Côte d'Ivoire", "Afrique de l'Ouest", "Afrique", "International"] },
  "keywords": { "concepts": [ { "concept": "", "keywords_fr": [], "keywords_en": [],
                                "synonyms": [], "variants": [] } ],
                "strategy": { "combinations": [], "document_types": [], "period": "",
                              "selection_criteria": [] } },
  "corpus": { "documents_count": 0, "corpus_sufficiency": "partial",
              "documents": [], "duplicates_removed": 0, "providers_used": [],
              "providers_failed": [], "by_language": {}, "by_geography": {}, "by_type": {} },
  "comparison": { "themes": [ { "theme": "", "convergences": [], "divergences": [], "limits": [],
                                "gaps": [], "doc_ids": [] } ] },
  "synthesis": { "state_of_knowledge": "", "authors_and_schools": [], "open_questions": [],
                 "blind_spots": [], "caution_notes": [] },
  "diagnosis": { "...": "voir §5" },
  "bibliography": { "style": "apa7", "entries": [], "entries_count": 0 },
  "unknowns": [], "limits_of_this_review": [],
  "confidence": { "overall": 0.0, "rationale": "" },
  "validation": { "verified": false, "verifier_status": "pending" }
}
```

Règles structurelles :
- `documents[]` : chaque entrée porte `doc_id`, `doi`/`url` **issus de l'API**, `retrieved = true`,
  `verification_status` posé par la plateforme, et `reference_apa` **rendue par le module
  déterministe** (jamais rédigée par le modèle).
- Aucune clé problématique / question de recherche / hypothèse / méthodologie personnelle de
  l'étudiant (anti-fusion) ; le diagnostic est une **proposition** (`status =
  proposal_to_validate_with_student`).
- `corpus.documents_count` ≤ `MAX_DOCUMENTS` ; si le corpus réel est inférieur à l'objectif, c'est
  déclaré (`corpus_sufficiency`, `limits_of_this_review`) — jamais compensé.
- `validation.verified = true` uniquement sur verdict du vérificateur.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mesure V1 |
|---|---|
| LLM01 Injection (entrées étudiantes **et** métadonnées/résumés récupérés) | Tout est balisé DONNÉE NON FIABLE et scanné (titres, résumés, noms de revues) avant d'être remis au modèle ; les consignes du directeur sont du texte, pas des ordres au système |
| LLM02 Fuite d'information | Aucun secret en contexte ; sortie filtrée ; logs filtrés ; aucun document payant téléchargé |
| LLM03 Supply chain | Dépendances figées (aucune nouvelle) ; fournisseurs déclarés en configuration ; aucune installation automatique |
| LLM04 Poisoning | Les métadonnées récupérées n'ont aucun effet sur les prompts, permissions ou bornes ; elles ne modifient jamais la configuration |
| LLM05 Traitement de sortie | Toute sortie LLM traverse Parser → Schéma → Métier → Sécurité ; rien n'est exécuté |
| LLM06 Agence excessive | Le modèle propose mots-clés, requêtes, notations et rédaction ; **l'outil** exécute les requêtes sur hôtes déclarés (anti-SSRF), sous bornes ; le modèle ne peut ni appeler une URL arbitraire, ni modifier les bornes, ni écrire hors workspace |
| LLM07 Fuite de prompt | Refus explicite ; réponse générique prévue |
| LLM08 Vector/embeddings | Aucune base vectorielle ; retrieval par API documentaires |
| LLM09 Désinformation | Interdiction d'inventer références/auteurs/années/DOI ; ancrage au corpus réel ; **bibliographie rendue par code** ; **extraction ancrée par citations verbatim vérifiées contre le texte réellement extrait** (§10bis) ; `corpus_sufficiency` honnête ; distinction fait / interprétation / inconnue |
| Téléchargement de fichiers (SSRF, abus) | Seules les URL **renvoyées par les API déclarées** sont téléchargées ; HTTPS uniquement ; schémas autres que http(s) refusés ; résolution d'hôte et **IP privées/loopback/métadonnées cloud refusées** ; signature `%PDF-` obligatoire ; taille ≤ 30 Mo ; timeout 40 s ; plafond de documents et quota disque par session |
| Droit d'auteur | Téléchargement **uniquement en accès ouvert légal** (Unpaywall/oa_locations, dépôts, éditeurs OA) ; aucun contournement de paywall ; licence conservée dans le manifeste ; fichiers stockés dans l'espace de la session, jamais redistribués |
| LLM10 Consommation | Bornes : requêtes (12), résultats/requête (25), documents (60), lots (6×12), lookups Unpaywall (60), appels LLM (≤ 12), timeout, cache obligatoire, budget de campagne |

Transverses : isolation `student_id`/`session_id` ; journalisation filtrée ; priorité absolue des
règles système sur tout contenu (entrée, document, métadonnée web) ; respect du droit d'auteur
(métadonnées + résumés, jamais de redistribution de texte intégral) ; pas de contournement de paywall.

---

## 9. Mécanisme de validation

**A. Schéma** — JSON conforme (§7) ; échec → `OUTPUT_SCHEMA_ERROR` + 1 re-tentative (puis échec
contrôlé, jamais de sortie non conforme transmise).
**B. Métier** (déterministe) :
1. `subject_reference.original` = copie exacte du sujet reçu ;
2. anti-fusion : aucune clé problématique / question de recherche / hypothèse / méthodologie ;
3. **ancrage** : tout `doc_id` cité (comparaison, synthèse, diagnostic, bibliographie) existe dans
   le corpus retenu ; DOI/URL identiques à ceux du record ; impossible de citer un document absent ;
4. `documents_count` = nombre réel d'entrées ; `≥` nombre de `doc_id` distincts cités ;
5. bibliographie : nombre d'entrées = nombre de documents retenus ; style = celui demandé ;
   `reference_apa` non vide pour chaque document ; aucun auteur/année inventé (comparé au record) ;
6. dédup : aucun DOI ni titre normalisé en double dans `documents[]` ;
7. cohérence du diagnostic : `matrix_row_id` ∈ matrice §4.4A ; la logique, le type de recherche,
   l'approche et les techniques déclarés correspondent à la ligne (ou sont justifiés comme
   combinaison mixte) ; `status = proposal_to_validate_with_student` ;
8. honnêteté : `corpus_sufficiency` doit être **exactement** la valeur du calcul déterministe
   (`scoring_stage.select_corpus`) — la suffisance n'est jamais déclarée par le modèle ;
9. **pertinence (garde de sélection)** : un document n'est retenu que s'il a été réellement analysé
   par la phase 2, que le modèle le juge pertinent (`relevance ≥ MIN_RELEVANCE = 0.3`) **et** qu'il
   recoupe au moins un concept du sujet (`record.term_hits ≥ 1`, calcul déterministe sur
   titre + résumé). Les documents écartés sont **comptés et déclarés** dans `limits_of_this_review`
   (`rejected_low_relevance`, `rejected_no_concept_match`, `not_analysed_over_budget`) : le corpus
   n'est jamais gonflé pour atteindre l'objectif de 60 ;
10. `validation.verified = false` et `verifier_status = "pending"` à la sortie de l'agent.
**C. Sécurité** — pas de fuite de prompt/clé, pas de contenu exécutable, pas de balise interne recopiée.
**D. Citations non vérifiables** — toute affirmation dont la citation ne se trouve pas dans le texte
réellement lu (ou, à défaut, dans le résumé fourni) est **retirée avant l'assemblage final**
(`campaign.sanitize_claims`) et le nombre de retraits est déclaré dans les limites de la revue.
**E. Reprise réseau** — les API publiques peuvent limiter le débit (OpenAlex renvoie `429`) :
`ApiFetcher` réessaie les `429`/`5xx` (`retry_on_transient`, `Retry-After` respecté, attente bornée),
compte chaque tentative dans le budget réseau et déclare les échecs persistants dans `providers_failed`.

---

## 10. Mécanisme de vérification (SPEC §12, §13, §14)

`verifier.py` = **appel LLM séparé**, prompt distinct, contexte indépendant. Il reçoit : les données
étudiantes, le corpus réel (métadonnées + résumés), les sorties produites et la grille L1–L12.
Contrôles :

| Code | Contrôle |
|---|---|
| L1 | Traçabilité : chaque document cité existe-t-il réellement dans le corpus fourni (DOI/URL) ? |
| L2 | Aucune référence, aucun auteur, aucune année inventés ? |
| L3 | Pertinence : les documents retenus servent-ils le sujet (pas de remplissage) ? |
| L4 | Couverture : cascade géographique et langues respectées, sans ajout artificiel du contexte ivoirien ? |
| L5 | Comparaison : convergences / divergences / limites / lacunes réellement adossées aux documents cités ? |
| L6 | Synthèse : fidèle à l'état des connaissances du corpus, sans extrapolation ? |
| L7 | Diagnostic : la ligne de matrice et la démarche proposée découlent-elles logiquement du sujet/problème ? |
| L8 | Alignement : incohérences signalées entre sujet, problème et démarche proposée ? |
| L9 | Honnêteté : `corpus_sufficiency`, limites et inconnues annoncées sans masquage ? |
| L10 | Anti-fusion : aucune problématique, question de recherche, hypothèse ou méthodologie produite à la place de l'étudiant ? |
| L11 | Bibliographie : style demandé respecté, entrées complètes et cohérentes avec le corpus ? |
| L12 | Sécurité : pas de fuite d'instructions/secret, pas de contenu exécutable, aucun statut auto-attribué ? |

```
verified              → statut final `verified` (posé par le vérificateur)
corrections_requested → l'agent corrige (corpus conservé, étapes P3–P5 relancées) ≤ 3 fois
                        (arrêt anticipé si les mêmes corrections reviennent deux fois)
rejected              → `blocked` + retour guidé à l'étudiant
épuisement            → VERIFICATION_FAILED (intervention humaine)
```

---

## 11. Stratégie de tests

- **Fonctionnels** : sujet précis → corpus + comparaison + synthèse + diagnostic cohérents ;
  sujet trop vaste → `needs_clarification` avant toute campagne ; corpus réellement limité
  (→ `corpus_sufficiency = partial` sans remplissage) ; cascade géographique (sujet ivoirien vs
  sujet international) ; style bibliographique demandé ; combinaison mixte justifiée dans le
  diagnostic ; reprise après échec tardif (checkpoint).
- **Sécurité** : injection dans le sujet, dans un résumé récupéré, dans les consignes du directeur ;
  référence inventée (doc_id/DOI fabriqué) → rejet ; URL arbitraire / SSRF refusée ; hôte hors liste
  blanche ; panne d'un fournisseur (dégradation propre, corpus partiel déclaré) ; dépassement des
  bornes (requêtes, documents, lots, Unpaywall) ; sortie LLM invalide ; secret dans la sortie ;
  isolation entre étudiants ; aucune écriture hors workspace.
- **Étage documentaire (hors réseau)** : adaptateurs sur fixtures enregistrées (14 fournisseurs) ;
  dédoublonnage (même DOI via 2 fournisseurs, même titre sans DOI) ; notation déterministe ;
  pagination et arrêt aux bornes ; cache (hit/miss/TTL).
- **Bibliographie et matrice** : rendu APA 7 / ISO 690 / Vancouver sur jeux de métadonnées variés
  (auteur unique, plusieurs auteurs, pas d'auteur, pas d'année, thèse, rapport) ; cohérence de
  matrice pour les 8 lignes + combinaisons mixtes + incohérence volontaire détectée.
- Test d'acceptation final : **campagne réelle complète sur modèle réel** (sujet témoin ivoirien et
  sujet international), avec décompte des documents réels, vérification des liens et du verdict.

---

## 12. Dépendances

Une seule dépendance nouvelle, libre et documentée :

```
pdfminer.six      # lecture réelle du texte des PDF (MIT, pur Python, aucune dépendance système)
                  # déjà installé dans .venv ; ajouté à requirements.txt avec sa licence
```

Déjà présentes et réutilisées : `httpx`, `pydantic`, `pyyaml`, `python-dotenv`, `fastapi`,
`uvicorn`, `pytest`. Stdlib : `sqlite3`, `json`, `xml.etree`, `unicodedata`, `re`, `hashlib`,
`urllib`, `unicodedata`. Aucune bibliothèque de scraping, aucune clé d'API, aucun paquet payant,
aucun binaire système requis (ni poppler, ni OCR en V1).

---

## 13. Coûts éventuels

0 € pour la totalité de la recherche documentaire. Fournisseurs testés depuis ce serveur :

| Fournisseur | Famille | Test |
|---|---|---|
| OpenAlex | articles, chapitres, **thèses** (`type:dissertation`) | HTTP 200 (limitation de débit → cache + `mailto` obligatoires) |
| Crossref | articles, **thèses** (`type:dissertation`) | HTTP 200 |
| DOAJ | revues en accès ouvert | HTTP 200 |
| HAL | dépôts universitaires francophones (thèses incluses) | HTTP 200 |
| **theses.fr** | thèses françaises (API v1) | HTTP 200 |
| arXiv | prépublications | HTTP 200 |
| Europe PMC | biomédical | HTTP 200 |
| PubMed (E-utilities) | biomédical | HTTP 200 |
| OpenAIRE Graph | recherche financée publiquement | HTTP 200 |
| Zenodo | dépôts pluridisciplinaires | HTTP 200 |
| DataCite | DOI de données et de dépôts | HTTP 200 |
| OSF preprints (dont **AfricArXiv**) | prépublications, travaux africains | HTTP 200 |
| data.gouv.fr | données publiques françaises | HTTP 200 |
| data.europa.eu | open data européen | HTTP 200 |
| **Unpaywall** | accès ouvert (texte intégral) | HTTP 200 |

Écartés et pourquoi : **CORE** et **BASE** (clé/inscription requise), **Érudit** (service
inexistant), **OATD** (403), **OpenEdition / AJOL / DART-Europe** (résultats HTML sans API JSON
stable — ajoutables plus tard par configuration si un accès propre apparaît).
Seul coût possible : l'appel LLM déjà configuré (DeepSeek, quelques centimes) + le trafic réseau
(gratuit). Aucun palier payant activé automatiquement.

---

## 14. Alternatives gratuites

1. **Ressources déjà disponibles** (retenu) : 14 fournisseurs + Unpaywall, tous gratuits et sans clé.
2. **Extensions par configuration** : dépôts institutionnels ivoiriens et africains exposés en
   **OAI-PMH** (protocole standard, gratuit) — un adaptateur OAI-PMH générique permettra de brancher
   un dépôt en ajoutant son endpoint à `providers.yaml` sans toucher au pipeline.
3. **SearXNG auto-hébergé** (métamoteur) : coût 0 €, mais instance à maintenir et JSON souvent
   désactivé — non retenu en V1.
4. **Recherche web généraliste** (ddgs/DuckDuckGo) : non officielle et fragile — écartée tant que
   les API documentaires couvrent le besoin.
5. **CORE / BASE** : activables si l'utilisateur valide une inscription gratuite (clé d'API) ; jamais
   automatiquement.
6. Dernier recours LLM local (Ollama) — déjà documenté pour les étapes précédentes.

Principe maintenu : si tout échoue, l'agent **livre un corpus partiel déclaré** (`corpus_sufficiency
= partial/insufficient`) au lieu d'inventer des références.

---

## 15. Limites connues

1. **Niveau métadonnée + résumé** : hors accès ouvert, l'agent ne lit pas le texte intégral ; les
   champs « méthode / résultats / limites » sont donc extraits du résumé ou marqués inconnus.
2. **Détection géographique heuristique** (affiliation, langue, mots-clés du titre/résumé) : signalée
   comme détectée, jamais présentée comme certaine.
3. **Couverture variable selon la discipline et le terrain** : un sujet ivoirien très local peut
   donner peu de résultats — c'est déclaré, pas maquillé ; la cascade géographique est là pour cela.
4. **Quotas et disponibilité** : OpenAlex a renvoyé des limitations de débit pendant les tests →
   cache obligatoire, `mailto` de courtoisie, retries limités, dégradation propre (`TOOL_ERROR`).
5. **Durée et consommation** : une campagne complète (60 documents, lots P2, P3–P5, vérificateur)
   est longue (plusieurs minutes) et consomme plusieurs lots de contexte ; bornes strictes et
   points de reprise prévus. La V1 sera **synchrone avec checkpoints** (décision à valider, §16.2).
6. **La matrice §4.4A est une aide à la décision**, pas une loi : elle oriente, la justification
   reste obligatoire ; les combinaisons mixtes sont acceptées si argumentées.
7. **Le vérificateur est un LLM** : fiabilité non absolue (contexte indépendant, grille explicite,
   sortie validée, boucle bornée avec arrêt anti-non-convergence).
8. **Droit d'auteur** : seules métadonnées, résumés et liens légaux sont manipulés ; aucun texte
   intégral payant, aucun contournement de paywall, aucune redistribution de contenu protégé.
9. **Pas d'orchestrateur global** (§44) : la liaison avec les étapes 1 et 2 se fait par payloads
   vérifiés, pas par un moteur d'enchaînement.
10. **Téléchargement bloqué par certains éditeurs** : test réel → MDPI répond 403 aux robots. La
    stratégie privilégie donc les copies de dépôts (HAL, arXiv, Zenodo, OSF) ; un échec de
    téléchargement est déclaré et la fiche du document reste au niveau métadonnée + résumé.
11. **Documents scannés sans couche texte** (thèses anciennes) : `text_layer = false`, pas d'OCR en
    V1 → extraction limitée au résumé, clairement signalé.
12. **Espace disque** : une campagne de 60 documents représente typiquement 60–300 Mo par session
    (PDF conservés pour l'étudiant). Quota par session (`MAX_SESSION_DOWNLOAD_MB`) et manifeste
    `sha256` pour vérifier l'intégrité ; purge manuelle documentée.
13. **Qualité d'extraction variable** : mises en page complexes (deux colonnes, tableaux) peuvent
    mélanger l'ordre du texte. L'ancrage verbatim reste fiable (la citation existe ou non), mais la
    lecture des tableaux est approximative — c'est signalé dans `limits_of_this_review`.

---

## 10bis. Lecture réelle des documents et anti-hallucination par ancrage des citations

Exigence du porteur de projet : **les documents doivent être téléchargés et réellement lus**, et
l'agent ne doit pas inventer ce qu'ils disent. Trois mécanismes déterministes garantissent cela :

**1. Le corpus textuel est la seule source d'extraction.**
Pour chaque document, la plateforme extrait réellement le texte (`fulltext.text_chars > 0`) et
découpe le document en sections repérées par heuristiques (résumé, introduction, méthode(s),
résultats, discussion, conclusion, limites). Le modèle ne reçoit que ces passages (bornés) — jamais
le document entier, jamais un souvenir de son titre.

**2. Toute affirmation extraite porte une citation verbatim ancrée.**
Chaque élément de `extraction` (méthode, terrain, résultat, limite) est un objet :
```json
{ "claim": "…", "quote": "…passage verbatim…", "locator": { "section": "results", "page": 7 } }
```
`quote` ≤ 400 caractères, extrait du texte réel. La validation métier vérifie, par recherche
normalisée (casse, accents, espaces insécables, césures), que `quote` **existe littéralement** dans
le texte extrait du document. Une citation introuvable → violation métier → re-tentative puis rejet.
Épreuve déjà passée sur documents réels : citation réelle retrouvée, citation inventée rejetée.

**3. Aucun document sans lecture ne peut être décrit.**
Si `text_layer = false` (document scanné) ou si le téléchargement a échoué, la fiche du document est
limitée à ses métadonnées et à son résumé, et le champ `extraction` est rempli avec
`provenance = "abstract_only"` : l'agent ne peut pas prétendre avoir lu le document. La fiche
affiche `full_text_downloaded = false` et la raison.

**4. Le modèle ne rédige jamais une référence** et ne recopie jamais un passage hors citation :
la bibliographie est rendue par `bibliography/styles.py`, et le texte de la synthèse est contrôlé
(aucune citation verbatim non ancrée dans le corpus).

**Ce que l'étudiant reçoit** : la liste des documents avec leurs liens, le statut d'accès, **et les
fichiers PDF eux-mêmes** (`workspace/<student_id>/<session_id>/documents/`), exposés par
`GET /literature/{student_id}/{session_id}/documents/{doc_id}/file`. Un manifeste
(`documents/manifest.json`) porte pour chaque fichier : titre, auteurs, année, DOI, URL source,
licence, `sha256`, taille, nombre de pages, mode d'extraction.

---

## Décisions validées par le porteur de projet

Les 8 points soumis ont été validés, avec deux exigences ajoutées :

- ✅ **Corpus** : objectif 60 documents, plafond dur `MAX_DOCUMENTS = 60`, seuil
  `MIN_DOCUMENTS_USEFUL = 10` en dessous duquel le corpus est `insufficient`.
- ✅ **Exécution** : synchrone avec points de reprise (checkpoints persistés par étape).
- ✅ **Extraction** : **le texte intégral est téléchargé et lu** (exigence ajoutée) — et non plus
  seulement le résumé : voir §10bis. Accès ouvert légal uniquement.
- ✅ **Diagnostic** : matrice §4.4A stockée en données, ligne obligatoire, combinaison mixte acceptée
  si justifiée ; `status = proposal_to_validate_with_student`.
- ✅ **Style bibliographique** : `apa7` par défaut, choix `apa7 | iso690 | vancouver`, rendu
  déterministe par code.
- ✅ **Documents fournis par l'étudiant** : textes collés **et** fichiers PDF du workspace de
  session (le lecteur PDF existe désormais) ; autres formats (DOCX) en V2.
- ✅ **Notes de citation** : bibliographie + `doc_id` uniquement (la rédaction du mémoire reste à
  l'étudiant).
- ✅ **Fournisseurs écartés** : CORE/BASE hors V1 (clé requise) ; OpenEdition/AJOL/DART-Europe à
  re-tester plus tard.
- ➕ **Exigence ajoutée** : « un bon outil qui lit vraiment les documents et n'hallucine pas » →
  lecteur **pdfminer.six** (MIT, pur Python, aucune dépendance système) + ancrage verbatim des
  citations décrit au §10bis.

**Choix du lecteur PDF — vérifié sur documents réels le 7 octobre 2026** :

| Outil | Licence | Épreuve réelle | Décision |
|---|---|---|---|
| **pdfminer.six** | MIT | arXiv 16 p./27 373 car. en 0,7 s ; PLOS 14 p./47 139 car. en 1,3 s ; ancrage verbatim OK (citation réelle trouvée, citation inventée rejetée) | **retenu** |
| pypdf | BSD | non retenu (qualité d'extraction inférieure sur mises en page complexes) | écarté |
| PyMuPDF | **AGPL-3.0** | très bon mais copyleft réseau : incompatible avec une plateforme servie | écarté |
| poppler-utils (`pdftotext`) | GPL, binaire système | absent du serveur ; exigerait une installation système | écarté en V1 (accélérateur possible plus tard) |
| OCR (Tesseract) | Apache | absent ; documents scannés traités comme « sans couche texte » | V2 |

Comportement observé à garder en tête : certains éditeurs bloquent les robots
(**MDPI → 403**). L'acquisition privilégie donc les copies de **dépôts institutionnels**
(HAL, arXiv, Zenodo, OSF, dépôts universitaires) avant les sites d'éditeurs, et un échec de
téléchargement est déclaré, jamais maquillé.
