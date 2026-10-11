# CAHIER DES CHARGES FONCTIONNEL ET TECHNIQUE

**Projet Miss Koffi — Plateforme intelligente d'accompagnement à la rédaction des mémoires de recherche**

- **Version** : 1.0
- **Statut** : Document de référence pour la conception, le développement, les tests et la présentation du projet
- **Porteuse du projet** : Miss Koffi
- **Destinataires** : Agents de conception, de développement, d'intégration de l'IA, de test et de présentation

> Document déposé **verbatim** dans le projet le 2026-10-10, à la demande du porteur : il constitue le
> **référentiel commun** du projet. La confrontation à la solution existante et les écarts sont traités
> dans `docs/adaptation-cdc-porteur-v1.md`.

---

## 1. Présentation générale du projet

### 1.1. Contexte

De nombreux étudiants rencontrent des difficultés lorsqu'ils doivent rédiger un mémoire de recherche, un rapport de recherche ou un travail académique de fin de cycle.

Ils ne savent pas toujours :

- Comment choisir et délimiter un sujet de recherche.
- Comment formuler une problématique pertinente.
- Comment définir les objectifs et les hypothèses.
- Comment effectuer une revue de littérature.
- Comment choisir une méthodologie scientifique adaptée.
- Comment collecter et analyser des données.
- Comment structurer les différents chapitres du mémoire.
- Comment citer correctement les sources et établir une bibliographie.
- Comment préparer la soutenance devant un jury.

Les ressources pédagogiques disponibles sont souvent dispersées. Les étudiants peuvent également se sentir perdus face à des explications trop techniques ou à des documents méthodologiques difficiles à appliquer.

### 1.2. Vision du projet

Créer une plateforme web éducative, accessible et intelligente qui accompagne chaque étudiant dans la réalisation de son mémoire de recherche.

La plateforme doit transformer une tâche complexe en un parcours progressif, compréhensible et réalisable.

Principe fondamental : l'étudiant ne doit jamais se demander seul quelle est la prochaine étape.

La plateforme lui explique ce qu'il doit faire, pourquoi il doit le faire, comment procéder, quels éléments fournir et comment vérifier son travail avant de continuer.

L'intelligence artificielle doit jouer le rôle d'un assistant méthodologique et pédagogique, et non celui d'un auteur qui rédige intégralement le mémoire à la place de l'étudiant.

### 1.3. Objectif principal

Permettre à un étudiant, même débutant en méthodologie scientifique, de suivre un parcours structuré et personnalisé pour élaborer son mémoire, avec des explications, des exemples, des exercices, des modèles, des outils d'aide à la rédaction et un accompagnement par l'intelligence artificielle.

### 1.4. Public cible

La première version vise principalement :

- Les étudiants de Licence.
- Les étudiants de Master.
- Les étudiants en fin de cycle dans les établissements d'enseignement supérieur.
- Les étudiants qui rédigent un mémoire ou un rapport de recherche.
- Les étudiants qui ont commencé leur mémoire mais ne savent plus comment avancer.

La plateforme pourra ensuite être adaptée aux doctorants et à d'autres types de travaux académiques.

### 1.5. Principes directeurs

- **Simplicité** : une interface compréhensible sans formation technique.
- **Progressivité** : avancer étape par étape sans submerger l'étudiant.
- **Personnalisation** : adapter le parcours au niveau, à la discipline et aux exigences de l'établissement.
- **Accompagnement** : expliquer chaque action au lieu de simplement afficher des formulaires.
- **Rigueur scientifique** : respecter les principes de la méthodologie scientifique.
- **Transparence** : distinguer les informations vérifiées, les suggestions de l'IA et les éléments à valider.
- **Autonomie** : aider l'étudiant à comprendre et à améliorer son propre travail.
- **Accessibilité** : privilégier une expérience mobile, un langage clair et une consommation raisonnable de données.

---

## 2. Expérience attendue pour l'étudiant

Le parcours utilisateur est au cœur du projet.

### 2.1. Scénario d'utilisation principal

Un étudiant découvre le site. Il n'a pas encore de sujet précis et ne connaît pas bien les étapes d'un mémoire.

Il arrive sur la page d'accueil et comprend immédiatement que la plateforme peut l'accompagner.

Il clique sur « Commencer mon mémoire ».

L'assistant lui pose quelques questions simples :

- Quel est votre niveau d'études ?
- Dans quel domaine étudiez-vous ?
- Quel est votre établissement ?
- Avez-vous déjà un sujet ?
- Disposez-vous d'un guide de rédaction ou de consignes de votre encadreur ?
- À quelle échéance devez-vous terminer votre travail ?

L'étudiant répond progressivement, avec des explications et des exemples.

La plateforme lui propose ensuite un parcours adapté.

S'il n'a pas de sujet, elle l'aide à explorer des idées. S'il en possède déjà un, elle l'aide à le délimiter et à vérifier sa faisabilité.

À chaque étape, il peut :

- Lire une explication simple.
- Consulter un exemple.
- Répondre à des questions guidées.
- Utiliser l'IA pour clarifier ses idées.
- Enregistrer son travail.
- Demander une vérification.
- Modifier ses réponses.
- Passer à l'étape suivante lorsqu'il est prêt.

Son espace personnel conserve son avancement. Lorsqu'il revient sur le site, il retrouve son travail et reprend là où il s'était arrêté.

### 2.2. Expérience des étudiants qui ont déjà commencé

La plateforme ne doit pas imposer à tous les utilisateurs de repartir de zéro.

Un étudiant qui possède déjà un sujet, une problématique ou un document doit pouvoir importer ou saisir ses éléments existants.

L'assistant identifie les éléments fournis, indique les informations manquantes et propose une reprise du parcours à l'étape appropriée.

Toute détection automatique doit rester modifiable par l'étudiant.

---

## 3. Structure pédagogique : les étapes du mémoire

Le parcours pédagogique constitue le socle du produit. Chaque étape doit être un véritable module d'apprentissage et de travail.

### Module 1 — Comprendre la méthodologie scientifique

**Objectif** : permettre à l'étudiant de comprendre ce qu'est un mémoire de recherche et comment il se construit.

Contenus :

- Définition d'un mémoire de recherche.
- Différence entre sujet, thème, problématique et question de recherche.
- Principales étapes d'une recherche scientifique.
- Différence entre recherche qualitative, quantitative et mixte.
- Rôle de l'encadreur.
- Erreurs courantes à éviter.

Fonctionnalités :

- Leçons courtes et illustrées.
- Glossaire des termes scientifiques.
- Quiz de compréhension.
- Assistant IA capable d'expliquer une notion avec des mots simples.

**Résultat attendu** : l'étudiant comprend la démarche générale avant de commencer son propre travail.

### Module 2 — Choisir et délimiter le sujet

**Objectif** : transformer une idée générale en sujet de recherche réalisable.

L'étudiant est accompagné pour :

- Identifier un domaine qui l'intéresse.
- Repérer un problème concret.
- Définir le contexte géographique, temporel et thématique.
- Vérifier la disponibilité potentielle des données.
- Évaluer la faisabilité du sujet selon ses ressources et son calendrier.

L'IA peut proposer des sujets, comparer leurs avantages et leurs limites et aider à reformuler un intitulé.

Elle ne doit pas présenter un sujet comme scientifiquement pertinent ou réalisable sans examiner les éléments disponibles.

**Résultat attendu** : un sujet provisoire, une justification et une délimitation clairement formulées.

### Module 3 — Construire la problématique

**Objectif** : apprendre à passer d'un sujet à un problème de recherche précis.

Le module explique :

- Le contexte du problème.
- Les constats et les faits qui justifient la recherche.
- Les écarts entre une situation observée et une situation souhaitée.
- Les questions auxquelles la recherche cherchera à répondre.
- La formulation de la question principale et des questions secondaires.

L'IA pose des questions, repère les formulations trop générales et propose des améliorations argumentées.

Elle ne doit pas inventer des faits, des statistiques ou des études pour justifier la problématique.

**Résultat attendu** : une problématique structurée et une question principale de recherche.

### Module 4 — Définir les objectifs et les hypothèses

**Objectif** : assurer la cohérence entre le problème posé et les résultats recherchés.

Le module permet de définir :

- L'objectif général.
- Les objectifs spécifiques.
- Les hypothèses de recherche, lorsque la démarche en nécessite.
- Les variables ou les concepts à étudier.
- Les relations attendues entre les éléments étudiés.

L'assistant vérifie la cohérence entre la question de recherche, les objectifs et les hypothèses.

Il explique pourquoi une hypothèse est utile dans certaines recherches, mais ne doit pas imposer des hypothèses aux approches qui n'en nécessitent pas.

**Résultat attendu** : des objectifs et, si nécessaire, des hypothèses clairement formulés.

### Module 5 — Réaliser la revue de littérature

**Objectif** : apprendre à rechercher, sélectionner, lire et organiser les travaux scientifiques existants.

Fonctionnalités :

- Guide de recherche documentaire.
- Conseils pour choisir des mots-clés.
- Organisation des références bibliographiques.
- Fiches de lecture.
- Tableau de synthèse des auteurs, concepts, méthodes et résultats.
- Aide à comparer les travaux et à identifier les limites de la littérature.
- Importation de références ou de documents lorsque les fonctionnalités correspondantes sont disponibles.

L'IA peut résumer un document fourni, extraire des idées importantes et aider à comparer des textes, en précisant le document utilisé.

Elle ne doit jamais inventer des références bibliographiques ou présenter une source comme consultée lorsqu'elle ne l'a pas été.

Les sources proposées par l'IA doivent être vérifiées avant utilisation.

**Résultat attendu** : une base documentaire organisée et une synthèse critique des connaissances existantes.

### Module 6 — Choisir la méthodologie de recherche

**Objectif** : aider l'étudiant à concevoir une démarche adaptée à sa question de recherche.

Contenus :

- Approches qualitative, quantitative et mixte.
- Population étudiée et échantillonnage.
- Critères d'inclusion et d'exclusion.
- Techniques de collecte des données.
- Entretiens, questionnaires, observations et analyse documentaire.
- Choix des outils de traitement et d'analyse.
- Limites méthodologiques.
- Consentement, confidentialité et éthique de la recherche.

L'assistant propose des options en expliquant leurs avantages, leurs limites et leurs conditions d'utilisation.

**Résultat attendu** : un protocole méthodologique cohérent, à faire valider par l'encadreur lorsque cela est nécessaire.

### Module 7 — Préparer les outils de collecte des données

**Objectif** : transformer la méthodologie en actions concrètes.

Fonctionnalités :

- Création guidée de questionnaires.
- Préparation de guides d'entretien.
- Élaboration de grilles d'observation.
- Vérification de la cohérence entre les questions et les objectifs.
- Conseils pour réaliser un prétest.
- Préparation d'un plan de collecte.
- Consignes sur le consentement et la protection des données.

Les outils générés par l'IA doivent être relus, testés et validés avant leur utilisation réelle.

**Résultat attendu** : des outils de collecte prêts à être examinés et utilisés selon le protocole approuvé.

### Module 8 — Traiter et analyser les données

**Objectif** : accompagner l'étudiant dans l'analyse rigoureuse des données réellement collectées.

Le module doit expliquer :

- Le nettoyage et l'organisation des données.
- Le codage des réponses qualitatives.
- Les statistiques descriptives élémentaires.
- La construction de tableaux et de graphiques.
- L'interprétation des résultats.
- La mise en relation des résultats avec les objectifs et les hypothèses.
- Les limites des analyses réalisées.

L'IA peut aider à comprendre une méthode d'analyse, à expliquer un tableau ou à proposer des pistes d'interprétation à partir des données fournies.

Elle ne doit jamais fabriquer des données de recherche ni présenter des résultats simulés comme des observations réelles.

**Résultat attendu** : des analyses documentées, des résultats traçables et une interprétation argumentée.

### Module 9 — Rédiger les chapitres du mémoire

**Objectif** : aider l'étudiant à structurer et à rédiger son document.

Les chapitres proposés sont indicatifs. Leur organisation doit être adaptable aux disciplines et aux consignes de l'établissement.

Le module couvre généralement :

- Introduction générale.
- Contexte et justification du sujet.
- Problématique et questions de recherche.
- Objectifs et hypothèses, selon le projet.
- Revue de littérature et cadre théorique.
- Méthodologie.
- Présentation des résultats.
- Discussion des résultats.
- Conclusion générale et recommandations.
- Bibliographie et annexes.

L'assistant doit aider à construire un plan détaillé, expliquer la fonction de chaque partie, suggérer des transitions et relire les textes rédigés par l'étudiant.

Il doit signaler les affirmations qui nécessitent une source et distinguer les suggestions de rédaction des éléments factuels.

**Résultat attendu** : un mémoire structuré et progressivement rédigé par l'étudiant.

### Module 10 — Citations, bibliographie et présentation

**Objectif** : réduire les erreurs formelles et renforcer la qualité académique du document.

Fonctionnalités :

- Explication des citations directes et indirectes.
- Organisation des références.
- Aide à l'application d'un style bibliographique.
- Contrôle de cohérence entre citations et bibliographie.
- Vérification de la présence des éléments obligatoires.
- Conseils sur les titres, tableaux, figures, annexes et numérotation.
- Export du document dans un format adapté, notamment DOCX si cette fonctionnalité est prévue et testée.

Les styles bibliographiques et les règles de présentation doivent pouvoir être adaptés aux exigences institutionnelles.

**Résultat attendu** : un document correctement structuré et des références vérifiables.

### Module 11 — Finaliser et préparer la soutenance

**Objectif** : préparer l'étudiant à présenter et défendre son travail.

Fonctionnalités :

- Liste de vérification finale.
- Relecture de cohérence générale.
- Préparation d'un résumé du mémoire.
- Élaboration d'un plan de présentation.
- Aide à la préparation des diapositives.
- Simulation de questions de jury.
- Entraînement à l'oral.
- Conseils pour répondre aux questions difficiles et reconnaître les limites de son travail.

L'IA doit formuler des questions pertinentes en fonction du mémoire fourni et expliquer comment construire une réponse argumentée.

**Résultat attendu** : un mémoire prêt à être soumis selon les exigences applicables et un étudiant mieux préparé à sa soutenance.

---

## 4. Fonctionnalités transversales obligatoires

### 4.1. Tableau de bord étudiant

Chaque étudiant dispose d'un espace personnel affichant :

- Son projet de mémoire.
- Son sujet et son domaine.
- L'étape actuelle.
- Les étapes terminées.
- Les tâches à effectuer.
- Les éléments à corriger.
- Les documents enregistrés.
- Les prochaines actions recommandées.

Le tableau de bord doit répondre immédiatement à trois questions :

- Où en suis-je ?
- Que dois-je faire maintenant ?
- Comment savoir si mon travail est suffisamment avancé ?

### 4.2. Assistant IA pédagogique

L'assistant est disponible tout au long du parcours.

Il doit pouvoir :

- Expliquer une notion difficile en langage simple.
- Reformuler une consigne.
- Poser des questions pour faire progresser l'étudiant.
- Donner des exemples clairement identifiés comme tels.
- Aider à améliorer un texte existant.
- Détecter les incohérences entre différentes parties du projet.
- Proposer des exercices.
- Résumer les progrès et les points à revoir.
- Adapter son niveau d'explication à l'étudiant.
- Expliquer pourquoi il recommande une modification.

L'étudiant doit pouvoir choisir entre plusieurs formes d'aide : « Explique-moi », « Donne-moi un exemple », « Aide-moi à commencer », « Vérifie mon travail » et « Que dois-je faire ensuite ? ».

**Règle essentielle** : l'IA ne doit pas se contenter de produire un texte prêt à copier. Elle doit expliquer, questionner, guider et aider à améliorer la compréhension. Lorsque des informations manquent, elle doit poser des questions au lieu de combler les lacunes par des inventions.

### 4.3. Validation des étapes

Chaque étape possède des critères de réussite explicites.

Par exemple, avant de considérer la problématique comme prête, la plateforme vérifie que l'étudiant a identifié le problème, présenté le contexte, formulé une question principale et expliqué l'intérêt de la recherche.

L'IA peut proposer un avis pédagogique, mais les validations automatiques doivent rester révisables. La plateforme ne doit pas prétendre garantir la qualité scientifique d'un mémoire.

Un statut clair est associé à chaque étape :

- À commencer.
- En cours.
- À améliorer.
- Prêt pour validation.
- Validé par l'étudiant.

Un statut supplémentaire peut permettre de noter la validation de l'encadreur, si le projet prévoit cette fonctionnalité.

### 4.4. Sauvegarde et reprise du travail

L'étudiant doit pouvoir quitter le site et revenir sans perdre son travail.

Les données saisies doivent être enregistrées de manière fiable. Les états de sauvegarde doivent être visibles.

L'application doit gérer les erreurs de connexion et éviter les pertes silencieuses de contenu.

### 4.5. Bibliothèque de ressources

La plateforme doit proposer :

- Des fiches méthodologiques.
- Des modèles de plans.
- Des exemples de problématiques.
- Des exemples de questionnaires.
- Des fiches de lecture.
- Des modèles de présentation.
- Un glossaire.
- Des listes de contrôle téléchargeables.

Les exemples doivent être identifiés comme pédagogiques et ne pas être présentés comme des recherches réelles si ce n'est pas le cas.

### 4.6. Gestion des documents

L'étudiant doit pouvoir, selon les fonctionnalités retenues :

- Créer du contenu directement dans la plateforme.
- Importer un document existant.
- Consulter ses documents enregistrés.
- Organiser les versions de son travail.
- Exporter les résultats de son travail.

Les formats, limites de taille et règles de conservation doivent être clairement définis.

---

## 5. Une plateforme adaptable aux exigences académiques

Il n'existe pas un plan unique valable pour tous les mémoires.

La plateforme doit donc commencer par identifier les consignes applicables à l'étudiant.

Au démarrage, il pourra préciser :

- Son établissement.
- Son diplôme.
- Sa discipline.
- Le type de travail attendu.
- Le guide méthodologique disponible.
- Le style bibliographique exigé.
- Les consignes spécifiques de son encadreur.

Lorsqu'il dispose d'un guide de rédaction en PDF ou en DOCX, la plateforme pourra, si l'import et l'analyse de ces formats sont implémentés, l'utiliser pour extraire les exigences pertinentes.

L'étudiant devra pouvoir corriger les informations extraites.

En l'absence de consignes institutionnelles, la plateforme proposera un parcours méthodologique général, en indiquant clairement qu'il doit être adapté aux exigences de l'établissement.

---

## 6. Interface et expérience utilisateur

### 6.1. Principes de conception

L'interface doit inspirer confiance, sérieux et simplicité.

Elle doit éviter :

- Les tableaux de bord trop chargés.
- Les termes techniques non expliqués.
- Les formulaires interminables.
- Les pages remplies de textes difficiles à parcourir.
- Les fonctionnalités qui semblent disponibles mais ne fonctionnent pas.
- Les demandes répétées d'informations déjà fournies.

Le design doit privilégier des étapes visuelles, des consignes courtes, des exemples accessibles, des boutons explicites et une navigation cohérente.

### 6.2. Page d'accueil

La page d'accueil doit présenter clairement :

- Le problème auquel répond la plateforme.
- La manière dont elle accompagne l'étudiant.
- Les principales étapes du parcours.
- Le rôle de l'intelligence artificielle.
- Les bénéfices concrets.
- Un bouton principal « Commencer mon mémoire ».
- Un accès à la connexion pour les utilisateurs existants.

L'étudiant doit comprendre en quelques secondes à quoi sert le site.

### 6.3. Écran d'une étape

Chaque écran de travail doit présenter :

- Le nom de l'étape.
- Son objectif.
- Une explication simple.
- Un exemple pertinent.
- Les questions ou actions à réaliser.
- L'espace de saisie.
- Un accès à l'assistant IA.
- Un bouton de sauvegarde ou un indicateur de sauvegarde automatique.
- Les critères permettant de vérifier le travail.
- Le bouton pour continuer.

L'interface doit être responsive et utilisable sur téléphone, tablette et ordinateur.

### 6.4. Accessibilité

Les contrastes, la taille des caractères, les libellés des champs et la navigation doivent être pensés pour limiter les difficultés d'utilisation.

Les messages d'erreur doivent expliquer comment corriger un problème, et non simplement signaler qu'une action a échoué.

---

## 7. Espace de gestion pour Miss Koffi

Miss Koffi doit pouvoir gérer le contenu pédagogique sans modifier le code.

L'administration doit lui permettre, selon les fonctionnalités retenues :

- D'ajouter et de modifier des leçons.
- De modifier les exemples.
- De gérer les modèles de documents.
- De corriger les consignes d'une étape.
- D'organiser les modules.
- De consulter des statistiques générales d'utilisation.
- De gérer les contenus publiés.
- De tester les modifications avant leur publication.

Un mode aperçu doit lui permettre de voir le résultat comme un étudiant.

Les contenus sensibles, les données personnelles et les travaux privés des étudiants ne doivent pas être accessibles sans autorisation appropriée.

**Exigence non négociable** : Miss Koffi ne doit pas avoir besoin d'un développeur pour corriger une faute, modifier un exemple ou mettre à jour une leçon courante.

---

## 8. Périmètre de la première version (MVP)

La première version doit être suffisamment complète pour démontrer la valeur du produit, mais suffisamment limitée pour être construite, testée et améliorée rapidement.

### 8.1. Fonctionnalités indispensables

- Page d'accueil.
- Présentation du fonctionnement.
- Création de compte et connexion.
- Questionnaire de démarrage.
- Création d'un projet de mémoire.
- Parcours guidé couvrant les principales étapes de la méthodologie scientifique.
- Leçons et exemples pédagogiques.
- Assistant IA contextuel.
- Sauvegarde de la progression.
- Tableau de bord étudiant.
- Vérification de cohérence de base.
- Bibliothèque initiale de ressources.
- Espace d'administration des contenus.
- Interface mobile.
- Export d'un document de synthèse ou d'un plan de mémoire.
- Gestion des erreurs, sécurité et protection des données.

Le parcours pédagogique doit couvrir l'ensemble du cycle de recherche dès le MVP. En revanche, les fonctionnalités avancées peuvent être développées progressivement.

### 8.2. Fonctionnalités pouvant être ajoutées ensuite

- Import et analyse avancée de guides institutionnels.
- Analyse approfondie de documents PDF et DOCX.
- Gestion avancée des références bibliographiques.
- Connexion à des catalogues scientifiques.
- Outils d'analyse statistique intégrés.
- Collaboration entre étudiants et encadreurs.
- Validation des étapes par un encadreur.
- Génération avancée de documents DOCX.
- Préparation de diapositives.
- Simulations vocales de soutenance.
- Formules gratuites et payantes.
- Applications mobiles dédiées.

Ces fonctionnalités ne doivent être présentées comme disponibles que lorsqu'elles ont effectivement été développées et testées.

---

## 9. Exigences relatives à l'intelligence artificielle

### 9.1. Architecture fonctionnelle

L'assistant IA doit recevoir un contexte contrôlé comprenant, selon le besoin :

- Le niveau d'études.
- La discipline.
- Les consignes institutionnelles fournies.
- Le sujet du mémoire.
- L'étape actuelle.
- Les réponses précédentes utiles.
- Le contenu que l'étudiant demande d'examiner.

Il doit fournir une réponse adaptée à la situation, sans obliger l'étudiant à répéter constamment les mêmes informations.

### 9.2. Qualité des réponses

L'agent chargé de l'IA doit définir et tester des instructions permettant de garantir que l'assistant :

- Répond en français clair par défaut.
- Adapte son vocabulaire au niveau de l'étudiant.
- Distingue les faits des hypothèses et des suggestions.
- Ne fabrique pas de sources ou de données.
- Signale les incertitudes.
- Explique les limites de ses recommandations.
- Privilégie les questions guidées lorsque des informations manquent.
- Respecte la confidentialité des documents.
- Ne présente pas un texte généré comme un travail personnel déjà réalisé par l'étudiant.

Si une recherche documentaire assistée est proposée, les références doivent être traçables et vérifiables.

### 9.3. Gestion des coûts et des erreurs

Les agents doivent prévoir :

- Un suivi de la consommation de l'IA.
- Des limites raisonnables d'utilisation.
- Une gestion des erreurs de fournisseur.
- Des messages compréhensibles en cas d'indisponibilité.
- La conservation du texte saisi avant une requête.
- Des mécanismes évitant les appels inutiles.
- Une architecture permettant de changer de fournisseur sans reconstruire toute l'application.

Si le service IA est indisponible, l'étudiant doit pouvoir continuer à consulter les leçons et à travailler sur ses documents.

### 9.4. Évaluation de l'assistant

L'assistant doit être testé sur un ensemble de scénarios représentatifs :

- Étudiant sans sujet.
- Sujet trop large.
- Problématique incohérente.
- Objectifs incompatibles avec la question de recherche.
- Demande de références bibliographiques inexistantes.
- Demande de fabrication de résultats.
- Document incomplet.
- Consignes institutionnelles contradictoires.
- Demande d'explication très simple.
- Reprise d'un projet déjà avancé.

Les critères d'évaluation incluent la pertinence pédagogique, la cohérence méthodologique, la clarté, la capacité à reconnaître ses limites et l'absence de fabrication de références ou de résultats.

---

## 10. Exigences techniques et sécurité

Les agents techniques doivent proposer une architecture adaptée au budget, aux compétences disponibles et aux objectifs du projet.

Le choix de la stack doit être justifié avant le développement. Il ne faut pas imposer une technologie uniquement parce qu'elle est populaire.

L'architecture doit couvrir :

- Le frontend.
- Le backend et les règles métier.
- La base de données.
- L'authentification.
- Le stockage des documents.
- L'intégration des fournisseurs d'IA.
- Les journaux d'erreurs.
- Les sauvegardes.
- Le déploiement.
- La supervision.

### 10.1. Sécurité

Les exigences minimales sont :

- Contrôle des accès.
- Protection des sessions et des comptes.
- Validation des données saisies.
- Protection contre les accès non autorisés.
- Sécurisation des fichiers importés.
- Secrets et clés API conservés côté serveur.
- Sauvegardes régulières et procédure de restauration testée.
- Limitation des requêtes abusives.
- Politique de conservation et de suppression des données.
- Protection des documents privés des étudiants.

Les données personnelles ne doivent pas être exposées dans les journaux techniques ou envoyées inutilement aux fournisseurs d'IA.

Le traitement des documents par un fournisseur d'IA doit respecter les conditions de confidentialité applicables et être expliqué à l'utilisateur.

La politique de confidentialité, les conditions d'utilisation et les règles de conservation doivent être préparées avant l'ouverture publique.

---

## 11. Organisation du travail des agents

Les agents doivent travailler avec des responsabilités distinctes, mais partager un référentiel commun.

### Agent 1 — Pilotage produit et coordination

Responsabilités : transformer le cahier des charges en tâches concrètes ; définir les priorités ; organiser les dépendances entre les travaux ; maintenir une liste des fonctionnalités et de leur état ; vérifier que chaque fonctionnalité répond à un besoin réel ; préparer les démonstrations destinées à Miss Koffi.

Livrables : plan de travail ; liste des tâches ; suivi des décisions ; registre des risques ; compte rendu des validations.

### Agent 2 — Expertise pédagogique et méthodologique

Responsabilités : définir le parcours de recherche ; produire les contenus des modules ; définir les critères de réussite ; préparer les exemples et exercices ; vérifier la cohérence scientifique ; identifier les variantes selon les disciplines et les établissements.

Livrables : référentiel pédagogique ; leçons et exercices ; exemples validés ; grilles de vérification ; références documentaires vérifiables.

Les contenus doivent être relus par une personne compétente en méthodologie scientifique avant leur publication définitive.

### Agent 3 — UX/UI et expérience utilisateur

Responsabilités : concevoir les parcours ; créer les maquettes ; organiser la navigation ; rendre les formulaires simples ; concevoir l'expérience mobile ; prévoir un mode de démonstration ; tester les écrans avec une personne non technique.

Livrables : maquettes ; prototype navigable ; système de composants visuels ; parcours de démarrage ; écrans du tableau de bord et des modules.

### Agent 4 — Développement frontend et backend

Responsabilités : construire l'application ; implémenter l'authentification ; développer le parcours pédagogique ; mettre en place la sauvegarde ; construire les espaces étudiant et administrateur ; garantir le bon fonctionnement sur les différents appareils ; gérer les erreurs et les états de chargement.

Livrables : application fonctionnelle ; code versionné ; base de données documentée ; tests automatisés pertinents ; documentation de déploiement ; environnement de test accessible.

### Agent 5 — Intégration de l'IA

Responsabilités : concevoir l'assistant contextuel ; définir les instructions et les garde-fous ; gérer les échanges avec les fournisseurs ; mettre en place les contrôles de cohérence ; limiter les coûts ; tester les cas d'erreur et les réponses dangereusement trompeuses.

Livrables : assistant intégré ; instructions documentées ; jeux de tests ; procédure de gestion des erreurs ; suivi de consommation ; documentation de maintenance.

### Agent 6 — Assurance qualité et tests

Responsabilités : vérifier les fonctionnalités ; tester les parcours complets ; détecter les régressions ; vérifier les sauvegardes et les autorisations ; tester les scénarios d'utilisation par des débutants ; contrôler les réponses de l'IA ; vérifier la conformité aux critères d'acceptation.

Livrables : plan de test ; scénarios exécutés ; registre des anomalies ; résultats de recette ; rapport de préparation à la mise en production.

### Agent 7 — Démonstration et accompagnement de Miss Koffi

Responsabilités : préparer une version de démonstration stable ; organiser la présentation ; expliquer les fonctionnalités sans jargon ; montrer comment Miss Koffi pourra administrer les contenus ; recueillir ses retours ; documenter ses décisions ; former Miss Koffi aux opérations courantes.

Livrables : scénario de démonstration ; guide utilisateur ; guide d'administration simplifié ; vidéo ou tutoriel de prise en main si nécessaire ; compte rendu de validation.

**Règle de coordination** : aucun agent ne doit considérer son travail comme terminé sans fournir un livrable vérifiable et signaler les dépendances restantes.

---

## 12. Accompagner Miss Koffi pas à pas

Cette section est obligatoire. Le projet ne doit pas être uniquement fonctionnel : Miss Koffi doit pouvoir comprendre son évolution et prendre des décisions éclairées.

### 12.1. Principe de communication

Les agents doivent expliquer les sujets techniques dans un langage courant.

À chaque présentation, ils doivent préciser :

- Ce qui a été fait.
- À quoi cela sert.
- Ce que Miss Koffi peut essayer.
- Ce qui fonctionne déjà.
- Ce qui reste à améliorer.
- La décision qu'elle doit prendre, si nécessaire.

Ils doivent éviter de lui demander de choisir entre des technologies complexes sans expliquer les conséquences pratiques.

### 12.2. Validation par petites étapes

Le projet doit être découpé en jalons compréhensibles.

- **Jalon 1 — Comprendre le besoin** : présenter le problème ciblé, les utilisateurs prioritaires, le fonctionnement général, les fonctionnalités essentielles et les limites de la première version. Elle valide la vision avant que l'équipe engage un développement important.
- **Jalon 2 — Voir le futur site** : présenter des maquettes cliquables (accueil, inscription, démarrage du mémoire, une étape pédagogique, l'assistant IA, le tableau de bord, l'administration). Miss Koffi doit pouvoir parcourir le prototype et indiquer ce qui lui semble confus.
- **Jalon 3 — Essayer une première version** : mettre à disposition une version de test avec un compte étudiant de démonstration, un parcours fonctionnel, des exemples de contenu, une première intégration de l'IA et un espace administrateur.
- **Jalon 4 — Tester un parcours complet** : Miss Koffi suit un scénario guidé, par exemple celui d'un étudiant qui souhaite rédiger un mémoire sur un problème de gestion d'entreprise.
- **Jalon 5 — Valider les améliorations** : les agents regroupent ses retours, expliquent les corrections proposées et présentent les résultats. Les problèmes bloquants doivent être corrigés avant la mise en production.
- **Jalon 6 — Présenter le produit final** : parcours complet, outils d'administration, mécanismes de sauvegarde, tests effectués et limites connues. Miss Koffi doit disposer d'un guide simple.

### 12.3. Règle de validation

Chaque jalon donne lieu à une démonstration et à une validation explicite. L'équipe doit distinguer :

- Les décisions de Miss Koffi.
- Les recommandations des agents.
- Les points nécessitant un avis spécialisé.
- Les décisions reportées.
- Les éléments qui ne sont pas encore développés.

L'objectif est qu'elle reste la décisionnaire du produit, sans avoir à devenir technicienne.

---

## 13. Plan de réalisation

Le calendrier définitif doit être proposé après l'évaluation de l'existant, des ressources humaines, du budget et de la stack retenue.

| Phase | Travaux | Résultat attendu |
|---|---|---|
| 1. Cadrage | Confirmer les besoins, les publics et les priorités | Périmètre validé |
| 2. Conception pédagogique | Structurer les modules et les critères de réussite | Parcours méthodologique |
| 3. UX/UI | Concevoir les écrans et les interactions | Prototype testable |
| 4. Socle technique | Préparer les environnements, l'authentification et la base de données | Application de base |
| 5. Développement fonctionnel | Construire le parcours, le tableau de bord et l'administration | Version fonctionnelle |
| 6. Intégration IA | Connecter l'assistant et contrôler ses réponses | Assistant opérationnel |
| 7. Tests | Vérifier les fonctions, la sécurité et l'expérience utilisateur | Version candidate |
| 8. Recette | Organiser les tests avec Miss Koffi et corriger les anomalies | Version validée |
| 9. Mise en production | Déployer, sauvegarder et superviser | Site accessible |
| 10. Accompagnement | Former Miss Koffi et documenter l'administration | Prise en main autonome |

Les phases peuvent se chevaucher lorsque cela est pertinent, mais les validations doivent être conservées.

---

## 14. Plan de tests et critères d'acceptation

Le produit ne doit pas être déclaré terminé parce que les pages s'affichent. Les parcours doivent réellement fonctionner.

### 14.1. Tests fonctionnels

- Un étudiant peut créer un compte et se connecter.
- Il peut démarrer un projet.
- Il peut enregistrer son sujet et ses réponses.
- Il peut fermer sa session et retrouver son travail.
- Il peut naviguer entre les étapes.
- Il peut consulter les ressources.
- Il peut interroger l'IA dans le contexte de son projet.
- Il peut modifier une réponse précédente.
- Il peut consulter son avancement.
- Il peut générer ou exporter les livrables prévus.
- Miss Koffi peut modifier une leçon depuis l'administration.
- Une modification publiée apparaît correctement dans le parcours étudiant.

### 14.2. Tests pédagogiques

Vérifier que :

- Les explications sont compréhensibles pour un débutant.
- Les étapes suivent une logique scientifique cohérente.
- Les objectifs, les questions et les méthodes sont cohérents entre eux.
- Les exemples ne sont pas présentés comme des données réelles lorsqu'ils sont fictifs.
- Les variantes méthodologiques sont correctement expliquées.
- Les consignes institutionnelles peuvent être prises en compte.
- L'étudiant sait quoi faire après chaque étape.

### 14.3. Tests de l'IA

Tester notamment :

- Les demandes imprécises.
- Les sujets trop larges.
- Les contradictions entre les réponses de l'étudiant.
- Les demandes de références inexistantes.
- Les demandes de données fabriquées.
- Les documents incomplets.
- Les interruptions du fournisseur d'IA.
- Les limites de consommation.
- La protection des informations personnelles.

### 14.4. Tests de sécurité

Vérifier :

- Qu'un étudiant ne peut pas consulter le projet privé d'un autre.
- Qu'un utilisateur non autorisé ne peut pas accéder à l'administration.
- Que les clés API ne sont pas exposées dans le navigateur.
- Que les fichiers importés sont contrôlés.
- Que les données peuvent être supprimées selon les règles définies.
- Que les sauvegardes peuvent réellement être restaurées.

### 14.5. Tests avec Miss Koffi

Elle doit réussir, sans intervention technique de l'équipe, à : ouvrir le site ; comprendre sa proposition de valeur ; créer un projet de démonstration ; parcourir plusieurs étapes ; utiliser l'assistant ; retrouver son travail ; modifier un contenu pédagogique dans l'administration ; comprendre comment signaler un problème.

Si elle ne peut pas réaliser ces actions après une prise en main raisonnable, l'expérience utilisateur doit être améliorée.

### 14.6. Conditions de mise en production

La mise en production est autorisée lorsque :

- Les parcours essentiels fonctionnent.
- Les anomalies bloquantes sont résolues.
- Les problèmes de sécurité critiques sont résolus.
- La sauvegarde et la restauration ont été testées.
- L'assistant respecte les règles de qualité définies.
- Miss Koffi a validé la version candidate.
- Les guides d'utilisation et d'administration sont disponibles.
- Les limites connues et les procédures de support sont documentées.

---

## 15. Livrables obligatoires

À la fin du projet, les agents doivent remettre :

- Le cahier des charges validé et ses éventuelles évolutions.
- Le référentiel pédagogique complet.
- Les maquettes et le prototype.
- L'application web fonctionnelle.
- Le code source versionné.
- La documentation de l'architecture.
- La documentation de la base de données.
- La documentation de l'intégration IA.
- Les tests automatisés pertinents.
- Le rapport de tests et les anomalies résolues.
- La version de production déployée.
- Les procédures de sauvegarde et de restauration.
- Le guide utilisateur étudiant.
- Le guide d'administration destiné à Miss Koffi.
- Le scénario de démonstration.
- Le compte rendu de validation.
- La liste des fonctionnalités reportées.
- Les informations nécessaires à la maintenance et à la reprise du projet.

Les comptes, accès et clés doivent être gérés de manière sécurisée. Les livrables ne doivent pas dépendre exclusivement d'un agent ou d'un prestataire.

---

## 16. Indicateurs de réussite

Les indicateurs doivent être suivis dès la phase pilote.

**Utilité pédagogique** : pourcentage d'étudiants qui terminent le parcours de démarrage ; pourcentage d'étudiants qui progressent d'une étape à la suivante ; nombre d'étudiants qui reprennent leur travail après une interruption ; satisfaction concernant la clarté des explications ; nombre d'étudiants qui comprennent mieux les étapes de la recherche.

**Qualité du produit** : taux de réussite des tests fonctionnels ; nombre d'anomalies bloquantes restantes ; fiabilité de la sauvegarde ; temps de réponse des fonctions essentielles ; disponibilité de l'assistant IA ; coût moyen de l'accompagnement par utilisateur.

**Autonomie de Miss Koffi** : capacité à modifier un contenu sans développeur ; capacité à tester le parcours étudiant ; capacité à comprendre les statistiques essentielles ; capacité à identifier les problèmes à transmettre à l'équipe technique.

Les objectifs chiffrés seront fixés après les premiers tests. Les indicateurs doivent servir à améliorer le produit, pas à afficher des performances non vérifiées.

---

## 17. Risques et mesures de prévention

| Risque | Mesure de prévention |
|---|---|
| L'IA invente des références | Vérification des sources et traçabilité |
| Les étudiants copient sans comprendre | Explications, questions guidées et exercices |
| Les consignes varient selon les établissements | Parcours adaptable et import éventuel des guides |
| L'étudiant abandonne en cours de route | Étapes courtes, sauvegarde et rappels adaptés |
| Le coût de l'IA devient trop élevé | Limites d'utilisation, suivi des coûts et optimisation |
| Le site est trop complexe pour Miss Koffi | Validation régulière et administration sans code |
| Les documents sont perdus | Sauvegardes, versions et tests de restauration |
| Les données personnelles sont exposées | Contrôle d'accès, confidentialité et minimisation des données |
| Le projet prend trop de temps | MVP priorisé et report explicite des fonctionnalités avancées |
| Les contenus pédagogiques sont erronés | Relecture spécialisée et processus éditorial |
| Le site promet des fonctions non opérationnelles | Démonstration fondée sur la version réellement testée |

---

## 18. Préparation de la présentation finale

La présentation doit être une démonstration concrète, pas seulement un exposé sur le développement.

Elle doit permettre à Miss Koffi de constater qu'un étudiant peut réellement être accompagné dans son travail.

Déroulement recommandé :

1. **Présentation du besoin** : expliquer les difficultés des étudiants et la réponse apportée par la plateforme.
2. **Découverte de l'interface** : montrer la page d'accueil et expliquer comment un étudiant commence son parcours.
3. **Démonstration du parcours** : créer un projet de démonstration et montrer comment l'étudiant passe du sujet à la problématique, puis aux autres étapes.
4. **Démonstration de l'IA** : demander une explication simple, une reformulation et une vérification de cohérence ; montrer comment l'assistant réagit lorsqu'il manque des informations ou qu'une référence doit être vérifiée.
5. **Démonstration de la sauvegarde** : quitter le projet, revenir et montrer que le travail est conservé.
6. **Démonstration de l'administration** : faire modifier une leçon ou un exemple par Miss Koffi elle-même.
7. **Présentation des tests** : expliquer les tests réalisés, les problèmes corrigés et les limites restantes.
8. **Prise de décision** : recueillir ses observations et convenir des améliorations prioritaires.

La démonstration doit utiliser des données fictives clairement identifiées et ne pas exposer de documents personnels d'étudiants.

---

## 19. Consignes finales aux agents

Le présent cahier des charges constitue le référentiel commun du projet.

Les agents doivent : étudier l'ensemble du document avant de commencer ; identifier les décisions encore ouvertes ; évaluer les ressources disponibles et l'existant technique ; proposer un plan de réalisation avec des priorités ; faire valider les maquettes avant le développement complet ; construire le MVP par incréments testables ; tester les fonctionnalités au fur et à mesure ; documenter les choix techniques et pédagogiques ; présenter régulièrement les résultats à Miss Koffi ; ne jamais déclarer une fonctionnalité terminée sans preuve de son fonctionnement ; signaler immédiatement les risques importants ; préparer une démonstration finale reproductible ; assurer le transfert de connaissances et la prise en main.

Aucune fonctionnalité ne doit être considérée comme acquise uniquement parce qu'elle apparaît dans une maquette ou dans une présentation.

La priorité est de livrer une plateforme utile, fiable, compréhensible et réellement utilisable par les étudiants.

---

## 20. Définition du succès du projet

Le projet sera considéré comme réussi lorsque trois conditions seront réunies :

- **Pour l'étudiant** : il peut comprendre les étapes de la méthodologie scientifique, avancer dans son mémoire, recevoir une aide contextualisée et retrouver son travail à tout moment.
- **Pour Miss Koffi** : elle peut présenter la plateforme, la faire essayer, comprendre son fonctionnement général et administrer les contenus courants sans dépendre systématiquement d'un technicien.
- **Pour l'équipe** : l'application est testée, documentée, sécurisée, maintenable et prête à évoluer.

La réussite ne se mesure pas au nombre de fonctionnalités annoncées ni à la quantité de texte que l'IA peut produire. Elle se mesure à la capacité réelle de la plateforme à aider un étudiant à réaliser un travail de recherche rigoureux, tout en comprenant ce qu'il fait et pourquoi il le fait.

**Décision attendue** : valider ce cahier des charges comme base de travail, puis lancer le cadrage opérationnel, la conception pédagogique et le prototype avant d'engager le développement complet.
