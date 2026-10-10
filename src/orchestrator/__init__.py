"""Orchestrateur de la plateforme — fait circuler les sorties RÉELLES d'une étape à la suivante.

Cette pièce n'appelle AUCUN modèle de langage et ne contient AUCUNE logique méthodologique :
elle tient le dossier d'un étudiant, décide quelle étape est ouverte, appelle l'agent concerné,
enregistre son verdict, et n'ouvre l'étape suivante qu'après une DÉCISION HUMAINE.
"""

__all__ = ["__version__"]

__version__ = "1.0"
