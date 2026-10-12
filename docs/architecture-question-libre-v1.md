# Architecture — Question libre de l'étudiant (V1)

> **Portillon §42.** Ce document présente la conception AVANT implémentation, comme l'exige
> `AGENTS.md`. Il décrit ce qui est proposé, ce qui est différé, et la décision qui revient au
> porteur de projet.

## 1. Le besoin, dit par le porteur

> « Quand l'étudiant est sur l'espace de travail il peut poser une question quelconque, c'est
> maintenant à l'orchestrateur d'examiner et de savoir à qui il doit envoyer la question, afin
> d'avoir une bonne expérience utilisateur. »

## 2. Le principe : l'orchestrateur est le seul à connaître la carte

L'étudiant ne connaît pas les agents — et ne doit pas les connaître. Il écrit une phrase ; c'est
l'orchestrateur qui :

1. **examine** la question,
2. **désigne** l'étape (et donc l'agent) responsable,
3. **le dit** à l'étudiant.

Rien de nouveau architecturalement : c'est exactement le rôle que l'orchestrateur tient déjà pour
les passations (il est le seul intermédiaire, les agents ne se parlent jamais).

## 3. Découpage en deux phases — et pourquoi

### Phase A — le ROUTAGE (cette livraison)

L'orchestrateur **désigne** l'étape responsable, de façon **déterministe** : un vocabulaire par
étape (expressions + mots), une normalisation du texte (minuscules, sans accents), un score, une
confiance annoncée. Il restitue ensuite à l'étudiant **ce que son dossier contient déjà** sur cette
étape (proposition, inconnues, questions ouvertes, signalements).

**Pourquoi déterministe et non un modèle de langage ?**
- l'orchestrateur a une propriété documentée : **il n'appelle aucun modèle de langage** ;
- le budget est de **0 €** et le quota de l'étudiant doit rester réservé à la production ;
- une règle est **explicable** : on peut montrer à l'étudiant *pourquoi* la question a été
  rattachée à cette étape (les mots qui ont fait basculer le choix) — un modèle, non ;
- c'est **instantané** et sans risque d'injection : aucun texte de l'étudiant n'est interprété
  comme une instruction, il est seulement comparé à un vocabulaire.

**Limite assumée et annoncée :** la phase A ne *répond* pas encore à la question. Elle dit
**quelle étape la porte** et **ce qui existe déjà**.

### Phase B — la RÉPONSE (à valider séparément)

Pour qu'un agent réponde *à une question posée sur son étape*, il lui faut une capacité qu'aucun
agent n'a aujourd'hui : une route d'interrogation (`/…/question`), qui reçoive la question **plus**
la production de son étape, et réponde en se limitant à son périmètre.

**Ce que cela implique — et c'est pour cela que je m'arrête ici :**
- aucun agent n'a de socle commun : chaque paquet est autonome. La capacité devrait être ajoutée
  **12 fois**, ou bien introduire un socle partagé ;
- l'`AGENTS.md` impose **un seul agent à la fois** et la **validation humaine avant implémentation
  importante** : toucher 12 agents validés est exactement ce que cette règle protège ;
- chaque réponse d'agent devra passer par `Parser → Schema validation → Business validation →
  Security validation` (OWASP LLM01–10) et consommer du quota.

**Décision demandée au porteur :** où doit vivre la réponse ?
- **(a)** dans chaque agent (route d'interrogation ajoutée aux 12 — le plus fidèle à
  « l'orchestrateur envoie la question à l'agent », le plus lourd) ;
- **(b)** dans un service d'interrogation unique, appelé par l'orchestrateur, qui détient le
  contexte du dossier et répond en attribuant la réponse à l'étape (un composant de plus, mais une
  seule implémentation, un seul prompt, un seul jeu de tests) ;
- **(c)** rien pour l'instant : on reste en phase A.

## 4. Contrat HTTP (phase A)

```
POST /dossiers/{etudiant}/{session}/question
{ "question": "Mon échantillon de 12 personnes suffit-il ?" }
```

Réponse :

```json
{
  "question": "Mon échantillon de 12 personnes suffit-il ?",
  "etape": 9, "position": 9, "libelle": "Méthodologie", "agent": "methodology_agent",
  "confiance": "haute", "methode": "mots-cles",
  "indices": ["echantillon"],
  "autres_etapes": [{"numero": 8, "libelle": "Orientation méthodologique"}],
  "extrait": { "statut": "proposee", "verdict": "…", "inconnues": [], "questions": [] },
  "message": "Ta question relève de l'étape 9 — Méthodologie. Voici ce que ton dossier
              contient déjà sur ce point."
}
```

- Aucune trace n'est écrite : la phase A est **sans effet de bord** (elle ne modifie ni le dossier,
  ni le quota, ni le journal).
- Question trop courte, vide ou trop longue → refus explicite, jamais d'invention.
- Aucun rattachement trouvé → `etape: null` et un message qui **le dit** au lieu de deviner.

## 5. Ce qui est explicitement HORS de cette livraison

- Répondre à la question (phase B).
- Conserver l'historique des échanges.
- Toute modification d'un agent existant : **aucun agent n'est touché par la phase A.**
