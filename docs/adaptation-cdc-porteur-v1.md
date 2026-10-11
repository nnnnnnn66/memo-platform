# Adaptation du cahier des charges porteur (v1.0) à la solution existante

> **Objet.** Le porteur a remis son *Cahier des charges fonctionnel et technique v1.0* de la
> plateforme. Ce document le confronte à **ce qui existe déjà** dans le projet, dit **ce qui est
> couvert, partiel ou absent**, tranche les **collisions de vocabulaire**, et propose l'**adaptation**
> et les **décisions à valider**. Aucune ligne de code n'a été écrite pour produire ce document.
> Statut : **proposition à valider par le porteur** (décision attendue en fin de document).

---

## 1. Résumé exécutif

| Constat | Détail |
|---|---|
| **Le socle scientifique demandé existe déjà** | 11 agents d'étape + 1 vérificateur global (étape 13), chaîne 1 → 11 vérifiée en exécution réelle, 688 tests. Le CDC §8.1 « parcours guidé couvrant les principales étapes de la méthodologie » est donc **déjà satisfait au fond**. |
| **Ce qui manque est d'une autre nature** | Ce ne sont pas des agents d'analyse : c'est la **couche pédagogique** (leçons, exemples, quiz, glossaire), l'**assistant conversationnel**, le **questionnaire de démarrage**, la **reprise d'un travail existant**, l'**administration des contenus sans code**, l'**export DOCX** et l'**exploitation** (sauvegardes testées, conservation des données, limitation de débit). |
| **Deux modules du CDC ne correspondent à aucune étape** | Module 1 (comprendre la méthodologie) et Module 11 (finaliser et préparer la soutenance). |
| **Une collision de vocabulaire doit être tranchée** | Le CDC §11 appelle « agents » les **7 rôles de l'équipe de construction** ; le projet appelle « agents » les **13 étapes logicielles**. À clarifier avant toute communication. |
| **Le cadre est déjà fixé et ne bouge pas** | Budget 0 €, aucune invention, portillon humain, sécurité OWASP LLM01-10, honnêteté affichée (inconnues et limites montrées). Le CDC est **compatible** avec ces règles — il les renforce même. |

---

## 2. Correspondance pédagogique : les 11 modules du CDC ↔ les étapes de la solution

| Module du CDC | Étape(s) existante(s) | État |
|---|---|---|
| **M1 — Comprendre la méthodologie** (leçons, glossaire, quiz) | *aucune* | **ABSENT** — contenu pédagogique à créer |
| **M2 — Choisir et délimiter le sujet** | Étape 1 (`subject_agent`) | **Couvert** |
| **M3 — Construire la problématique** | Étapes 2, 3, 4 (problème, revue de littérature, problématique) | **Couvert** |
| **M4 — Objectifs et hypothèses** | Étapes 5, 6, 7 (question, objectifs, hypothèses) | **Couvert** |
| **M5 — Revue de littérature** | Étape 3 | **Couvert** (recherche, sélection, bibliographie APA/BibTeX/RIS/CSV, téléchargement des PDF) — **partiel** sur les *fiches de lecture* et le *tableau de synthèse des auteurs* |
| **M6 — Choisir la méthodologie** | Étapes 8, 9 (diagnostic, protocole) | **Couvert** |
| **M7 — Préparer les outils de collecte** (questionnaires, guides d'entretien, grilles) | Étape 9 (le protocole décrit les instruments) | **Partiel** — la production guidée des outils n'est pas exposée |
| **M8 — Traiter et analyser les données** | Étape 10 | **Couvert** (les chiffres sont calculés par le code, jamais inventés) |
| **M9 — Rédiger les chapitres** | Étape 11 (conclusion) + sorties de chaque étape | **Partiel** — pas de plan de rédaction global, ni transitions, ni relecture de texte fourni |
| **M10 — Citations, bibliographie, présentation** | Étape 3 (styles APA, exports) + étape 11 | **Partiel** — manquent le contrôle citations ↔ bibliographie et l'export **DOCX** |
| **M11 — Finaliser et préparer la soutenance** | *aucune* | **ABSENT** |

**Proposition** : utiliser l'**étape 12, aujourd'hui réservée**, pour « **Finalisation et préparation
de la soutenance** » (M9 complet + M10 restant + M11). Le vérificateur global reste en étape 13 et
audite alors le dossier complet, soutenance comprise. Aucune renumérotation, aucun agent existant
modifié.

---

## 3. Collision de vocabulaire à trancher (important pour la communication)

| Terme | Dans le CDC porteur | Dans la solution | Proposition |
|---|---|---|---|
| « Agent » | les 7 **rôles de l'équipe** de construction (§11 : Pilotage, Pédagogie, UX/UI, Développement, IA, QA, Démonstration) | les **13 étapes logicielles** (un service par étape, avec son vérificateur) | Appeler les 7 rôles des **pôles de travail** (« pôle pédagogie », « pôle développement »…) et réserver le mot **agent** aux étapes de la plateforme. Sinon chaque échange sera ambigu. |

Les **7 pôles du CDC §11 sont conservés intégralement** : ils décrivent l'organisation du travail, pas
le logiciel. Ils recouvrent exactement les tâches prévues au plan (§13) : cadrage, conception
pédagogique, UX/UI, socle technique, développement, intégration IA, tests, recette, mise en ligne,
accompagnement.

---

## 4. Ce qui existe déjà — avec preuves

| Élément du CDC | Où c'est, aujourd'hui | Preuve |
|---|---|---|
| Parcours méthodologique complet (§3, §8.1) | 11 étapes + vérification globale | `src/research_*` / `src/*_agent`, chaîne 1 → 11 `verified` |
| Cohérence entre question, objectifs, hypothèses, méthodologie, résultats (§3 M4, §4.3) | vérificateurs d'étape **+ vérificateur global** (étape 13) | audit réel : 9 constats fondés, dont « objectifs non couverts », « question changement d'objet » |
| Zéro invention (§9.2, §17) | gardes numériques et de traçabilité + contrôleurs | tests : chiffre inventé refusé, référence absente refusée, hypothèse « confirmée » refusée |
| Statuts d'étape (§4.3) | statuts de document par étape (brouillon → validé) + portillon humain | `document_status`, `student_validation` |
| Sauvegarde et reprise (§4.4) | dossier persistant par étudiant/session + journal d'audit | `workspace/<étudiant>/<session>/…`, `audit-*.db` |
| Bibliographie et citations (§3 M10) | styles APA 7, exports BibTeX/RIS/CSV, téléchargement des PDF | `GET /literature/…/bibliographie?format=…` |
| Documents téléchargeables (§4.6) | manifeste des documents + fichier réel + lien officiel | routes de l'étape 3 |
| Export (§8.1) | export du dossier depuis le site | `GET /memoire/{session}/export` |
| Isolation des étudiants et sécurité (§10.1, §14.4) | session, CSRF, hachage, cloisonnement par compte | 57 tests du site + tests de sécurité des agents |
| Interface mobile (§8.1) | pages responsive | à confirmer avec le porteur sur téléphone |
| Tableau de bord (§4.1) et administration (§7) | écrans présents, **contenus non modifiables** | `main.py` — l'admin ne gère pas encore les leçons |

---

## 5. Écarts à combler, par ordre de priorité

| # | Écart | Pourquoi c'est prioritaire | Effort |
|---|---|---|---|
| **E1** | **Questionnaire de démarrage** (niveau, domaine, établissement, sujet existant ?, guide ?, échéance) + dossier de consignes | le CDC en fait le point d'entrée (§2.1) et conditionne l'adaptation (§5) | faible |
| **E2** | **Couche pédagogique** : leçons courtes, exemples, quiz, glossaire, bibliothèque de ressources (§3 M1, §4.5) | c'est **le cœur du CDC** ; aujourd'hui la plateforme questionne mais n'**enseigne** pas | **élevé** (contenu à écrire) |
| **E3** | **Assistant IA contextuel** avec les 5 formes d'aide (« Explique-moi », « Donne-moi un exemple », « Aide-moi à commencer », « Vérifie mon travail », « Que dois-je faire ensuite ? ») | §4.2 ; aujourd'hui l'aide est figée par étape | moyen |
| **E4** | **Reprise d'un travail existant** : import/saisie d'éléments déjà rédigés, détection des manques, reprise à la bonne étape, tout restant modifiable (§2.2) | §2.2 ; évite de forcer l'étudiant à repartir de zéro | moyen |
| **E5** | **Administration des contenus sans code** (leçons, exemples, modèles, aperçu avant publication) | **exigence non négociable du CDC §7** | moyen |
| **E6** | **Export DOCX** + contrôle cohérence citations ↔ bibliographie (§3 M10) | §8.1 (export) et §3 M10 | moyen |
| **E7** | **Étape 12 — Finalisation et soutenance** : plan de rédaction, transitions, résumé, plan de présentation, questions de jury, entraînement (§3 M9/M11) | le CDC veut couvrir **tout le cycle** dès le MVP | **élevé** |
| **E8** | **Exploitation** : sauvegardes **testées en restauration**, limitation de débit, politique de conservation et de suppression, politique de confidentialité (§10.1, §14.4, §11) | conditions de mise en production du CDC (§14.6) | moyen |
| **E9** | **Indicateurs et statistiques** dans l'espace de gestion (§7, §16) | pilotage par le porteur | faible |
| **E10** | **Statuts d'étape du CDC** (§4.3 : à commencer, en cours, à améliorer, prêt pour validation, validé) + validation d'encadreur **optionnelle** | vocabulaire visible par l'étudiant ; à aligner avec nos statuts internes | faible |
| **E11** | **Outils de collecte guidés** (questionnaire, guide d'entretien, grille d'observation) — §3 M7 | module entier à exposer, pas seulement décrit | moyen |

---

## 6. Ce que je propose de ne pas faire — et pourquoi

| Demande du CDC | Proposition | Raison |
|---|---|---|
| « Formules gratuites et payantes » (§8.2) | **reporter** | contrainte projet : budget 0 € ; un paiement ouvrirait des obligations (facturation, remboursement, données bancaires) hors de portée aujourd'hui |
| Applications mobiles dédiées (§8.2) | **reporter** | le CDC demande lui-même une expérience mobile ; une page responsive y répond à coût nul |
| Collaboration étudiants ↔ encadreurs, validation d'encadreur (§8.2) | **garder la porte ouverte**, ne pas construire maintenant | exige des comptes encadreurs et une gestion des droits ; à décider après le pilote |
| Connexion à des catalogues scientifiques et analyse PDF/DOCX avancée (§8.2) | **reporter** | l'étape 3 couvre déjà la recherche en accès ouvert ; l'analyse de documents importés demande un traitement de fichiers à sécuriser |
| Diapositives générées, simulations vocales (§8.2) | **reporter** | utile, mais après le MVP |

Ces reports sont **explicites** et devront figurer dans « la liste des fonctionnalités reportées »
(livrable du CDC §15) : rien ne sera **présenté comme disponible** avant d'être réellement testé
(règle du CDC §8.2 et §19).

---

## 7. Adaptation proposée du plan de réalisation

Le CDC §13 fixe 10 phases et §12.2 six jalons avec validation à chaque jalon. Proposition alignée sur
l'existant :

| Jalon | Contenu | Validation attendue |
|---|---|---|
| **J1 — Comprendre le besoin** | ce document + le cahier des charges validé ; liste des écarts E1–E11 ; reports explicites | porteur : valide le besoin et les priorités |
| **J2 — Voir le futur site** | maquettes cliquables de l'accueil « Commencer mon mémoire », du questionnaire de démarrage, d'une étape **avec leçon + exemple**, de l'assistant, du tableau de bord, de l'administration | porteur : dit ce qui est confus |
| **J3 — Essayer une première version** | E1 (démarrage) + E2 (premières leçons) + E3 (assistant) + E5 (administration) ; parcours réel jouable de bout en bout | porteur : suit un dossier de démonstration |
| **J4 — Parcours complet + soutenance** | E7 (étape 12), E6 (export DOCX), E4 (reprise) | porteur : joue le scénario complet §12.2 jalon 4 |
| **J5 — Améliorations** | E8 (sauvegardes testées, conservation, débit), E9, E10, E11 | porteur : valide les corrections |
| **J6 — Produit final** | mise en ligne (Caddy + HTTPS + adresse), recette des 10 critères, guides utilisateur et administration | porteur : recette et prise en main |

**Un seul chantier à la fois**, comme aujourd'hui : chaque jalon est un incrément testable, et rien
n'est annoncé avant d'être vérifié.

---

## 8. Contraintes du CDC que la solution respecte déjà — à maintenir

- **Aucune invention** : sources, données, résultats, références. Déjà garanti par le code (gardes,
  traçabilité, refus des chiffres non calculés) et non par la seule consigne de prompt.
- **Distinguer** ce qui est vérifié, suggéré et à valider : affiché, jamais masqué.
- **L'IA n'écrit pas le mémoire à la place de l'étudiant** : chaque étape produit une *proposition*,
  la décision appartient à l'étudiant.
- **Secrets côté serveur**, jamais dans le navigateur.
- **Un étudiant ne voit que son dossier.**

---

## 9. Décisions attendues du porteur

| # | Décision | Proposition par défaut |
|---|---|---|
| 1 | Valider ce cahier des charges comme **base de travail** (CDC §19) | oui |
| 2 | **Nommer les 7 rôles du CDC §11 « pôles »** et réserver « agent » aux étapes logicielles | oui |
| 3 | Utiliser l'**étape 12** (réservée) pour « Finalisation et préparation de la soutenance » | oui |
| 4 | Ordre des priorités : **E1 → E2 → E3 → E5** avant le reste | oui |
| 5 | Qui **relit et valide les contenus pédagogiques** (le CDC §11 l'exige : « relus par une personne compétente en méthodologie ») | à désigner |
| 6 | **Ouverture** : pilote fermé (invitations) ou inscription libre (le CDC §2.1 décrit une inscription libre) | pilote fermé d'abord, à l'usage des quotas |
| 7 | **Nom public** de la plateforme et **adresse** (gratuite ou domaine) | à préciser |
| 8 | **Conservation des données** et **suppression** sur demande | à fixer (proposition : conservation pendant le cursus, suppression sur demande) |
| 9 | L'**encadreur** peut-il voir le dossier de son étudiant ? | plus tard, après le pilote |

---

## 10. Ce que ce document ne fait pas

Il ne remplace pas le cahier des charges : **celui du porteur fait référence**. Il ne code rien, ne
maquette rien, ne planifie aucun calendrier chiffré (le CDC §13 demande le calendrier **après**
évaluation des ressources, ce qui suppose les décisions ci-dessus). Il ne modifie aucun agent
existant : toute évolution d'un agent déjà validé passera par une contre-signature du porteur.

**Décision attendue : valider le cahier des charges v1.0 comme base de travail, puis lancer le
cadrage opérationnel (J1) et la conception pédagogique avant tout développement complet.**
