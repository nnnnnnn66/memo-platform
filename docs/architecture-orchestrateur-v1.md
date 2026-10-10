# Architecture V1 — Orchestrateur de la plateforme (portillon §42)

> **À valider par le porteur de projet AVANT toute implémentation** (règle du projet, SPEC §42).
> Ce document ne code rien : il expose l'architecture en 15 points, les décisions à trancher et les
> limites connues. L'orchestrateur est la pièce qui rend les 11 agents utilisables par un étudiant,
> sans qu'il voie jamais un terminal, un port ou du JSON.

---

## Problème à résoudre

Les 11 agents sont des **services séparés** (ports 8020 à 8110), chacun ignorant les autres. Un
étudiant ne peut pas :
- savoir **quelle étape** il peut faire maintenant ;
- faire circuler la **sortie réelle** d'une étape vers la suivante ;
- **valider** une étape (décision humaine) ;
- reprendre son dossier plus tard ;
- être protégé d'une **consommation illimitée** de tokens.

L'orchestrateur fait exactement cela — et **rien d'autre**.

---

## 1. Architecture

```
Étudiant → (site web, plus tard) → ORCHESTRATEUR → agent de l'étape (HTTP local)
                                                 → vérificateur de l'agent
                                ← résultat proposé → DÉCISION de l'étudiant
                                                 → étape suivante
                                                 → … → vérificateur GLOBAL (étape 13)
```

L'orchestrateur est un **service unique**, distinct des agents :
- il **n'appelle pas** un modèle de langage lui-même (aucun prompt propre) ;
- il ne contient **aucune** logique méthodologique (elle est dans les agents) ;
- il **n'écrit pas** de texte pour l'étudiant, il présente ce que les agents produisent.

## 2. Arborescence prévue

```
src/orchestrator/
  main.py            # point d'entrée (service HTTP)
  api/routes.py      # endpoints exposés à la plateforme
  core/
    config.py        # bornes, ports des agents, quotas
    errors.py        # erreurs propres (étape impossible, agent indisponible, quota)
  pipeline/
    chain.py         # ordre des étapes, étape suivante autorisée
    call_agent.py    # appel HTTP d'un agent (jamais de LLM ici)
    checkpoint.py    # lecture/écriture de l'état du dossier
    quota.py         # comptage et refus des dépassements
    handoff.py       # pont réel sortie d'une étape → entrée de la suivante
  storage/
    state.py         # état par étudiant/session (SQLite, comme les agents)
  schemas/
    dto.py           # contrats d'entrée/sortie de l'orchestrateur
run-orchestrateur.sh
config/settings-orchestrateur.yaml
tests/orchestrateur/
```

## 3. Rôle de chaque fichier

| Fichier | Rôle |
|---|---|
| `chain.py` | **source de vérité de l'ordre des étapes** (1 → 13) et de la condition d'ouverture de la suivante |
| `call_agent.py` | appel HTTP **local** (`127.0.0.1:80xx`), délai borné, aucune clé transmise à l'étudiant |
| `handoff.py` | transforme la sortie d'une étape en entrée de la suivante — **le point de bugs déjà rencontré** (un décalage de structure passe inaperçu) |
| `checkpoint.py` | sauvegarde le résultat, le verdict et la décision ; permet la reprise |
| `quota.py` | compte les analyses par étudiant et par jour, refuse proprement au-delà |
| `state.py` | état durable par `student_id`/`session_id` |
| `routes.py` | API **interne** de l'orchestrateur (consommée par le site web, jamais par l'étudiant directement) |

## 4. Flux des données

1. La plateforme demande : « où en est l'étudiant X ? »
2. L'orchestrateur lit l'état → **étape courante** et **statut** (à faire / en attente de décision / validée).
3. L'étudiant lance l'étape → l'orchestrateur vérifie le **quota** puis appelle l'agent.
4. L'agent répond : résultat **proposé** + verdict de son vérificateur.
5. L'orchestrateur **enregistre** et renvoie : proposition, inconnues, limites, questions.
6. L'étudiant **décide** (valider / demander une révision) → décision enregistrée.
7. Seule une **validation humaine** ouvre l'étape suivante.
8. À l'étape 11 passée, l'orchestrateur peut appeler le **vérificateur global (étape 13)**.

## 5. Modèle de données (état du dossier)

| Champ | Sens |
|---|---|
| `student_id`, `session_id` | identité du dossier (déjà utilisée par les 11 agents) |
| `etape_courante` | 1 → 13 |
| `etapes[]` | par étape : statut, date, verdict du vérificateur, décision de l'étudiant |
| `inconnues[]`, `limites[]` | remontées par les agents, **conservées telles quelles** |
| `analyses_du_jour` | compteur de quota (par date) |
| `journal[]` | trace des appels (étape, durée, succès/échec) — sans secret |

## 6. Contrat d'entrée

- Créer/ouvrir un dossier : `student_id`, `session_id`, sujet et contexte (fournis par l'utilisateur).
- Lancer l'étape courante : aucun paramètre (l'orchestrateur sait quoi faire).
- Enregistrer une décision : `valider` | `demander_revision` (+ commentaire libre).
- Consulter : état + résultat de l'étape courante + dossier complet.

## 7. Contrat de sortie

- **Où en est l'étudiant** : étape, statut, et ce qui bloque s'il y a blocage.
- **La proposition de l'étape** : texte, inconnues, limites, questions pour l'étudiant, verdict du vérificateur.
- **Jamais** `validated` sans décision humaine.
- **Les erreurs en clair** : « l'étape 3 n'a pas pu aboutir : le fournisseur X n'a pas répondu ; voici ce qui est possible » — jamais un code technique.

## 8. Règles de sécurité (OWASP LLM01-10)

- L'orchestrateur **n'exécute jamais** une sortie de modèle : il la transmet.
- **Isolation** : un dossier n'est accessible que par son propriétaire (vérification à chaque appel).
- Les agents sont appelés en **local** (`127.0.0.1`) : aucun port d'agent exposé à Internet.
- **Aucun secret** ne traverse l'orchestrateur ni n'apparaît dans une réponse ou un journal.
- **Quota** = protection du portefeuille du porteur (voir §9 du cahier des charges).
- Toute entrée est validée avant d'être transmise à un agent (taille, type).

## 9. Mécanisme de validation

- Refus par défaut : une étape inconnue, un dossier inexistant ou une décision hors vocabulaire est **rejeté**.
- Une étape ne peut être lancée que si la précédente est **validée** par l'humain.
- Le quota est vérifié **avant** l'appel à l'agent (jamais après coup).

## 10. Mécanisme de vérification

Chaque agent a **déjà** son vérificateur (ne pas en ajouter un second). L'orchestrateur :
- conserve le verdict de l'agent et **ne le réécrit jamais** ;
- refuse de déclarer une étape « terminée » si le verdict n'est pas `verified` ;
- signale à l'étudiant les **signalements (flags)** sans les masquer ;
- en fin de parcours, appelle le **vérificateur global (étape 13)** sur le dossier complet.

## 11. Stratégie de tests

- **Hors réseau, hors modèle** : enchaînement des étapes, refus d'étape non autorisée, quota dépassé, agent indisponible, dossier d'un autre étudiant (doit échouer), décision invalide.
- **Pont réel entre étapes** (leçon du projet) : rejouer les **sorties réelles** enregistrées des 11 agents et vérifier que chacune arrive intacte à l'étape suivante.
- **Test de bout en bout** avec les agents réellement lancés, sur un dossier témoin.

## 12. Dépendances

- Python + FastAPI (déjà utilisé), bibliothèque HTTP standard.
- SQLite (déjà utilisé par les agents).
- **Aucune** nouvelle dépendance payante.

## 13. Coûts éventuels

- **0 €** pour l'orchestrateur lui-même.
- Le coût reste **les appels au modèle des agents** — d'où le quota (§8).

## 14. Alternatives gratuites

- Pas d'orchestrateur dédié : un module dans le site web (moins clair, à éviter).
- File d'attente externe type Redis/Celery : **écartée** en V1 (dépendance et complexité inutiles pour un service séquentiel).
- Exécution synchrone (l'étudiant attend) en V1 ; asynchrone seulement si nécessaire.

## 15. Limites connues

- Les agents restent **séquentiels** : pas de parallélisme en V1.
- L'orchestrateur ne juge **pas** la qualité méthodologique : il transporte et applique les règles de progression.
- Il dépend de la **disponibilité de chaque agent** : un agent arrêté bloque l'étape (et doit le dire clairement).
- Le quota protège le portefeuille, il ne **mesure** pas finement la consommation réelle par appel.
- **Non traité ici** : le site web, l'authentification, la passerelle HTTPS (phases suivantes du cahier des charges).

---

## Décisions attendues du porteur de projet

| # | Décision | Proposition par défaut |
|---|---|---|
| 1 | L'orchestrateur est-il un **service séparé** ? | oui (recommandé) |
| 2 | Les agents sont-ils appelés **en local** (`127.0.0.1`) ? | oui |
| 3 | **Quota** par étudiant (analyses/jour) — valeur ? | 20/jour, à ajuster |
| 4 | En cas d'échec d'un agent : **réessai automatique** ou arrêt et message ? | arrêt + message clair |
| 5 | L'étudiant peut-il **revenir** sur une étape validée ? | oui, avec nouvelle décision tracée |

## Ce qui reste à faire après validation de ce document

1. Implémenter `src/orchestrator/` (paquet autonome, comme les agents).
2. Tests hors réseau + **pont réel** sur les sorties des 11 agents.
3. Campagne réelle de bout en bout sur un dossier témoin.
4. Puis seulement : le site web, puis la mise en ligne (HTTPS + comptes).
