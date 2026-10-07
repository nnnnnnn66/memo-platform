# Architecture V1 — Agent Problématique & Construction Théorique (`problematization_agent` 1.0)

> Présentation exigée par la SPEC §42 (15 points). **Aucune implémentation n'a été faite.**
> Ce document attend la validation humaine avant toute ligne de code.
> Référentiel : `docs/spec-agent-04-problematique.md` (SPEC reçue).
> Éléments de l'agent : `docs/elements-agent-04-problematique.md` (profil Hermes
> `agent-problematique` + paquet prévu). **Cadre autonome** : aucun agent existant n'est modifié et
> aucun code n'est partagé avec eux.

---

## 1. Architecture

Un **pipeline de problématisation** en étapes, chacune suivie d'une validation déterministe et d'un
**contrôle d'ancrage** sur le corpus réellement fourni par l'étape 3. Le principe des agents
précédents est conservé : *aucune sortie LLM utilisée avant Parser → Schéma → Métier → Sécurité*, et
*le modèle ne déclenche jamais lui-même une requête réseau*.

```
ÉTUDIANT (sujet, problème de terrain, observations, consignes, style bibliographique)
   │
   ▼
[1] Input Controller          ── student_id/session_id + snapshots amont (sujet, problème, revue)
[2] Input Validation          ── contrat d'entrée, tailles, champs obligatoires
[3] Security Layer            ── entrées étudiantes + contenus documentaires = DONNÉES NON FIABLES
   │
   ▼
[4] PRÉ-CADRAGE (déterministe) ── prérequis SPEC §5 présents ? corpus revue VÉRIFIÉ disponible ?
   │     non → status `needs_clarification` + questions précises, AUCUNE rédaction lancée
   │     oui → suite
   ▼
[5] CHARGEMENT & INDEXATION DU CORPUS AMONT (déterministe, sans LLM)   ← matière première de l'ancrage
   │     corpus (documents réels) + textes intégralement lus (manifeste `documents/`) → index par doc_id
   │     découpage en sections repérées (résumé, intro, méthode, résultats, discussion, conclusion)
   ▼
[6] LLM P1 — CARTOGRAPHIE DU PROBLÈME RÉEL (le constat) : phénomène, population touchée, zone
   │        géographique, dysfonctionnement constaté + provenance (fourni / déduit / inconnu)
[7] LLM P2 — CONFRONTATION LITTÉRAIRE (l'état des savoirs) : modèles dominants, consensus,
   │        concepts, à partir des seuls documents du corpus amont
   │        CHAQUE affirmation porte une CITATION VERBATIM + son `doc_id`
[8] CONTRÔLE D'ANCRAGE (déterministe) ── la citation existe-t-elle réellement dans le texte ?
   │     citation non ancrée → RETIRÉE (jamais réparée) ; taux d'ancrage mesuré et déclaré
[9] LLM P3 — IDENTIFICATION DU PARADOXE / DU « GAP » (la rupture)
   │        classification : contextuelle | conceptuelle | empirique | méthodologique + justification
   │        ancrée (doc_id + citation)
[10] GAP CHECK (OUTIL DÉTERMINISTE, sans LLM)   ← vérifier que le gap n'a pas déjà été comblé
   │     API académiques gratuites sans clé (OpenAlex, Crossref) ; requêtes issues des concepts du
   │     gap, bornées, cache SQLite, hôtes en liste blanche. Aucun appel piloté par le modèle.
[11] LLM P4 — JUSTIFICATION SCIENTIFIQUE + ARGUMENTAIRE RÉDIGÉ SOURCÉ (premier jet de la note
   │        de problématisation) ; chaque affirmation théorique porte un `doc_id` + citation verbatim
[12] LLM P5 — QUESTION DE RECHERCHE (PROPOSITION) + OBJECTIFS (1 général + 2–3 spécifiques)
   │        champs DISTINCTS de la problématique, marqués `status = "proposed"` (transition)
[13] AMORCE D'ALIGNEMENT MÉTHODOLOGIQUE (déterministe : matrice) ── logique → type → approche →
   │        techniques ; cohérence avec le diagnostic de l'étape 3, ou divergence DÉCLARÉE
[14] Parser → Schéma → Métier → Sécurité   (sur CHAQUE sortie des étapes 6 à 13)
   │     contrôle d'ancrage : tout `doc_id` cité existe dans le corpus amont réel
   ▼
[15] VÉRIFICATEUR INDÉPENDANT (LLM séparé) ── contrôles L1–L12 ; sortie elle-même validée
   │     verified | corrections_requested (≤ MAX_VERIFICATION_RETRIES) | rejected
   ▼
[16] Persistance (note, gap, question candidate, objectifs, alignement) + audit + réponse HTTP
```

Points non négociables :
- **Moindre privilège** : `read: session_only` + recherche publique autorisée, `write:
  workspace_only`, `delete/deploy/send: false`.
- **Ancrage** : une affirmation théorique sans citation présente dans le texte réel ne franchit pas
  la validation métier ; un document mentionné hors corpus amont est rejeté.
- **Anti-fusion** : la problématique, la question de recherche candidate et les objectifs candidats
  sont trois champs distincts ; aucun n'est présenté comme la version validée de l'étape suivante.
- **Honnêteté** : un corpus amont partiel, un texte absent ou un gap check en échec sont **déclarés**,
  jamais masqués ni transformés en « gap confirmé ».
- **0 €** : gap check sur fournisseurs gratuits sans clé uniquement (voir §13).

---

## 2. Arborescence des fichiers

```
/root/memo-platform/
├── config/
│   └── settings-problematique.yaml        # propre à l'agent (LLM, bornes, chemins, sources, biblio)
├── docs/
│   ├── spec-agent-04-problematique.md              # SPEC reçue (déposée)
│   ├── architecture-agent-04-problematique-v1.md   # ce document
│   └── elements-agent-04-problematique.md          # fiche des 19 éléments
├── src/problematization_agent/            # paquet AUTONOME
│   ├── main.py                             # app FastAPI (lifespan, state)
│   ├── api/routes.py                       # POST /problematique/analyze, GET /problematique/{st}/{sess}, /health
│   ├── pipeline/
│   │   ├── input_controller.py             # session + snapshots amont
│   │   ├── input_validation.py             # contrat d'entrée, tailles
│   │   ├── prerequisites.py                # pré-cadrage SPEC §5 (étape [4], déterministe)
│   │   ├── security_layer.py               # balisage + scan des entrées ET des contenus amont
│   │   ├── campaign.py                     # orchestrateur, points de reprise
│   │   ├── corpus_loader.py                # étape [5] : index du corpus amont + sections
│   │   ├── problem_mapping_stage.py        # LLM P1 (cartographie du constat)
│   │   ├── confrontation_stage.py          # LLM P2 (état des savoirs) + ancrage (étape [8])
│   │   ├── gap_stage.py                    # LLM P3 (identification + classification du gap)
│   │   ├── gap_check_stage.py              # étape [10] : outil réseau borné (déterministe)
│   │   ├── justification_stage.py          # LLM P4 (justification + argumentaire rédigé)
│   │   ├── question_objectives_stage.py    # LLM P5 (question candidate + objectifs candidats)
│   │   ├── alignment_stage.py              # étape [13] : matrice d'alignement (déterministe)
│   │   ├── output_parser.py
│   │   ├── schema_validation.py
│   │   ├── business_validation.py          # ancrage, anti-fusion, cohérence gap/alignement, style
│   │   ├── security_validation.py
│   │   └── verifier.py                     # vérificateur indépendant
│   ├── anchoring/
│   │   ├── index.py                        # index texte par doc_id + sections repérées
│   │   └── quote_anchoring.py              # ancrage verbatim (citation existe dans le texte ?)
│   ├── theory/
│   │   └── matrix.py                       # matrice d'alignement méthodologique en DONNÉES
│   ├── sources/
│   │   ├── providers.yaml                  # fournisseurs + hôtes autorisés (gap check)
│   │   ├── registry.py                     # sélection des fournisseurs + liste blanche
│   │   ├── http.py                         # client borné (timeout, taille, requêtes polies)
│   │   ├── cache.py                        # cache SQLite des requêtes (14 j)
│   │   └── adapters/
│   │       ├── openalex.py crossref.py     # vérification « gap déjà comblé ? »
│   │       └── hal.py theses_fr.py openaire.py datacite.py doaj.py europepmc.py
│   │                                        #   fournisseurs gratuits de repli (429 OpenAlex)
│   ├── schemas/
│   │   ├── input.py problem.py gap.py question.py alignment.py output.py verifier.py
│   ├── core/
│   │   ├── config.py limits.py errors.py logging.py sessions.py security_rules.py
│   ├── storage/
│   │   ├── workspace.py                    # artefacts par session
│   │   └── audit.py                        # journal d'audit (SQLite)
│   └── llm/
│       ├── client.py                       # client LLM (clé héritée, budget, re-tentative)
│       └── prompts/
│           ├── p1_problem_mapping_system.md p2_confrontation_system.md p3_gap_system.md
│           ├── p4_justification_system.md p5_question_objectives_system.md
│           └── verifier_system.md
├── run-problematique.sh                    # port 8040
├── workspace/                              # audit-problematique.db, gap-check-cache.db, <student>/<session>/
└── tests/problematique/                    # fonctionnels, sécurité, ancrage, gap check, alignement
```

---

## 3. Rôle de chaque fichier (nouveaux éléments)

| Fichier | Rôle |
|---|---|
| `pipeline/prerequisites.py` | Vérifie les prérequis de la SPEC §5 : sujet exact, discipline, problème de terrain, et surtout **corpus de revue de littérature vérifié** (`upstream_literature.validation.verified = true`). Manque essentiel → `needs_clarification`, aucune rédaction lancée. Manque secondaire → valeur par défaut **déclarée**. |
| `pipeline/corpus_loader.py` | Construit l'**index d'ancrage** : pour chaque `doc_id` du corpus amont, métadonnées + texte intégral lu (si disponible) + sections repérées. Les `doc_id` sont repris **tels quels** (jamais renumérotés). |
| `anchoring/quote_anchoring.py` | Cœur anti-hallucination : `quote_is_anchored(doc_id, citation)` vérifie que la citation est un fragment **verbatim** du texte réel du document. Toute citation non ancrée est **retirée**, jamais réparée. Couvre le cas court (25–60 car.) — le bug « fail-open » de l'étape 3 est connu. |
| `pipeline/confrontation_stage.py` | LLM P2 : synthétise l'état des savoirs à partir des seuls documents du corpus amont ; chaque affirmation porte citation + `doc_id` ; l'ancrage est appliqué juste après (étape [8]). |
| `pipeline/gap_stage.py` | LLM P3 : met en évidence le paradoxe / la tension et **classe** la lacune (contextuelle / conceptuelle / empirique / méthodologique) avec des preuves ancrées. |
| `pipeline/gap_check_stage.py` | Étape [10] : outil déterministe — vérifie via API académiques gratuites si le gap a déjà été comblé. Requêtes dérivées des concepts du gap, bornées, cachées. Un échec réseau est **déclaré** (`gap_check = unavailable`), jamais interprété comme « gap confirmé ». |
| `pipeline/justification_stage.py` | LLM P4 : rédige la justification scientifique et le premier jet argumenté de la problématique, en s'appuyant exclusivement sur les documents ancrés. |
| `pipeline/question_objectives_stage.py` | LLM P5 : formule la question de recherche **candidate** et les objectifs **candidats**, champs distincts de la problématique et marqués `proposed`. |
| `theory/matrix.py` | Matrice d'alignement méthodologique stockée **en données** : indicateurs → logique → type de recherche → approche → techniques. Le pipeline vérifie la cohérence déclarée et la convergence avec le diagnostic de l'étape 3 (ou exige une divergence déclarée). |
| `sources/providers.yaml` | Fournisseurs du gap check déclarés en configuration (hôte autorisé, famille). Ajouter un fournisseur gratuit = éditer ce fichier. |
| `pipeline/business_validation.py` | Ancrage (chaque affirmation théorique → `doc_id` du corpus amont + citation présente), anti-fusion (problématique ≠ question ≠ objectifs ≠ sujet/problème), cohérence du gap avec la matrice et le diagnostic amont, style bibliographique respecté, `status` honnête. |

---

## 4. Flux des données

```
POST /problematique/analyze
  body: { student_id, session_id?, subject_text, research_problem, discipline, academic_level,
          country?, geographical_scope?, population?, field_observations?,
          research_question_draft?, student_notes?, supervisor_guidelines?, citation_style?,
          language_prefs?, upstream_subject?, upstream_problem?, upstream_literature,
          constraints? }
   │
   ├─ Input Controller → session ; snapshots amont acceptés SEULEMENT si `validation.verified`
   ├─ Input Validation → 422 INVALID_INPUT si non conforme
   ├─ Security Layer   → balisage non fiable (sujet, contexte, observations, consignes, documents)
   ├─ Pré-cadrage      → corpus revue non vérifié / prérequis manquants ?
   │                     → 200 `needs_clarification` + questions, FIN
   │
   ├─ Chargement & indexation du corpus amont (déterministe) → index d'ancrage
   ├─ LLM P1 → cartographie du problème        → Parser → Schéma → Métier → Sécurité
   ├─ LLM P2 → confrontation littéraire         → Parser → Schéma → Métier
   ├─ CONTRÔLE D'ANCRAGE (déterministe)         → citations non ancrées retirées + taux
   ├─ LLM P3 → gap classé + preuves             → Parser → Schéma → Métier
   ├─ GAP CHECK (déterministe, réseau borné)    → gap déjà comblé ? (déclaré, jamais supposé)
   ├─ LLM P4 → justification + note rédigée     → Schéma → Métier (ancrage global)
   ├─ LLM P5 → question candidate + objectifs   → Schéma → Métier (anti-fusion)
   ├─ Alignement (déterministe : matrice)       → logique/type/approche/techniques + cohérence amont
   ├─ Sécurité (toutes sorties)                 → rien d'exécutable, aucune URL arbitraire
   ├─ VÉRIFICATEUR INDÉPENDANT                   → verified | corrections_requested | rejected
   └─ Persistance + audit → 200 { statut, note, gap, question, objectifs, alignement, evidence }
```

---

## 5. Modèle de données

| Objet | Champs principaux | Remarques |
|---|---|---|
| `ProblemMapping` | `phenomene`, `population`, `zone`, `dysfonctionnement`, `provenance` | `provenance` ∈ {provided, inferred, unknown} ; rien d'inventé |
| `AnchoredStatement` | `text`, `doc_id`, `quote`, `section`, `anchored: bool` | `anchored` posé par le contrôle d'ancrage, pas par le modèle |
| `LiteratureConfrontation` | `modeles_dominants[]`, `consensus[]`, `divergences[]`, `statements[]` | Uniquement des documents du corpus amont |
| `Gap` | `type` ∈ {contextuelle, conceptuelle, empirique, methodologique}, `description`, `statements[]`, `gap_check` | `gap_check` ∈ {already_addressed, not_found, unavailable} |
| `Justification` | `texte`, `statements[]` | Fil argumentatif terrain ↔ littérature |
| `ProblematiqueNote` | `sections[]` (`probleme_reel`, `etat_des_savoirs`, `rupture`, `justification`, `argumentaire`), `texte_complet` | Livrable « note de problématisation » |
| `ResearchQuestionCandidate` | `question`, `type`, `status = "proposed"` | Champ **distinct** ; proposition de transition |
| `ObjectivesCandidate` | `general`, `specifics[2..3]`, `status = "proposed"` | Champ **distinct** |
| `MethodologicalAlignment` | `logic`, `research_type`, `approach`, `techniques[]`, `justification`, `upstream_coherence` | `upstream_coherence` ∈ {consistent, divergent, absent} |
| `Evidence` | compteurs : citations rédigées / ancrées / retirées, appels LLM, requêtes réseau, documents lus | Preuve d'honnêteté |
| `Validation` | `verified: bool`, `checks[]`, `limitations[]` | `verified` posé par le vérificateur uniquement |

---

## 6. Contrat d'entrée (SPEC §5)

| Champ | Type | Requis | Provenance |
|---|---|---|---|
| `student_id` | string | oui | fourni |
| `session_id` | string | non (généré) | fourni |
| `subject_text` | string | oui (ou `upstream_subject` vérifié) | fourni |
| `research_problem` | string | oui | fourni |
| `discipline` | string | oui | fourni |
| `academic_level` | enum | oui (défaut Master) | fourni |
| `country` / `geographical_scope` | string | non | fourni |
| `population` | string | non | fourni |
| `field_observations` | string | non | fourni (le constat de terrain) |
| `research_question_draft` | string | non | fourni (question provisoire de l'étudiant, s'il en a une) |
| `student_notes` / `supervisor_guidelines` | string | non | fourni (données non fiables) |
| `citation_style` | enum {APA7, ISO690, VW} | non (défaut APA7) | fourni |
| `language_prefs` | object | non | fourni |
| `upstream_subject` / `upstream_problem` | object | non | acceptés si `validation.verified = true` |
| `upstream_literature` | object | **oui** | corpus + synthèse + diagnostic de l'étape 3, accepté si `validation.verified = true` |
| `constraints` | object | non | bornes de session |

Taille maximale : 60000 caractères. Un `upstream_literature` non vérifié ⇒ `422` ou
`needs_clarification` (jamais de production non sourcée).

---

## 7. Contrat de sortie (SPEC §4)

```json
{
  "status": "ready_for_verification | needs_clarification | draft",
  "problem_mapping": { "phenomene": "...", "population": "...", "zone": "...",
                       "dysfonctionnement": "...", "provenance": "provided" },
  "literature_confrontation": {
    "modeles_dominants": [{ "text": "...", "doc_id": "...", "quote": "...", "section": "resultats", "anchored": true }],
    "consensus": [], "divergences": [], "statements": []
  },
  "gap": { "type": "conceptuelle", "description": "...",
           "statements": [ { "text": "...", "doc_id": "...", "quote": "...", "anchored": true } ],
           "gap_check": { "result": "not_found", "publications_recentes": [], "queries": 3 } },
  "justification": { "texte": "...", "statements": [] },
  "problematique_note": { "sections": [], "texte_complet": "..." },
  "research_question": { "question": "...", "type": "ou_rte", "status": "proposed" },
  "objectives": { "general": "...", "specifics": ["...", "...", "..."], "status": "proposed" },
  "methodological_alignment": { "logic": "inductive", "research_type": "...", "approach": "...",
                                "techniques": [], "justification": "...",
                                "upstream_coherence": "consistent" },
  "bibliography": [ { "doc_id": "...", "reference": "..." } ],
  "evidence": { "quotes_written": 0, "quotes_anchored": 0, "quotes_removed": 0,
                "llm_calls": 0, "network_requests": 0, "documents_read": 0 },
  "validation": { "verified": false, "checks": [], "limitations": [] }
}
```

Aucun champ de l'étape suivante n'est produit comme « validé » : `research_question` et `objectives`
sont explicitement `status = "proposed"`. Pas de fusion avec le sujet ni le problème.

---

## 8. Règles de sécurité (OWASP LLM01–10)

| Risque | Mitigation dans cet agent |
|---|---|
| LLM01 — Prompt injection | Sujet, observations, consignes et **contenus documentaires amont** traités comme DONNÉES NON FIABLES : balisés, scannés (motifs d'injection), jamais suivis comme instructions. |
| LLM02 — Insecure output handling | Aucune sortie LLM utilisée sans `Parser → Schéma → Métier → Sécurité` ; aucune exécution, aucun appel réseau déclenché par le modèle. |
| LLM03 — Supply chain | Dépendances figées et documentées, toutes gratuites/open source ; aucune installation automatique. |
| LLM04 — Data/model poisoning | Les documents amont proviennent d'un corpus vérifié et ancré ; un contenu non ancré n'entre pas dans la note. |
| LLM05 — Improper output handling | Sorties structurées uniquement ; les références bibliographiques sont **rendues par un module déterministe**, jamais écrites par le modèle. |
| LLM06 — Excessive agency | Moindre privilège : `read session_only`, `write workspace_only`, `delete/deploy/send = false` ; périmètre réseau limité au gap check (liste blanche). |
| LLM07 — System prompt leakage + **misinformation** | Zéro hallucination : aucune référence/statistique/lacune inventée ; ancrage verbatim obligatoire ; citation non ancrée retirée. |
| LLM08 — Vector/embedding weaknesses | Aucune base vectorielle en V1 (pas d'embedding) : surface supprimée. |
| LLM09 — Misinformation | Gap check déterministe (le gap est-il déjà comblé ?) + ancrage strict + déclaration des limites. |
| LLM10 — Unbounded consumption | Bornes : `max_input_size`, `max_output_tokens`, `max_external_requests`, `max_gap_check_queries`, `max_documents_read`, cache, garde anti-non-convergence, budget de tokens par campagne. |

Isolation par `student_id`/`session_id` : chaque session écrit dans
`workspace/<student_id>/<session_id>/` et rien d'autre.

---

## 9. Mécanisme de validation

Sur **chaque** sortie LLM (étapes [6] à [13]) :

1. **Parser** — extraction JSON stricte ; en cas de troncature (modèle raisonneur), **re-tentative**
   avec consigne de concision (budget large : `max_output_tokens` 16000).
2. **Schéma** — validation pydantic : types, énumérations (type de gap, logique), champs requis.
3. **Métier** — contrôles codés :
   - ancrage : chaque affirmation théorique → `doc_id` du corpus amont + citation **présente** ;
   - anti-fusion : problématique ≠ question ≠ objectifs ≠ sujet/problème (textes distincts) ;
   - classification du gap dans l'enum canonique, avec preuves ancrées ;
   - cohérence de l'alignement avec la matrice et le diagnostic de l'étape 3 ;
   - style bibliographique rendu par le module déterministe ;
   - `status` honnête ; `provenance` renseignée pour la cartographie du problème.
4. **Sécurité** — aucun contenu exécutable, aucune URL arbitraire, aucune tentative d'injection
   propagée depuis les documents.

Violations métier non bloquantes : re-tentative ; si des violations subsistent à la **dernière**
tentative, **lever** (jamais de sortie non conforme transmise au vérificateur).

---

## 10. Mécanisme de vérification (SPEC §10, §12)

**Vérificateur indépendant** (LLM séparé, prompt dédié, reçoit toutes les données étudiantes + le
corpus amont + la production) — contrôles **L1–L12** :

| Code | Contrôle |
|---|---|
| L1 | Ancrage : chaque affirmation théorique porte un `doc_id` du corpus amont ET une citation présente dans le texte réel. |
| L2 | Aucune référence, statistique, date ou lacune inventée ; aucun chiffre non fourni. |
| L3 | Anti-fusion : problématique / question de recherche / objectifs / sujet / problème = champs distincts ; la question et les objectifs sont marqués `proposed`. |
| L4 | Gap classé dans l'enum canonique et justifié par des preuves ancrées (pas de gap « de complaisance »). |
| L5 | Cartographie du problème traçable aux entrées étudiantes (`provenance = provided`) ; population/zone non inventées. |
| L6 | Confrontation littéraire : aucun document mentionné hors corpus amont ; les modèles cités existent. |
| L7 | Amorce d'alignement cohérente avec le diagnostic de l'étape 3, ou divergence explicitement déclarée et justifiée. |
| L8 | Question de recherche : unique, ouverte, directrice, découlant de l'argumentation ; non fusionnée avec la problématique. |
| L9 | Objectifs : 1 général + 2–3 spécifiques, mesurables ou explorables, alignés sur la question. |
| L10 | Style bibliographique respecté ; références rendues par le module déterministe. |
| L11 | Format : listes de chaînes normalisées (`corrections`/`flags`), statuts dans l'enum, `verification_status = not_verified` par défaut. |
| L12 | Honnêteté : limites déclarées (corpus insuffisant, textes non lus, gap check indisponible) ; aucun auto-`verified`. |

Verdict : `verified` | `corrections_requested` (≤ `MAX_VERIFICATION_RETRIES`) | `rejected`.
Si les mêmes corrections reviennent deux fois, la boucle s'arrête (pas de consommation de tours).
La sortie du vérificateur est elle-même validée en schéma/métier (format des listes normalisé
défensivement).

---

## 11. Stratégie de tests

| Niveau | Contenu |
|---|---|
| Unitaire / fonctionnel hors réseau | `tests/problematique/` : LLM simulé (JSON conformes **et** JSON dégradés) + corpus de fixtures (documents avec texte). Cartographie, confrontation, classification du gap, justification, question/objectifs, alignement. |
| Ancrage | Citation **réelle** acceptée ; citation **inventée courte** (25–60 car.) refusée ; citation longue partiellement présente refusée ; identifiants `doc_id` stables (aucune renumérotation). |
| Anti-fusion | Problématique / question / objectifs restent distincts ; aucune version « validée » de l'étape 5. |
| Gap check | Fournisseurs simulés : `not_found`, `already_addressed`, `unavailable` (échec réseau déclaré). Hôtes hors liste blanche refusés. |
| Sécurité | Injection dans un document amont non suivie ; sortie exécutable rejetée ; isolation par session. |
| Intégration | `POST /problematique/analyze` bout en bout avec upstream vérifié ; `needs_clarification` sans revue vérifiée. |
| **Réel** | Modèle réel + corpus amont réel (issu d'une campagne de l'étape 3) → jusqu'au verdict du vérificateur. Script hors dépôt, résultats reportés dans la section « État réel ». |

Nommage : module d'aide `tests/problematique/problematique_helpers.py` (pas `helpers.py` — collision
avec `tests/helpers.py`).

---

## 12. Dépendances

Toutes **gratuites / open source**, figées et documentées (aucune installation automatique) :
`fastapi`, `uvicorn`, `pydantic`, `httpx`, `pyyaml`, `pdfminer.six` (lecture du texte amont — même
dépendance qu'à l'étape 3, paquet autonome), `pytest` (tests). Aucune clé tierce : le gap check
n'utilise que des API publiques sans clé. Le LLM passe par la clé existante de `~/.hermes/.env`
(DeepSeek, déjà en place).

---

## 13. Coûts éventuels

| Poste | Coût |
|---|---|
| LLM (P1–P5 + vérificateur) | Clé DeepSeek déjà en place (budget projet 0 € ; tokens bornés par campagne). |
| Gap check (8 fournisseurs gratuits sans clé) | Gratuit, sans clé (voir §14). |
| Téléchargement / lecture | Aucun (les textes amont sont déjà dans l'espace de session de l'étape 3). |
| Stockage | Local, nul. |

**Total : 0 €.**

---

## 14. Alternatives gratuites

- Gap check : **huit** fournisseurs sans clé déclarés en configuration — OpenAlex, Crossref, HAL,
  theses.fr, OpenAIRE, DataCite, DOAJ, Europe PMC. Ajouter/retirer un fournisseur = éditer
  `sources/providers.yaml` (l'adaptateur correspondant existe déjà dans `sources/adapters/`).
- **OpenAlex renvoie 429 depuis ce serveur** : le quota quotidien gratuit est *partagé par toute
  l'adresse IP* et s'épuise (`x-ratelimit-remaining: 0`, réinitialisation à minuit UTC). La
  vérification ne dépend donc pas d'un seul fournisseur : les sept autres prennent le relais, la
  défaillance d'OpenAlex est **déclarée** (`providers_failed`), jamais interprétée comme une preuve
  d'absence. Repli de repli : une **clé OpenAlex gratuite** (quota propre) lève la limite partagée.
- **Requêtes en mots-clés joints par OR** : HAL, theses.fr, OpenAIRE, DataCite, DOAJ et Europe PMC
  appliquent un **ET** sur les requêtes multi-termes — une phrase, ou même deux mots, ne renvoie
  rien. La première requête est donc `mot1 OR mot2 OR …` (mots-clés du croisement sujet × gap) ; les
  fournisseurs à recherche libre (Crossref, OpenAlex) acceptent aussi les formulations en clair.
- **Pertinence déterministe** : une publication est retenue si son titre/revue contient au moins
  DEUX des mots-clés du gap (et non un ratio sur tous les mots du sujet, trop strict : il écartait
  des travaux réellement proches au profit de seuls titres longs de Crossref).
- **Clé OpenAlex (facultatif, 0 €)** : lue dans l'environnement sous `OPENALEX_API_KEY`
  (`~/.hermes/.env`), elle est envoyée en EN-TÊTE `Authorization: Bearer …` (jamais dans l'URL, qui
  est journalisée) et donne à la plateforme son propre quota (10× le budget anonyme). Jamais écrite
  en configuration ni dans les journaux.
- Aucune base vectorielle : l'ancrage se fait par recherche verbatim dans le texte, sans embedding.

---

## 15. Limites connues

1. **Dépendance forte à l'amont** : sans revue de littérature **vérifiée**, l'agent ne peut pas
   sourcer → `needs_clarification` (choix assumé : mieux vaut ne rien produire que produire non sourcé).
2. **Ancrage limité par les textes disponibles** : si un document du corpus n'a qu'un résumé
   (`abstract_only`), l'affirmation correspondante est retirée — perte de richesse déclarée.
3. **Gap check partiel** : les API gratuites ne couvrent pas tout ; `not_found` signifie « non trouvé
   dans ces sources », jamais « gap certain ». Toujours déclaré. Depuis ce serveur, OpenAlex (quota
   IP partagé) est en 429 : la vérification s'appuie sur les sept autres fournisseurs gratuits.
4. **Qualité = proposition** : la problématique reste une proposition à valider par l'étudiant et son
   directeur ; l'agent n'a jamais raison contre eux.
5. **Pas d'embedding/RAG vectoriel en V1** (SPEC §28) : l'accès aux documents passe par le texte réel,
   pas par une similarité sémantique.
6. **Chevauchement avec les étapes 5–6** : la question de recherche et les objectifs sont produits ici
   comme **propositions de transition**, pas comme livrables validés (voir décision D1).

---

## Décisions à valider par le porteur de projet (portillon §42)

- **D1 — Question de recherche & objectifs.** La SPEC (§3.8, §9.6–9.7) demande à l'agent 4 de
  formuler la question de recherche principale et les objectifs ; le parcours (`README.md`) en fait
  les étapes 5 et 6. Proposition retenue : l'agent 4 les produit en **sortie séparée, marquée
  `proposed`** (« proposition de transition »), distincte de la problématique — **sans** livrer la
  version validée de l'étape 5/6 (pas de fusion). Alternative : s'arrêter à la problématique et
  laisser toute la question aux étapes suivantes.
- **D2 — Enum du gap.** La SPEC §9.3 liste 3 types (contextuelle, conceptuelle, empirique) mais §3.5
  en mentionne 4 (+ méthodologique). Proposition : enum à **4 valeurs**.
- **D3 — Gap check réseau — CONTRESIGNÉ le 2026-10-07.** Étage déterministe de vérification du gap
  (huit fournisseurs gratuits sans clé : OpenAlex, Crossref, HAL, theses.fr, OpenAIRE, DataCite,
  DOAJ, Europe PMC). Note : OpenAlex renvoie `429` depuis ce serveur (quota gratuit **partagé par
  l'adresse IP**, réinitialisation à minuit UTC) ; la vérification ne repose donc pas sur lui seul,
  sa défaillance est déclarée. Une **clé OpenAlex gratuite** — lue dans l'environnement sous
  `OPENALEX_API_KEY` (`~/.hermes/.env`), jamais écrite en configuration — donne un quota propre et
  supprime cette limite.
- **D4 — Interface.** Route `POST /problematique/analyze`, port **8040**, `run-problematique.sh`.
- **D5 — Bibliographie.** Rendu **déterministe** (le modèle ne rédige jamais une référence), cohérent
  avec l'étape 3 ; à partir des seuls `doc_id` réellement cités.
