"""Contrats des objectifs : périmètre, faisabilité, alignement, ambiguïtés (SPEC §4, §16)."""

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


class QuestionObjectiveAlignment(StrictModel):
    """Chaîne « Question → Objectif général → Objectifs spécifiques → Données » (SPEC §9.4)."""

    general_to_question: str = ""            # en quoi l'objectif général répond à la question
    specifics_cover_general: str = ""        # comment les OS décomposent l'OG
    secondary_questions_coverage: list[str] = Field(default_factory=list)  # question sec. → OS
    uncovered_dimensions: list[str] = Field(default_factory=list)          # dimensions non couvertes


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
