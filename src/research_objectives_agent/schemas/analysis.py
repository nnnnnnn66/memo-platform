"""Analyse de la question de recherche (SPEC §9.1)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class Provenance(str, Enum):
    provided = "provided"   # dit par l'étudiant / présent dans les entrées
    inferred = "inferred"   # interprétation de l'agent, à confirmer
    unknown = "unknown"     # non établi : jamais inventé


class QuestionAnalysis(StrictModel):
    """Ce que l'agent dégage de la question AVANT de fixer des objectifs (étape 1 de la SPEC)."""

    phenomene: str = ""
    action_attendue: str = ""            # action intellectuelle attendue (décrire, expliquer…)
    dimensions: list[str] = Field(default_factory=list)   # dimensions à examiner
    perimetre: str = ""                  # périmètre de la recherche
    ambiguites: list[str] = Field(default_factory=list)   # ce qui empêche de définir des objectifs
    provenance: Provenance = Provenance.unknown
