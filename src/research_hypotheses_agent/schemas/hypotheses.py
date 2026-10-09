"""Contrats des hypothèses : décision, hypothèses, alignement, support, preuves (SPEC §4, §16)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class DecisionCode(str, Enum):
    recommended = "HYPOTHESES_RECOMMENDED"
    not_required = "HYPOTHESES_NOT_REQUIRED"
    require_clarification = "HYPOTHESES_REQUIRE_CLARIFICATION"


class Hypothesis(StrictModel):
    """Une hypothèse = une PROPOSITION À EXAMINER (jamais une réponse ni un fait établi)."""

    id: str = ""
    formulation: str = ""
    linked_to: str = ""                              # question ou objectif concerné
    concepts_variables: list[str] = Field(default_factory=list)
    justification: str = ""
    sources: list[str] = Field(default_factory=list)
    required_data: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)


class HypothesisObjectiveAlignment(StrictModel):
    """Chaîne « Question → Objectifs → Hypothèses éventuelles » (SPEC §10.D)."""

    general_to_objectives: str = ""
    hypotheses_cover_objectives: str = ""
    uncovered_objectives: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


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
