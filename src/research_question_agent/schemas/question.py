"""Contrats de la proposition de question : périmètre, faisabilité, ambiguïtés, sources."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class ScopeAndBoundaries(StrictModel):
    geo: str = ""
    temps: str = ""
    population: str = ""
    added_without_source: bool = False


class FeasibilityVerdict(str, Enum):
    feasible = "feasible"
    uncertain = "uncertain"
    not_feasible = "not_feasible"


class FeasibilityAssessment(StrictModel):
    verdict: FeasibilityVerdict = FeasibilityVerdict.uncertain
    raisons: list[str] = Field(default_factory=list)
    manques: list[str] = Field(default_factory=list)


class FormulationRationale(StrictModel):
    texte: str = ""
    rattachement_problematique: str = ""


class Ambiguity(StrictModel):
    description: str = ""
    impact: str = ""
    clarification_question: str = ""


class SourceEvidence(StrictModel):
    """Preuve documentaire (clarification optionnelle). Un `source_id` doit venir d'un appel réel."""

    query: str = ""
    provider: str = ""
    source_id: str = ""
    title: str = ""
    url: str = ""
    used: bool = False


class ResearchQuestion(StrictModel):
    main: str = ""
    secondary: list[str] = Field(default_factory=list)
    status: str = "proposed"
