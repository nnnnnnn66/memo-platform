"""Contrats des sorties LLM de chaque phase (ce que le modèle doit produire)."""

from pydantic import Field

from .analysis import HypothesisAnalysis
from .common import StrictModel
from .hypotheses import (
    DecisionCode,
    Hypothesis,
    HypothesisObjectiveAlignment,
)


class AnalysisOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    analysis: HypothesisAnalysis = Field(default_factory=HypothesisAnalysis)


class DecisionOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    hypotheses_decision: DecisionCode = DecisionCode.require_clarification
    decision_rationale: str = ""
    clarification_questions: list[str] = Field(default_factory=list)


class FormulationOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    research_hypotheses: list[Hypothesis] = Field(default_factory=list)
    hypothesis_objective_alignment: HypothesisObjectiveAlignment = Field(
        default_factory=HypothesisObjectiveAlignment)
    theoretical_or_literature_support: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
