"""Contrat de sortie de l'Agent Hypothèses de recherche (SPEC §16)."""

from enum import Enum

from pydantic import Field

from .analysis import HypothesisAnalysis
from .common import Confidence, StrictModel, Validation
from .decision import StudentValidation
from .hypotheses import (
    Ambiguity,
    DecisionCode,
    Hypothesis,
    HypothesisObjectiveAlignment,
    SourceEvidence,
)


class HypothesisStatus(str, Enum):
    needs_clarification = "needs_clarification"
    ready_for_verification = "ready_for_verification"
    verification_failed = "verification_failed"
    awaiting_human_validation = "awaiting_human_validation"
    blocked = "blocked"
    validated = "validated"


class Evidence(StrictModel):
    llm_calls: int = 0
    network_requests: int = 0
    reformulations: int = 0


class HypothesesOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    status: HypothesisStatus

    subject: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)
    analysis: HypothesisAnalysis = Field(default_factory=HypothesisAnalysis)
    hypotheses_decision: DecisionCode = DecisionCode.require_clarification
    decision_rationale: str = ""
    research_hypotheses: list[Hypothesis] = Field(default_factory=list)
    hypothesis_objective_alignment: HypothesisObjectiveAlignment = Field(
        default_factory=HypothesisObjectiveAlignment)
    theoretical_or_literature_support: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    verification_result: Validation = Field(default_factory=Validation)
    student_validation: StudentValidation = Field(default_factory=StudentValidation)
    confidence: Confidence = Field(default_factory=Confidence)

    # champs propres à l'accompagnement (hors SPEC §16, utiles au workflow)
    clarification_questions: list[str] = Field(default_factory=list)
    limits_of_this_output: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence: Evidence = Field(default_factory=Evidence)
