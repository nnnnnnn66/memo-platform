# Spécification du site web — Plateforme d'accompagnement méthodologique

> **Statut** : proposition à valider par le porteur. Décrit **ce que l'étudiant voit et fait**.
> Aucun code n'est écrit avant validation de l'architecture (portillon §42).
> Décisions appliquées faute d'objection : accès **sur invitation** · encadreur **sans accès au
> dossier** · conservation **durée du mémoire + 2 ans** · **5 à 10 étudiants** au démarrage ·
> **20 analyses/jour/étudiant**.

---

## 1. Ce que le site est — et n'est pas

**C'est** l'unique interface entre l'étudiant et les 12 agents : il pose ses questions, reçoit une
proposition par étape, **décide**, consulte ses documents et exporte son dossier.

**Ce n'est pas** : un générateur de mémoire (l'agent questionne, il n'écrit pas à sa place), ni une
interface technique (l'étudiant ne voit **jamais** de terminal, de port, de JSON, de nom d'agent).

---

## 2. Les écrans (8, pas plus)

### É1 — Connexion / invitation
- L'étudiant reçoit un **lien d'invitation** (pas d'inscription libre).
- Création du mot de passe (règle simple : 10 caractères minimum).
- Message en cas d'échec : « Identifiant ou mot de passe incorrect. » (jamais « ce compte n'existe
  pas » : cela révélerait qui est inscrit).

### É2 — Mes mémoires
- La liste de ses mémoires (un étudiant peut en avoir plusieurs).
- Bouton **« Nouveau mémoire »** → sujet + contexte (discipline, pays, zone, période).

### É3 — Mon parcours (l'écran central)
- La **barre des 13 étapes**, avec pour chacune son état : **à faire / en cours / en attente de ta
  décision / validée / à réviser**.
- L'étape ouverte est mise en avant ; les suivantes sont **fermées** et le disent.

### É4 — L'étape en cours
C'est ici que tout se joue. Le site affiche, **dans cet ordre** :
1. **La proposition** de l'agent pour cette étape (le document produit).
2. **Ce qui reste inconnu** (`unknowns`) — en évidence, jamais caché.
3. **Les limites** de cette proposition (`limits_of_this_output`).
4. **Les questions posées à l'étudiant** (`questions_for_human`) → il répond dans un formulaire.
5. **Le verdict du vérificateur** de l'agent, affiché tel quel.
6. **Les deux boutons** : **« Je valide »** et **« Demander une révision »** (+ commentaire libre).

### É5 — Mes documents
- Les **PDF réellement téléchargés** par la revue de littérature, avec leur statut d'accès.
- Pour les documents non récupérables : **leur lien officiel** + la mention « texte intégral non
  récupéré ».
- **« Télécharger ma bibliographie »** : BibTeX, RIS ou CSV.
- Chaque lien est **vérifié avant affichage** : jamais un lien mort.

### É6 — Le journal de mon parcours
- L'historique lisible : « Étape 3 — Revue de littérature — en ligne le 12/10, validée le 14/10 ».
- C'est la **traçabilité** demandée par le lab : voir ce qui s'est passé, sans jargon.

### É7 — Export de mon dossier
- Un fichier contenant les 13 étapes, les réponses, les sources et les validations.
- Disponible **à tout moment** (pas seulement à la fin).

### É8 — Tableau de bord (toi, administrateur — jamais l'étudiant)
- **Agents en ligne / éteints** (repris du lab : `/health` des 12 agents, rafraîchi).
- **Avancement des étudiants** et **consommation du quota** (protection de ton portefeuille).
- **Derniers événements** : quelle étape a été lancée, par qui, quand, avec quel verdict.

---

## 3. Le parcours type, de bout en bout

1. L'étudiant ouvre son lien d'invitation et crée son mot de passe.
2. Il crée son mémoire : sujet + contexte.
3. **Étape 1 — Sujet** : il lance l'étape (ou répond d'abord), lit la proposition, **valide** ou
   demande une révision.
4. L'étape 2 s'ouvre **seulement après sa validation**. Et ainsi de suite.
5. À l'étape 3, il **télécharge** les articles trouvés et sa bibliographie.
6. À l'étape 10, il fournit ses données ; **les calculs sont faits par le code**, jamais par le
   modèle.
7. Après l'étape 11, la **vérification globale** (étape 13) passe le dossier au crible.
8. Il exporte son dossier complet.

---

## 4. Règles de conduite du site (non négociables)

| Règle | Pourquoi |
|---|---|
| **Rien n'est validé sans son clic** | `validated` ne vient jamais d'un agent |
| **Les inconnues et les limites sont toujours visibles** | honnêteté du produit |
| **Un lien de téléchargement n'est affiché que s'il a été vérifié** | jamais de lien mort |
| **Un étudiant ne voit que ses dossiers** | isolation stricte |
| **Le quota est affiché** (« il te reste 17 analyses aujourd'hui ») | pas de refus surprise |
| **Aucun jargon** : « le service de cette étape est éteint », pas « HTTP 502 » | l'étudiant n'est pas technicien |

---

## 5. Cas d'erreur et messages (rédigés à l'avance)

| Situation | Ce que l'étudiant lit |
|---|---|
| Agent de l'étape éteint | « Le service de cette étape est éteint pour le moment. Ton dossier est conservé : tu pourras relancer dès qu'il sera rallumé. » |
| Étape qui n'aboutit pas | « Cette étape n'a pas pu aboutir. Rien n'a été validé ; tu peux la relancer. » |
| Quota atteint | « Tu as atteint tes 20 analyses du jour. Ton dossier est conservé : tu peux reprendre demain. » |
| Étape suivante demandée trop tôt | « L'étape précédente doit d'abord être validée. » |
| Déconnexion | « Ta session a expiré. Reconnecte-toi — ton travail est enregistré. » |

**Jamais** : une trace technique, un nom de fichier, une adresse IP, un code d'erreur brut.

---

## 6. Ce que l'étudiant ne voit JAMAIS

- Les 12 agents, leurs noms, leurs ports, leurs API.
- L'orchestrateur, la base de données, le serveur.
- Hermes, le terminal, les journaux d'exécution.
- Les clés, les prompts, les fichiers internes.
- Le dossier d'un autre étudiant.

---

## 7. Critères d'acceptation (le site est prêt quand…)

1. Un étudiant fait les **13 étapes sans jamais voir** de terminal, de port ou de JSON.
2. Chaque étape affiche : proposition, **inconnues**, limites, questions, verdict.
3. `validated` ne peut venir **que** d'un clic humain.
4. Aucun étudiant ne peut lire le dossier d'un autre (vérifié par test).
5. Un agent éteint produit un **message clair**, sans perdre le dossier.
6. Le quota est **visible** et un dépassement est refusé **proprement**.
7. Les téléchargements fonctionnent (documents + bibliographie) et **aucun lien n'est mort**.
8. Le tableau de bord administrateur montre les agents en ligne et la consommation.
9. Tout est en **HTTPS** ; aucun secret dans une URL ou un journal.
10. La **sauvegarde et la restauration** ont été testées pour de vrai.

---

## 8. Ce qui reste à décider par le porteur

| # | Question | Proposition |
|---|---|---|
| 1 | Nom de domaine / nom public du site | *(à préciser — provisoire : `memo.<domaine>`)* |
| 2 | Export du dossier : **archive unique** ou élément par élément ? | les deux : archive + accès direct |
| 3 | Le site doit-il parler **arabe** ou seulement français ? | **français** au démarrage |
| 4 | Les étudiants voient-ils le **journal technique** complet ou seulement leur parcours ? | **leur parcours** seulement |

---

**Suite (étape 2)** : l'architecture V1 du site en 15 points, à valider avant toute ligne de code.
