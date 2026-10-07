# Plateforme d'accompagnement méthodologique du mémoire (Master)

## Nature du projet
Plateforme web d'accompagnement méthodologique pour étudiants de Master réalisant un
mémoire de recherche. Elle n'écrit pas le mémoire à la place de l'étudiant : elle
accompagne son raisonnement, questionne, structure, détecte les manques et les
incohérences, et aide à améliorer progressivement.

## Architecture cible (rappel)
Étudiant → Plateforme web → Backend/API → Orchestrateur → Agent spécialisé →
Agent vérificateur → Résultat validé → Étape suivante → Vérification globale finale.

Hermes = environnement de construction / test / orchestration technique uniquement.
L'étudiant n'a jamais affaire à Hermes, au terminal, à Docker ou au serveur.

## Parcours méthodologique (13 étapes)
1. Sujet
2. Problème de recherche
3. Revue de littérature
4. Problématique
5. Question de recherche
6. Objectifs
7. Hypothèses (si pertinent)
8. Orientation méthodologique
9. Méthodologie
10. Résultats
11. Analyse / Discussion
12. Conclusion
13. Vérification globale de la cohérence

Règle absolue : **Problématique et Question de recherche restent deux éléments
distincts**, jamais fusionnés automatiquement.

## Stack retenue
Python + FastAPI. Emplacement du code : ce dossier.

## Méthode de construction (un agent à la fois)
Pour chaque agent, dans cet ordre :
1. définir sa mission ;
2. définir ses entrées ;
3. définir son processus de travail ;
4. définir ses sorties ;
5. définir ses contraintes ;
6. définir son vérificateur ;
7. créer l'architecture technique minimale ;
8. tester l'agent ;
9. corriger les problèmes ;
10. valider l'agent avant de passer au suivant.

Ne jamais construire toute la plateforme d'un coup. Un seul agent à la fois.

## État d'avancement
- [x] Cadrage général validé (ce document)
- [x] SPEC définitive Agent Sujet V1 reçue → `docs/spec-agent-sujet-v1.md` (référentiel canonique)
- [x] **Présentation d'architecture V1 (15 points, §42) → `docs/architecture-v1.md`** ← en attente de validation humaine
- [ ] Implémentation de l'Agent Sujet V1 (à démarrer après validation de l'architecture)
- [ ] Vérificateur
- [ ] Tests (§36–37)
- [ ] Validation de l'agent

