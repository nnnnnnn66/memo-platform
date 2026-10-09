"""Analyse de la question, des objectifs et de la pertinence des hypothèses (SPEC §9.1-9.2)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class Provenance(str, Enum):
    provided = "provided"   # dit par l'étudiant / présent dans les entrées
    inferred = "inferred"   # interprétation de l'agent, à confirmer
    unknown = "unknown"     # non établi : jamais inventé


class HypothesisAnalysis(StrictModel):
    """Ce que l'agent dégage AVANT de décider si des hypothèses sont pertinentes."""

    phenomene: str = ""
    action_attendue: str = ""            # comprendre, décrire, comparer, expliquer, examiner…
    nature_du_travail: str = ""          # exploratoire / descriptif / compréhensif / explicatif…
    ambiguites: list[str] = Field(default_factory=list)
    provenance: Provenance = Provenance.unknown
