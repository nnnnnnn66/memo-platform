"""Contrat de sortie de l'Agent Objectifs de recherche (SPEC §16)."""

from enum import Enum

from pydantic import Field

from .analysis import QuestionAnalysis
from .common import Confidence, StrictModel, Validation
from .decision import StudentValidation
from .objectives import (
    Ambiguity,
    FeasibilityAssessment,
    QuestionObjectiveAlignment,
    ScopeAndBoundaries,
    SourceEvidence,
)


class ObjectiveStatus(str, Enum):
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


class ObjectivesOutput(StrictModel):
    agent: str = "research_objectives_agent"
    version: str = "1.0"
    status: ObjectiveStatus

    subject: str = ""
    validated_problematic: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    question_analysis: QuestionAnalysis = Field(default_factory=QuestionAnalysis)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)
    objective_rationale: str = ""
    question_objective_alignment: QuestionObjectiveAlignment = Field(
        default_factory=QuestionObjectiveAlignment)
    scope_and_boundaries: ScopeAndBoundaries = Field(default_factory=ScopeAndBoundaries)
    feasibility_assessment: FeasibilityAssessment = Field(default_factory=FeasibilityAssessment)
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
