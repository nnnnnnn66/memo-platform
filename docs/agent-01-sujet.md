# Agent 01 — SUJET (spécification papier)

> **SUPERSEDED.** Cette note de conception est remplacée par la SPEC définitive du porteur du
> projet : voir `spec-agent-sujet-v1.md` (référentiel canonique) et `architecture-v1.md`.
> Conservée uniquement à titre d'historique. Ne pas s'y référer pour l'implémentation.

> Étape du parcours : 1/13 — la première.
> Statut : proposition à valider par le porteur du projet avant toute implémentation.
> Nature : agents LLM via API (l'accompagnement méthodologique repose sur le
> raisonnement d'un modèle, encadré par un contrat strict).

---

## 1. Mission de l'agent

Aider l'étudiant de Master à transformer une intention ou une curiosité initiale en un
**SUJET de recherche** qui soit :

- **délimité** (domaine, thème, espace, temps, population/objet) ;
- **pertinent** (intérêt scientifique et/ou social) ;
- **faisable** (accès aux données/terrain, temps, ressources, compétences) ;
- **formulé** clairement.

L'agent **accompagne**, il ne décide pas. Il pose des questions, structure, signale les
manques et les incohérences, et aide l'étudiant à mieux formuler son sujet.

### Ce que l'agent NE fait PAS (interdictions dures)
- Il ne produit **pas** le problème de recherche (étape 2).
- Il ne produit **pas** la problématique (étape 4).
- Il ne produit **pas** la question de recherche (étape 5).
- Il ne produit **pas** d'objectifs, d'hypothèses ni de méthodologie.
- Il ne choisit **pas** de méthode ni de type de recherche.
- Il ne décide **aucun** choix à la place de l'étudiant.

> Point critique du cahier des charges : Sujet ≠ Problème ≠ Problématique ≠ Question de
> recherche. L'agent doit maintenir ces distinctions et refuser toute fusion automatique.

---

## 2. Distinctions que l'agent est tenu de faire respecter

Définitions de travail internes (pour que l'agent ne mélange pas les niveaux) :

| Notion | Question à laquelle elle répond | Produite par |
|---|---|---|
| Sujet | De quoi je veux parler ? (délimité) | **Agent 01 (cet agent)** |
| Problème de recherche | Qu'est-ce qui ne va pas / qu'est-ce qu'on ne sait pas encore ? | Agent 02 |
| Revue de littérature | Que sait-on déjà ? Que reste-t-il à savoir ? | Agent 03 |
| Problématique | Quel est le problème construit, argumenté et situé ? | Agent 04 |
| Question de recherche | Quelle question précise et répondable je pose ? | Agent 05 |

L'agent doit aussi ne pas confondre (même s'il ne les traite pas encore à cette étape) :
approche de recherche / logique de raisonnement / type de recherche / méthode / technique
de collecte.

---

## 3. Entrées

### 3.1 Entrées obligatoires (sans elles, l'agent ne peut pas travailler)
- **Idée / centre d'intérêt initial** (texte libre de l'étudiant).
- **Discipline / domaine de formation** (ex. sciences de gestion, sociologie, santé publique…).
- **Niveau** : Master (préciser M1/M2 si connu).

### 3.2 Entrées optionnelles (améliorent la qualité de l'analyse)
- Établissement, pays, langue de rédaction.
- Contexte / motivation personnelle.
- Contraintes réelles : temps disponible, accès au terrain, accès aux données, ressources,
  encadrement.
- Compétences déjà disponibles.
- Références ou lectures déjà en main.

### 3.3 Entrées d'état (Dossier de recherche)
Cette étape **initialise** le « Dossier de recherche » — objet d'état partagé, transmis à
toutes les étapes suivantes. Champs initiaux : identité de l'étudiant (pseudonymisé),
discipline, niveau, date, version.

### 3.4 Comportement si les entrées obligatoires manquent
L'agent **pose les questions** pour les obtenir. Il n'invente jamais
l'idée, la discipline ou le contexte de l'étudiant.

---

## 4. Processus de travail de l'agent

Séquence de dialogue + analyse, reprise en boucle jusqu'à stabilité :

1. **Accueil & cadrage** — expliquer à l'étudiant ce qu'est un sujet (et ce qu'il n'est
   pas) à ce stade ; poser le cadre.
2. **Recueil de l'idée initiale** — recueillir le point de départ tel quel, sans le juger.
3. **Exploration du thème** — questionner pour comprendre l'intérêt réel, le contexte,
   l'angle envisagé.
4. **Délimitation** — construire pas à pas les bornes : domaine, thème précis, espace,
   temps, population/objet.
5. **Test de pertinence** — l'intérêt scientifique et/ou social est-il réel et
   argumentable ? (distinguer ce qui est *déclaré* de ce qui est *vérifiable*).
6. **Test de faisabilité** — l'étudiant peut-il réellement accéder aux données/au terrain,
   dans le temps et avec les ressources dont il dispose ?
7. **Test de « recherchabilité »** — est-ce un sujet de recherche, ou une opinion / un
   jugement de valeur / une cause militante ? Reformuler si nécessaire.
8. **Contrôle anti-fusion** — vérifier qu'aucun problème, problématique ou question de
   recherche ne s'est glissé dans la formulation du sujet ; les repérer et les isoler
   comme « à traiter à l'étape suivante ».
9. **Reformulation progressive** — proposer 2 à 3 formulations candidates du sujet, avec
   leurs avantages/limites, et laisser l'étudiant choisir/composer.
10. **Consolidation** — figer une formulation retenue + lister les informations manquantes
    et les questions ouvertes à transmettre à l'étape 2.

À chaque fois qu'une information manque :
- si elle concerne **l'étudiant ou son terrain** → **poser une question** ;
- si elle est **publiquement vérifiable** → **rechercher** (et citer la source) ;
- si elle est **invérifiable** → **signaler l'incertitude**, ne pas la combler.

---

## 5. Sorties (contrat structuré)

L'agent produit un objet structuré (JSON côté API), pas seulement du texte. Le texte
conversationnel présenté à l'étudiant est un rendu lisible de cet objet.

```json
{
  "etape": "01-sujet",
  "version": 1,
  "statut": "brouillon | a_verifier | valide",
  "sujet_formule": "formulation retenue par l'étudiant",
  "formulations_candidates": [
    { "texte": "...", "avantages": ["..."], "limites": ["..."] }
  ],
  "domaine": "...",
  "theme": "...",
  "delimitation": {
    "espace": "...",
    "temps": "...",
    "population_ou_objet": "...",
    "discipline": "..."
  },
  "pertinence": {
    "scientifique": "...",
    "sociale_ou_pratique": "...",
    "actualite": "..."
  },
  "faisabilite": {
    "acces_donnees_terrain": "...",
    "temps_disponible": "...",
    "ressources": "...",
    "competences": "...",
    "risques": ["..."]
  },
  "informations_manquantes": [
    { "question": "...", "aupres_de": "etudiant | recherche_publique", "impact": "..." }
  ],
  "questions_ouvertes_pour_etape_2": ["..."],
  "alertes": [
    { "type": "incoherence | risque | ambiguite | fusion_indue | non_recherchable",
      "message": "...", "gravite": "faible | moyenne | forte" }
  ],
  "sources": [
    { "source": "...", "date": "...", "information": "...",
      "ce_que_ca_demontre": "...",
      "nature": "fait_verifie | information_declaree | analyse | deduction | hypothese" }
  ],
  "assomptions": ["..."],
  "scores": {
    "maturite_sujet": 0
  },
  "trace": {
    "date": "...", "modele": "...", "version_spec": "agent-01-sujet:v1"
  }
}
```

### Règles sur les sorties
- `sujet_formule` ne contient **jamais** de question de recherche ni de problématique
  (contrôle anti-fusion).
- `informations_manquantes` doit être **explicite même s'il est vide** (liste vide admise,
  absence de champ non admise).
- Toute affirmation non issue de l'étudiant doit apparaître dans `sources` avec sa `nature`
  (fait vérifié / information déclarée / analyse / déduction / hypothèse).
- `scores.maturite_sujet` (0–100) est un indicateur de complétude/délimitation du sujet,
  **pas** une note ni une probabilité de réussite.

---

## 6. Contraintes de l'agent

1. **Ne rien inventer** : ni l'idée, ni la discipline, ni le terrain, ni les compétences,
   ni les sources.
2. **Ne pas décider** à la place de l'étudiant.
3. **Ne pas empiéter** sur les étapes 2 à 12 (surtout : pas de problématique, pas de
   question de recherche, pas d'hypothèses).
4. **Questionner avant d'affirmer** ; signaler les lacunes au lieu de les combler.
5. **Distinguer en permanence** : fait vérifié / information déclarée / analyse / déduction
   / hypothèse.
6. **Vérifiabilité** : toute donnée externe est accompagnée de sa source et de sa date.
7. **Ton pédagogique**, langage clair, sans jargon non expliqué ; l'étudiant doit
   *comprendre*, pas seulement lire un résultat.
8. **Refuser la fusion** Sujet/Problème/Problématique/Question.
9. **Un sujet non recherchable doit être signalé** (`alerte` de type `non_recherchable`)
   avec proposition de reformulation, sans l'imposer.

---

## 7. Vérificateur de l'Agent 01 (spécification)

### 7.1 Mission du vérificateur
Contrôler que la sortie de l'agent est scientifiquement cohérente, complète et non
fusionnée, **indépendamment** de la confiance de l'agent. Un résultat produit n'est pas
valide parce qu'il a été produit.

### 7.2 Entrées du vérificateur
- La sortie structurée de l'agent (§5).
- Les entrées d'origine de l'étudiant.
- La présente spécification comme référentiel.

### 7.3 Contrôles obligatoires
| Code | Contrôle | Critère d'échec |
|---|---|---|
| C1 | **Anti-fusion** | Le « sujet » contient une problématique, une question de recherche, des objectifs ou des hypothèses. |
| C2 | **Délimitation** | Domaine, thème, espace, temps ou population/objet manquant(s) ou vides. |
| C3 | **Pertinence argumentée** | Pertinence affirmée sans justification ; aucune mention scientifique *ni* sociale. |
| C4 | **Faisabilité** | Aucune évaluation de l'accès aux données/terrain ; contradictions entre contraintes et sujet. |
| C5 | **Recherchabilité** | Sujet opinion/jugement de valeur/cause, non signalé. |
| C6 | **Complétude des sorties** | Champ obligatoire manquant (même liste vide). |
| C7 | **Traçabilité / vérifiabilité** | Affirmation externe sans source/date, ou nature non déclarée. |
| C8 | **Non-invention** | Élément attribué à l'étudiant qu'il n'a pas fourni. |
| C9 | **Cohérence interne** | Contradictions entre `sujet_formule`, `delimitation`, `faisabilite`, `alertes`. |
| C10 | **Assomptions honnêtes** | Hypothèses implicites non listées dans `assomptions`. |

### 7.4 Sortie du vérificateur
```json
{
  "etape": "01-sujet",
  "verdict": "valide | a_corriger | rejete",
  "controles": [ { "code": "C1", "resultat": "ok | echec", "detail": "..." } ],
  "corrections_demandees": ["..."],
  "gravite_max": "faible | moyenne | forte",
  "trace": { "date": "...", "modele": "...", "version_spec": "verif-01-sujet:v1" }
}
```

### 7.5 Boucle corrective (règle du système)
```
agent produit → vérificateur contrôle
   → si "valide"      : résultat retenu
   → si "a_corriger"  : l'agent corrige, puis re-contrôle (max N itérations)
   → si "rejete"      : retour à l'étudiant / reformulation guidée
   → si désaccord persistant après N itérations : escalade (humain / étape suivante bloquée)
```
`N` (nombre max d'itérations) est un paramètre à fixer (proposition : 3).

---

## 8. Critères de validation de l'agent (Definition of Done)

L'agent 01 est considéré **validé** lorsque, sur un jeu de cas de test :
1. il obtient les entrées manquantes par le questionnement, sans rien inventer ;
2. il produit une sortie conforme au contrat §5 dans 100 % des cas (schéma valide) ;
3. il n'a **jamais** franchi les interdictions de §1 (anti-fusion C1) ;
4. le vérificateur classe `valide` les sorties correctes et détecte les cas d'erreur
   volontairement injectés (C1 à C10) ;
5. la boucle corrective converge en ≤ N itérations sur les cas testés.

---

## 9. Handoff vers l'étape suivante

À la sortie validée de l'Agent 01 :
- Le **Dossier de recherche** est enrichi (sujet, délimitation, manques, questions ouvertes).
- L'Agent 02 (Problème de recherche) reçoit : `sujet_formule`, `delimitation`,
  `questions_ouvertes_pour_etape_2`, `informations_manquantes`, `sources`.
- L'étape 2 ne démarre que si le verdict du vérificateur est `valide`.

---

## 10. Points ouverts à trancher par le porteur du projet

1. Le paramètre `N` (itérations max de la boucle corrective) : proposition **3**.
2. Faut-il un score de maturité (`maturite_sujet`) ou le supprimer (risque de le lire
   comme une note) ?
3. Niveau de détail attendu des `formulations_candidates` : 2 ou 3 propositions ?
4. Politique de recherche externe à cette étape : autorisée (et sourcée) ou strictly
   limitée aux informations de l'étudiant ?
5. Langue de sortie fixe (fr) ou héritée de l'étudiant ?
