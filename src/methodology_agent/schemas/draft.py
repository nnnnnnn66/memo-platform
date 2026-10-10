"""Proposition de rédaction de la section « Méthodologie » (étage P4).

Chaque affirmation porte un statut : `prevu` (le protocole), `realise` (exige une PREUVE fournie par
l'étudiant) ou `a_confirmer`. Le contrôle déterministe P1 refuse tout passé sans preuve.
"""

from pydantic import Field

from .common import StrList, StrictModel
from .protocol import StatutAffirmation


class DraftSection(StrictModel):
    titre: str = ""
    contenu: str = ""
    statut: StatutAffirmation = StatutAffirmation.prevu


class MethodologyDraft(StrictModel):
    sections: list[DraftSection] = Field(default_factory=list)
    elements_a_confirmer: StrList = Field(default_factory=list)
