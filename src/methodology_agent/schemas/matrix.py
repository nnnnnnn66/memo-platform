"""Matrice de cohérence (étage P3) : chaque objectif relié aux données, à la collecte et à l'analyse.

Construite DÉTERMINISTEMENT depuis les objectifs vérifiés de l'agent 6 (une ligne par objectif) ;
le modèle ne fait que la remplir. Un objectif sans ligne est impossible (règle R4).
"""

from enum import Enum

from pydantic import Field

from .common import StrictModel, StrList


class Couverture(str, Enum):
    couverte = "couverte"
    partielle = "partielle"
    non_couverte = "non_couverte"


class MatrixRow(StrictModel):
    objectif: str = ""
    donnees_necessaires: StrList = Field(default_factory=list)
    techniques: StrList = Field(default_factory=list)
    analyses: StrList = Field(default_factory=list)
    statut: Couverture = Couverture.non_couverte
    remarque: str = ""


class CoherenceMatrix(StrictModel):
    lignes: list[MatrixRow] = Field(default_factory=list)
