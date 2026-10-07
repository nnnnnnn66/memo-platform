"""Contrat de sortie de l'Agent Problématique (SPEC §4, §9)."""

from enum import Enum

from pydantic import Field

from .alignment import MethodologicalAlignment
from .common import Confidence, Scope, StrictModel, SubjectReference, Validation
from .confrontation import LiteratureConfrontation
from .gap import Gap
from .problem import ProblemMapping
from .question import ObjectivesCandidate, ResearchQuestionCandidate
from .statement import AnchoredStatement


class ProblemStatus(str, Enum):
    needs_clarification = "needs_clarification"
    ready_for_verification = "ready_for_verification"
    blocked = "blocked"


class Justification(StrictModel):
    texte: str = ""
    statements: list[AnchoredStatement] = Field(default_factory=list)


class ProblematiqueNote(StrictModel):
    sections: list[str] = Field(default_factory=list)   # sections rédigées, dans l'ordre
    texte_complet: str = ""


class Bibliography(StrictModel):
    style: str = "apa7"
    entries: list[str] = Field(default_factory=list)
    entries_count: int = 0


class Evidence(StrictModel):
    statements_written: int = 0
    statements_anchored: int = 0
    statements_removed: int = 0
    documents_read: int = 0
    documents_total: int = 0
    llm_calls: int = 0
    network_requests: int = 0


class ProblematizationOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    status: ProblemStatus
    subject_reference: SubjectReference = Field(default_factory=SubjectReference)
    scope: Scope = Field(default_factory=Scope)
    problem_mapping: ProblemMapping = Field(default_factory=ProblemMapping)
    literature_confrontation: LiteratureConfrontation = Field(
        default_factory=LiteratureConfrontation)
    gap: Gap = Field(default_factory=Gap)
    justification: Justification = Field(default_factory=Justification)
    problematique_note: ProblematiqueNote = Field(default_factory=ProblematiqueNote)
    research_question: ResearchQuestionCandidate = Field(default_factory=ResearchQuestionCandidate)
    objectives: ObjectivesCandidate = Field(default_factory=ObjectivesCandidate)
    methodological_alignment: MethodologicalAlignment = Field(
        default_factory=MethodologicalAlignment)
    bibliography: Bibliography = Field(default_factory=Bibliography)
    unknowns: list[str] = Field(default_factory=list)
    limits_of_this_note: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    evidence: Evidence = Field(default_factory=Evidence)
    confidence: Confidence = Field(default_factory=Confidence)
    validation: Validation = Field(default_factory=Validation)
