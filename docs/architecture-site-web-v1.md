# Architecture V1 — Site web de la plateforme (portillon §42)

> **À valider par le porteur AVANT toute implémentation.** 15 points, puis les décisions et les
> limites. Ce document suit la spécification `docs/spec-site-web.md`.

---

## 1. Architecture

```
Étudiant (navigateur)
     │  HTTPS
     ▼
PASSERELLE (Caddy)              ← seule chose exposée à Internet
     │  127.0.0.1
     ▼
SITE WEB (FastAPI + gabarits HTML)   ← comptes, sessions, écrans, formulaires
     │  127.0.0.1:8000
     ▼
ORCHESTRATEUR                        ← parcours, portillon humain, quota, registre
     │  127.0.0.1:8010 … 8130
     ▼
LES 12 AGENTS
```

**Règle structurante** : le site **ne connaît pas** les agents. Il ne parle qu'à l'orchestrateur.
C'est ce qui permet d'ajouter/remplacer un agent sans toucher au site.

## 2. Arborescence prévue

```
src/site_web/
  main.py                 # serveur FastAPI du site
  core/config.py          # bornes, adresse de l'orchestrateur, durée de session
  core/securite.py        # mots de passe (stdlib scrypt), jetons de session, CSRF
  storage/comptes.py      # comptes, invitations, sessions (SQLite)
  clients/orchestrateur.py# SEUL point de contact avec l'orchestrateur (HTTP local)
  vues/                   # les 8 écrans (gabarits HTML)
  static/                 # une feuille de style, aucune dépendance externe
templates/
run-site.sh
config/settings-site.yaml
tests/site_web/
```

## 3. Rôle de chaque fichier

| Fichier | Rôle |
|---|---|
| `clients/orchestrateur.py` | **unique** porte vers le parcours : créer un dossier, lancer l'étape, décider, lire l'état, télécharger. Aucun autre module n'appelle l'extérieur. |
| `core/securite.py` | hachage des mots de passe (`hashlib.scrypt`, bibliothèque standard), jetons de session, protection CSRF |
| `storage/comptes.py` | invitations, comptes, sessions — SQLite |
| `vues/` | un gabarit par écran ; **aucune** logique métier dans les gabarits |
| `static/` | une seule feuille de style, écrite à la main (aucun CDN : 0 € et fonctionne hors ligne) |

## 4. Flux des données

1. L'étudiant se connecte → **session serveur** (jeton aléatoire en cookie `HttpOnly; Secure`).
2. Il ouvre son mémoire → le site demande l'état à l'orchestrateur → affiche l'étape ouverte.
3. Il clique **« Lancer cette étape »** → le site appelle l'orchestrateur (qui vérifie quota et
   disponibilité de l'agent, appelle l'agent, enregistre) → réaffiche la page.
4. Il lit la proposition, **inconnues**, limites, questions, verdict.
5. Il clique **« Je valide »** → l'orchestrateur enregistre la décision → l'étape suivante s'ouvre.
6. Il télécharge un document ou sa bibliographie → le site **relaie** le fichier de l'agent.
7. Il exporte son dossier → le site assemble les 13 étapes en un fichier.

## 5. Modèle de données (comptes)

| Table | Contenu |
|---|---|
| `invitations` | jeton, e-mail, créée le, **utilisée le** (usage unique) |
| `comptes` | identifiant, e-mail, **empreinte** du mot de passe (jamais le mot de passe), sel, créé le |
| `sessions` | jeton, compte, créée le, dernière activité, expiration |
| `journal_site` | événements lisibles (connexion, étape lancée, décision, téléchargement) |

Le dossier méthodologique lui-même **n'est pas** ici : il appartient à l'orchestrateur.

## 6. Contrat d'entrée / sortie

- **Entrée** : formulaires HTML (connexion, création de mémoire, réponse aux questions, décision).
  Toute entrée est validée avant d'être transmise (taille, type, champs inconnus refusés).
- **Sortie** : pages HTML rendues côté serveur. L'étudiant ne reçoit **jamais** de JSON brut.
- Le site **ne réécrit jamais** ce que l'orchestrateur renvoie : il l'affiche.

## 7. Règles de sécurité (OWASP LLM01-10)

- **Aucune sortie de modèle exécutée ou interprétée** : elle est affichée en texte échappé.
- **Isolation** : chaque requête est liée au compte connecté ; un étudiant ne peut demander que
  **ses** dossiers (contrôle côté serveur, jamais côté navigateur).
- **Mots de passe** : `hashlib.scrypt` (bibliothèque standard, aucun service externe), sel unique.
- **Sessions** : jetons aléatoires, cookie `HttpOnly` + `Secure` + `SameSite`, expiration.
- **Anti-forçage** : limitation du nombre de tentatives de connexion (repris du lab : le test 401).
- **CSRF** : jeton par formulaire.
- **Secrets** : jamais dans une page, une URL ou un journal ; les clés LLM restent chez les agents.
- **En-têtes** : `Content-Security-Policy` stricte (aucun script externe), `X-Frame-Options: DENY`.

## 8. Mécanisme de validation

- Formulaire non valide → la page est réaffichée avec un message, **rien n'est envoyé** à
  l'orchestrateur.
- Une décision ne peut porter que sur l'étape **en attente** : le site ne propose pas les boutons
  si ce n'est pas le cas (et l'orchestrateur le refuse de toute façon).

## 9. Mécanisme de vérification

Le site n'a **pas** de vérificateur propre — il n'en a pas besoin :
- le verdict du vérificateur **de l'agent** est affiché tel quel, sans reformulation ;
- le verdict du **vérificateur global** (étape 13) est affiché de même ;
- le site **ne peut pas** marquer une étape validée : seul l'orchestrateur le fait, sur un clic.

## 10. Stratégie de tests

- **Hors réseau, hors modèle** : connexion, isolation entre deux comptes, invitation à usage unique,
  CSRF, quota affiché, messages d'erreur en français, aucun jargon dans les pages.
- **Avec un orchestrateur simulé** : chaque écran, chaque cas d'erreur, chaque téléchargement.
- **Test d'acceptation réels** (étape 5 du plan) : parcours complet joué par un vrai dossier.

## 11. Dépendances

- `fastapi`, `uvicorn`, `jinja2` (gabarits) — déjà présentes dans l'environnement du projet.
- **Aucun** framework JavaScript, **aucun** CDN, **aucun** service externe.
- Base SQLite (bibliothèque standard).

## 12. Coûts

- **0 €** : site, passerelle, certificat (Let's Encrypt), base, sauvegardes.
- Seul coût : le **nom de domaine** (~10-15 €/an), et les appels aux modèles (déjà bornés par le
  quota).

## 13. Alternatives gratuites écartées

| Alternative | Pourquoi écartée |
|---|---|
| Application à page unique (React/Vue) | chaîne de construction, dépendances, complexité inutile pour 8 écrans |
| Hébergement externe gratuit | sortirait les dossiers des étudiants du serveur maîtrisé |
| Authentification par service tiers (OAuth) | dépendance externe, données chez un tiers, hors budget 0 € |
| Tunnel type ngrok pour exposer | URL changeante, non maîtrisée — écarté au profit de Caddy + domaine |

## 14. Limites connues

- Rendus **côté serveur** : chaque action recharge la page (choix assumé : simplicité, robustesse).
- **Un seul serveur** : pas de haute disponibilité (acceptable pour un pilote).
- **Pas d'encadreur** au démarrage (décision du porteur).
- La vérification globale (étape 13) peut être **longue** : le site doit afficher une attente
  explicite plutôt que de laisser croire à une panne.
- Le site dépend de l'orchestrateur : s'il est arrêté, le site le **dit** clairement.

## 15. Livrables et ordre de mise en œuvre

| # | Livrable | Contenu |
|---|---|---|
| 1 | `src/site_web/` + tests | comptes, invitations, sessions, client orchestrateur |
| 2 | Les 8 écrans | É1 à É8, avec tous les cas d'erreur |
| 3 | Premier essai **en local** | parcours complet 1 → 13 |
| 4 | `run-site.sh` + `settings-site.yaml` | lancement du site |
| 5 | Mise en ligne | Caddy + domaine + HTTPS (étape 6 du plan) |
| 6 | Recette | les 10 critères d'acceptation de la spécification |

---

## Décisions attendues du porteur

| # | Décision | Proposition |
|---|---|---|
| 1 | Technologie : pages rendues **côté serveur** | oui (le plus simple, 0 €) |
| 2 | **Nom de domaine** | à préciser (provisoire : `memo.<domaine>`) |
| 3 | Export du dossier : **archive unique** | oui, + accès élément par élément |
| 4 | Langue | français seulement au démarrage |
| 5 | Combien de tentatives de connexion avant blocage temporaire | 5, puis 15 minutes |
