"""Agent Conclusion — étape 11 (paquet autonome), dernier agent du parcours.

Transforme les RÉSULTATS VÉRIFIÉS de l'étape 10 en une conclusion générale : réponse argumentée à la
question de recherche, bilan des objectifs et des hypothèses, apports, limites réelles, perspectives
justifiées — dans les limites de ce que les résultats permettent d'affirmer.

Règle structurante : **aucun résultat nouveau**. Chaque affirmation centrale renvoie au résultat qui la
justifie (identifiant `R…`), et aucun chiffre ne peut apparaître s'il ne provient pas des calculs
vérifiés. Sans résultats, la production se limite à un plan de conclusion.

Aucun code n'est partagé avec les autres agents : la duplication contrôlée est assumée.
"""

AGENT_ID = "research_conclusion_agent"
VERSION = "1.0"
