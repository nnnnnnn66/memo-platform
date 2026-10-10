# Cahier des charges v1 — Plateforme web d'accompagnement méthodologique du mémoire

> **Statut** : proposition de rédaction par l'assistant, à corriger et valider par le porteur de
> projet. Ce document décrit **ce que la plateforme doit faire**, pas comment la coder.
> Il ne remet pas en cause la règle du projet : **un seul agent à la fois**. L'interface et
> l'orchestrateur ne seront construits qu'après validation explicite de cette spécification.

---

## 1. Objet et contexte

La plateforme accompagne un étudiant de Master dans la construction méthodologique de son mémoire
de recherche, **étape par étape**, en le questionnant et en détectant ses manques et incohérences.
Elle n'écrit pas le mémoire à sa place.

**Ce qui existe déjà** (vérifié en exécution réelle) :

| Élément | État |
|---|---|
| 11 agents (étapes 1 à 11), chacun avec son vérificateur | construits, testés, validés |
| Chaîne complète 1 → 11 sur sorties réelles | vérifiée (`verified`) |
| Tests hors réseau | 608+ |
| Commandes de lancement | `run-<agent>.sh`, un service HTTP par agent |

**Ce qui n'existe pas encore** : le site web, l'orchestrateur, l'authentification, l'accès public.

**Rappel fondateur** : Hermes est l'**environnement de construction**. Le produit est la plateforme.
L'étudiant ne doit jamais voir le terminal, Hermes, le serveur, ni un port technique.

---

## 2. Utilisateurs et rôles

| Rôle | Ce qu'il fait |
|---|---|
| **Étudiant** (utilisateur principal) | crée son dossier, avance étape par étape, répond aux questions, valide ou demande une révision |
| **Encadreur / porteur** | consulte l'avancement d'un étudiant, garde la main sur les décisions méthodologiques |
| **Administrateur** (le porteur) | gère les comptes, les quotas, surveille la consommation, sauvegarde |

> **À DÉCIDER PAR LE PORTEUR** : la plateforme est-elle ouverte à l'inscription libre, ou
> sur invitation ? Un étudiant peut-il avoir plusieurs mémoires ?

---

## 3. Périmètre fonctionnel

### 3.1 Les 13 étapes du parcours
Le parcours est celui du `README.md` du projet : Sujet → Problème → Revue de littérature →
Problématique → Question de recherche → Objectifs → Hypothèses → Orientation méthodologique →
Méthodologie → Résultats → Analyse/Discussion → Conclusion → Vérification globale de la cohérence.

**Une étape = un agent.** La plateforme présente **une étape à la fois** et n'ouvre la suivante
qu'après validation.

### 3.2 Ce que la plateforme doit offrir
1. **Compte étudiant** : inscription/connexion, un dossier par mémoire.
2. **Écran d'étape** : la plateforme affiche ce que l'agent demande à l'étudiant (questions,
   informations manquantes, champs à confirmer) et permet de répondre.
3. **Portillon humain** : à chaque étape, le résultat est **proposé**, jamais imposé. L'étudiant (ou
   son encadreur) **valide** ou demande une révision. `validated` ne vient **jamais** de l'agent.
4. **Dossier persistant** : tout est conservé par `student_id` / `session_id`, reprise possible à
   tout moment.
5. **Documents** : la revue de littérature télécharge des PDF d'accès ouvert ; l'étudiant doit
   pouvoir les **consulter et les télécharger** depuis la plateforme.
6. **Honnêteté visible** : ce qui reste **inconnu**, **non vérifié** ou **limité** doit être affiché
   à l'étudiant (jamais masqué).
7. **Export** : à la fin, télécharger le dossier complet (étapes, réponses, sources, validation).
8. **Vérification globale finale** (étape 13) : le vérificateur transverse vérifie la cohérence du
   dossier complet, et dit aussi **ce qu'il ne peut pas vérifier**.

### 3.3 Ce que la plateforme ne doit PAS faire
- Écrire le mémoire à la place de l'étudiant.
- Fusionner Sujet / Problème / Problématique / Question de recherche (règle absolue du projet).
- Inventer une donnée, une source ou un résultat (les calculs sont faits par le code, pas par le modèle).
- Laisser croire qu'un résultat est validé alors qu'il est seulement proposé.

---

### 3.4 Téléchargements offerts à l'étudiant (exigence explicite)

L'étudiant doit pouvoir **télécharger lui-même** les éléments de son travail, à tout moment :

| Ce qu'il télécharge | D'où cela vient | État technique |
|---|---|---|
| **Les documents scientifiques** (PDF réellement récupérés en accès ouvert) | Agent 3 — revue de littérature | ✅ déjà exposé : `GET /literature/{étudiant}/{session}/documents` (manifeste) puis `/…/{doc_id}/file` |
| **Le lien officiel** des documents non récupérables (payants, protégés) | Agent 3 | ✅ le manifeste indique l'accès et le lien officiel |
| **Sa bibliographie** en BibTeX, RIS ou CSV | Agent 3 | ✅ ajouté : `GET /literature/{étudiant}/{session}/bibliographie?format=bibtex|ris|csv` |
| **Le résultat d'une étape** (texte proposé, inconnues, limites, verdict) | chaque agent | ✅ chaque agent expose déjà sa sortie ; à **présenter** dans le site |
| **Son dossier complet** (les 13 étapes, réponses, sources, validations) | orchestrateur | à construire (agrégation) |

**Règles** :
- Un lien ne doit être annoncé **que s'il a été vérifié** (le fichier existe et s'ouvre réellement).
- Un document sans PDF récupérable doit **quand même** offrir son **lien officiel**, accompagné de la mention « texte intégral non récupéré » — jamais un lien mort, jamais un faux.
- Les fichiers d'un étudiant ne sont accessibles **qu'à lui** (isolation par compte).

> **À DÉCIDER PAR LE PORTEUR** : l'étudiant peut-il télécharger **tout son dossier d'un coup**
> (archive), ou élément par élément ?

---

## 4. Parcours utilisateur type

1. L'étudiant s'inscrit, crée « mon mémoire » (titre provisoire, discipline, niveau).
2. **Étape 1 — Sujet** : l'agent demande les informations manquantes (QUOI / QUI / OÙ / QUAND).
3. Il répond, relit la proposition, **valide** ou demande une révision.
4. L'étape 2 s'ouvre, et ainsi de suite jusqu'à l'étape 13.
5. À tout moment : voir son dossier, ses documents, ses inconnues.
6. À la fin : export du dossier complet + rapport de vérification globale.

---

## 5. Exigences non fonctionnelles

| Exigence | Détail |
|---|---|
| **Budget 0 €** | ressources existantes, puis gratuites, puis open source, puis locales. Aucun service payant activé automatiquement. |
| **Sécurité (OWASP LLM01-10)** | aucune sortie de modèle exécutée ou utilisée directement ; pipeline `LLM → Parser → Schéma → Métier → Sécurité` ; moindre privilège ; journalisation. |
| **Isolation des étudiants** | un étudiant ne voit **que** son dossier. Aucune fuite entre `student_id`. |
| **Secrets** | jamais dans le code ni dans les journaux ; les clés voyagent en **en-tête**, jamais dans une URL. |
| **Données personnelles** | consentement, anonymisation possible, durée de conservation à définir, hébergement maîtrisé. |
| **Transparence et honnêteté** | `not_verified`, inconnues et limites affichés tels quels. |
| **Traçabilité** | chaque étape conserve sa version, son verdict de vérificateur et la décision de l'étudiant. |
| **Sauvegardes** | sauvegarde régulière des dossiers et de la base, restauration testée. |

> **À DÉCIDER PAR LE PORTEUR** : durée de conservation des dossiers, et si un encadreur peut voir
> le dossier de son étudiant.

---

## 6. Architecture cible

```
Étudiant → Site web → Orchestrateur → Agent de l'étape → Vérificateur de l'agent
                                    → Résultat proposé → DÉCISION de l'étudiant → étape suivante
                                    → … → Vérificateur GLOBAL (étape 13)
```

**Ce qui existe (backend)** : 11 services FastAPI indépendants, un par étape, lançables par
`run-<agent>.sh`, avec pour chacun :
- `POST /<domaine>/analyze` — lance l'analyse de l'étape
- `GET /<domaine>/{student_id}/{session_id}` — relit le résultat enregistré
- `POST /<domaine>/{student_id}/{session_id}/decision` — enregistre la décision de l'étudiant
- `GET /health` — état du service

**Ce qui reste à construire** : le site web, l'orchestrateur, l'authentification, la passerelle.

> **À DÉCIDER PAR LE PORTEUR** : l'orchestrateur est-il un nouveau service (recommandé) ou un
> module du site web ? Le stockage reste-t-il en SQLite (simple, gratuit) ou passe-t-il à une base
> plus robuste ?

---

## 7. L'orchestrateur (le chef d'orchestre)

Son rôle, et rien d'autre :
1. Savoir **quelle étape** un étudiant peut faire maintenant.
2. Appeler le **bon agent**, avec la **sortie réelle** de l'étape précédente (le « pont » entre
   agents est déjà éprouvé : chaîne 1 → 11 vérifiée).
3. **Conserver** la sortie, son verdict de vérificateur et la décision de l'étudiant.
4. **Arrêter** la progression si un agent échoue, et l'expliquer en clair à l'étudiant.
5. Appliquer les **quotas** (voir §9) et refuser proprement en cas de dépassement.

---

## 8. Hébergement et accès (comment le rendre accessible)

Aujourd'hui les agents ne sont joignables que depuis le serveur. Il faut ajouter :

1. **Une adresse** : nom de domaine (payant, ~10-15 €/an) **ou** sous-donnée gratuite
   (DuckDNS, nip.io) pour une mise en ligne immédiate à 0 €.
2. **HTTPS** : certificat **gratuit** (Let's Encrypt) — indispensable : sans lui, mots de passe et
   travaux d'étudiants circuleraient en clair.
3. **Une passerelle** (Caddy ou nginx) : la **seule** chose exposée à Internet. Elle termine le
   HTTPS et route vers le site et l'orchestrateur. **Les 11 agents restent cachés derrière** et ne
   sont jamais joignables de l'extérieur.
4. **Comptes étudiants** : mot de passe haché, session, limitation du nombre de tentatives.
5. **Cloisonnement** : l'orchestrateur ne sert que le dossier du compte connecté.
6. **Exploitation** : sauvegardes, journalisation, supervision, alertes (déjà en place pour le solde).

> **À DÉCIDER PAR LE PORTEUR** : le nom de domaine souhaité et le nom public de la plateforme.

---

## 9. Coûts — le point critique

| Poste | Coût |
|---|---|
| Serveur (VPS existant) | déjà payé |
| Passerelle, HTTPS, base de données, sauvegardes | **0 €** (open source / gratuit) |
| Nom de domaine | 0 € (sous-domaine gratuit) ou ~10-15 €/an |
| **Appels au modèle (LLM)** | **payant, à l'usage — le vrai coût** |

**Conséquence à trancher maintenant, pas plus tard** : ouvrir la plateforme à plusieurs étudiants
consomme **le solde du porteur**. Trois stratégies possibles, compatibles entre elles :

1. **Quota par étudiant** (ex. N analyses par étape et par jour) — le plus simple à mettre en place.
2. **Clé personnelle** : chaque étudiant saisit sa propre clé de modèle — coût transféré, mais
   barrière à l'entrée pour un étudiant non technique.
3. **Groupe pilote fermé** (invitations, effectif limité) — recommandé pour commencer.

> **À DÉCIDER PAR LE PORTEUR** : combien d'étudiants au démarrage, et quelle stratégie de coût.

---

## 10. Livrables et mise en œuvre par phases

| Phase | Livrable | Prérequis |
|---|---|---|
| 0 | **Ce cahier des charges validé** | décisions du porteur (§2, §5, §6, §8, §9) |
| 1 | **Spécification du site web** (écrans, parcours, messages) + **architecture V1** (portillon §42) | phase 0 |
| 2 | **Orchestrateur** : enchaînement des étapes, état par étudiant, quotas | phase 1 |
| 3 | **Site web** : compte, écran d'étape, réponses, validation, documents, export | phase 2 |
| 4 | **Passerelle + HTTPS + comptes** : mise en ligne | phase 3 |
| 5 | **Vérification globale (étape 13)** intégrée au parcours | agents 1-11 + orchestrateur |
| 6 | **Pilote** avec un petit groupe, puis corrections | phase 4 |

**Règle maintenue** : un seul chantier à la fois, architecture présentée avant implémentation.

---

## 11. Critères d'acceptation (la plateforme est prête quand…)

1. Un étudiant crée un compte, fait les 13 étapes **sans jamais voir** de terminal, de port ou de JSON.
2. Chaque étape affiche : la proposition, ce qui reste **inconnu**, les limites, la question posée.
3. `validated` ne peut venir **que** d'une décision humaine.
4. Aucun étudiant ne peut lire le dossier d'un autre.
5. Tout est en **HTTPS** ; aucun secret n'apparaît dans une URL ou un journal.
6. Un dépassement de quota est **refusé proprement** et expliqué, sans jamais bloquer la plateforme.
7. Une panne d'un agent est expliquée en clair à l'étudiant, et n'efface pas son dossier.
8. La sauvegarde/restauration a été **testée** pour de vrai.

---

## Décisions attendues du porteur de projet (récapitulatif)

| # | Décision | Où |
|---|---|---|
| 1 | Inscription libre ou sur invitation ? | §2 |
| 2 | Un encadreur voit-il le dossier de son étudiant ? | §2, §5 |
| 3 | Durée de conservation des dossiers | §5 |
| 4 | Orchestrateur : service séparé ou module du site ? | §6 |
| 5 | Nom de domaine / nom public de la plateforme | §8 |
| 6 | Nombre d'étudiants au démarrage + stratégie de coût LLM | §9 |
