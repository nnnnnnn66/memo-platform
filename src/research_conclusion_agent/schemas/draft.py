"""Brouillon de conclusion (SPEC §9 étape 4)."""

from enum import Enum

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class NiveauAffirmation(str, Enum):
    """Ce que dit l'affirmation : un CONSTAT des résultats, une INTERPRÉTATION, ou une PERSPECTIVE."""

    constat = "constat"
    interpretation = "interpretation"
    perspective = "perspective"


class DraftSection(LenientModel):
    titre: str = ""
    contenu: str = ""
    fonction: str = ""                       # à quoi sert cette partie du texte
    niveau: NiveauAffirmation = NiveauAffirmation.constat
    justification: str = ""                   # pourquoi cette affirmation est justifiée
    resultats: StrList = Field(default_factory=list)   # identifiants R… qui l'appuient


class ConclusionDraft(StrictModel):
    sections: list[DraftSection] = Field(default_factory=list)
    apports_scientifiques: StrList = Field(default_factory=list)
    apports_pratiques: StrList = Field(default_factory=list)
    limites: StrList = Field(default_factory=list)
    perspectives: StrList = Field(default_factory=list)
    points_a_confirmer: StrList = Field(default_factory=list)
