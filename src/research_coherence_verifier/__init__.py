"""Agent 13 — Vérificateur global de cohérence (paquet autonome), audit transversal du dossier.

Chaque étape du parcours possède son vérificateur : personne ne vérifie l'ENCHAÎNEMENT. Cet agent
confronte le dossier complet (étapes 1 à 11) à lui-même — découlement question/problématique, service
des objectifs, examinabilité des hypothèses par la méthodologie, couverture des objectifs par les
résultats, fidélité de la conclusion aux résultats — et détecte les contradictions et les fusions
abusives.

Deux règles structurantes :
- **le programme établit les faits (X1–X12), le modèle juge les liens** ;
- **aucun constat sans preuve, et la portée de l'audit est toujours déclarée** (ce que l'agent ne peut
  PAS vérifier : véracité du terrain, exactitude des sources, plagiat, style, règles locales non
  fournies, éthique de terrain, jugement du jury).

Aucun code n'est partagé avec les autres agents : la duplication contrôlée est assumée.
"""

AGENT_ID = "research_coherence_verifier"
VERSION = "1.0"
