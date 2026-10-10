"""Inventaire et qualité des données (étage P1, SPEC §7.A et §9 étape 1)."""

from pydantic import Field

from .common import LenientModel, StrictModel, StrList


class VariableProfile(LenientModel):
    nom: str = ""
    nature: str = ""          # numerique | categorielle | texte | date
    type_valeurs: str = ""
    manquants: int = 0
    # Toute transformation est DÉCLARÉE, jamais silencieuse (SPEC §7.A).
    transformations: StrList = Field(default_factory=list)


class Inventory(StrictModel):
    datasets_resumes: StrList = Field(default_factory=list)
    variables: list[VariableProfile] = Field(default_factory=list)
    lignes: int = 0
    provenance: str = ""
    periode: str = ""
    # Déclarations de qualité : jamais masquées (SPEC §10.4).
    manquants: StrList = Field(default_factory=list)
    doublons: StrList = Field(default_factory=list)
    anomalies: StrList = Field(default_factory=list)
    donnees_personnelles: StrList = Field(default_factory=list)
    analyses_impossibles: StrList = Field(default_factory=list)
    provenance_analyse: str = "provided"
