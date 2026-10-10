"""Agent Résultats et analyse — étape 10 (paquet autonome).

Traite les données RÉELLEMENT collectées (ou les documents effectivement étudiés) conformément à la
méthodologie validée de l'étape 9 : inventaire et qualité des données, analyse, présentation,
interprétation prudente, examen des hypothèses, limites — puis rédaction de la section « Résultats et
analyse » et synthèse exploitable par l'étape 11 (Conclusion).

Principe fondateur : **les chiffres viennent du CODE**. Le moteur déterministe
(`analysis/data_engine.py`) calcule ; le modèle lit et interprète. Aucun résultat ne peut être inventé :
tout chiffre publié est vérifié contre la liste blanche des valeurs réellement calculées.

Aucun code n'est partagé avec les autres agents : la duplication contrôlée est assumée.
"""

AGENT_ID = "research_results_analysis_agent"
VERSION = "1.0"
