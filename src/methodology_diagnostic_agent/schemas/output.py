"""Contrat de sortie de l'Agent Diagnostic méthodologique (SPEC §16)."""

from enum import Enum

from pydantic import Field

from .analysis import DossierAnalysis
from .common import Confidence, StrictModel, Validation
from .decision import StudentValidation
from .methodology import (
    Ambiguity,
    DiagnosticStatusEnum,
    MethodologyDiagnosis,
    SourceEvidence,
)


class MethodologyStatus(str, Enum):
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


class MethodologyOutput(StrictModel):
    agent: str = "methodology_diagnostic_agent"
    version: str = "1.0"
    status: MethodologyStatus

    # dossier de preuve (SPEC §16)
    research_id: str = ""                       # student_id/session_id
    dossier_versions: dict = Field(default_factory=dict)
    generated_at: str = ""
    diagnostic_status: DiagnosticStatusEnum = DiagnosticStatusEnum.provisoire
    provisional: bool = True

    # résumé du dossier examiné
    subject: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)
    hypotheses_examined: list[str] = Field(default_factory=list)
    resume: str = ""

    # le diagnostic
    analysis: DossierAnalysis = Field(default_factory=DossierAnalysis)
    diagnosis: MethodologyDiagnosis = Field(default_factory=MethodologyDiagnosis)
    alternatives_overview: list[str] = Field(default_factory=list)
    coherence_controls: list[str] = Field(default_factory=list)
    feasibility_controls: list[str] = Field(default_factory=list)

    # honnêteté et preuves
    missing_information: list[str] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    tools_and_documents: list[str] = Field(default_factory=list)
    questions_for_human: list[str] = Field(default_factory=list)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    verification_result: Validation = Field(default_factory=Validation)
    student_validation: StudentValidation = Field(default_factory=StudentValidation)
    confidence: Confidence = Field(default_factory=Confidence)

    # champs propres à l'accompagnement
    clarification_questions: list[str] = Field(default_factory=list)
    limits_of_this_output: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence: Evidence = Field(default_factory=Evidence)
