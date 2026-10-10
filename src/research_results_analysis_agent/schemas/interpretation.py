"""Interprétation et présentation des résultats (étage P3, SPEC §7.E-F-G)."""

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class Lecture(LenientModel):
    """Une lecture : observation → objectif → interprétation prudente → limites (SPEC §7.F)."""

    id_resultat: str = ""
    observation: str = ""
    objectif: str = ""
    interpretation: str = ""
    autres_explications: StrList = Field(default_factory=list)
    limites: StrList = Field(default_factory=list)


class TableauDescription(LenientModel):
    """Un tableau DÉCRIT (jamais un tableau de valeurs inventées) : titre, variables, unités, lecture."""

    titre: str = ""
    variables: StrList = Field(default_factory=list)
    unites: StrList = Field(default_factory=list)
    effectif: int = 0
    lecture: str = ""
    resultats: StrList = Field(default_factory=list)


class FigureDescription(LenientModel):
    titre: str = ""
    variables: StrList = Field(default_factory=list)
    unites: StrList = Field(default_factory=list)
    lecture: str = ""
    resultats: StrList = Field(default_factory=list)


class CompareLitterature(LenientModel):
    resultat: str = ""
    lien: str = ""
    source: str = ""             # doit exister dans le dossier fourni, sinon l'absence est déclarée


class Interpretation(StrictModel):
    lectures: list[Lecture] = Field(default_factory=list)
    tableaux: list[TableauDescription] = Field(default_factory=list)
    figures: list[FigureDescription] = Field(default_factory=list)
    comparaison_litterature: list[CompareLitterature] = Field(default_factory=list)
    resultats_inattendus: StrList = Field(default_factory=list)
    limites_analyse: StrList = Field(default_factory=list)
    points_non_resolus: StrList = Field(default_factory=list)
