"""Plan de conclusion (SPEC §9 étape 3)."""

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class PlanSection(LenientModel):
    titre: str = ""
    #: Fonction de la rubrique dans la conclusion (à quoi elle sert).
    fonction: str = ""
    contenu_prevu: str = ""
    retenue: bool = True


class ConclusionPlan(StrictModel):
    sections: list[PlanSection] = Field(default_factory=list)
    rubriques_ecartees: StrList = Field(default_factory=list)
    adaptation_consignes: str = ""
