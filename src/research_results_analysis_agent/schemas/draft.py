"""Proposition de rédaction de la section « Résultats et analyse » (étage P4)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel, StrList


class StatutAffirmation(str, Enum):
    etabli = "etabli"              # appuyé par un résultat calculé référencé
    a_confirmer = "a_confirmer"


class DraftSection(StrictModel):
    titre: str = ""
    contenu: str = ""
    statut: StatutAffirmation = StatutAffirmation.a_confirmer
    resultats: StrList = Field(default_factory=list)   # id des résultats cités


class ResultsDraft(StrictModel):
    sections: list[DraftSection] = Field(default_factory=list)
    # Contrat de passation 10 → 11 : la synthèse exploitable par l'Agent Conclusion.
    synthese_pour_conclusion: StrList = Field(default_factory=list)
    elements_a_confirmer: StrList = Field(default_factory=list)
