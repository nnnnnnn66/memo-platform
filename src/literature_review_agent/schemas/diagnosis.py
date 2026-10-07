"""Contrat du diagnostic méthodologique et de l'alignement épistémologique (SPEC §4.4A)."""

from enum import Enum

from pydantic import Field

from .common import Confidence, StrictModel


class ReasoningLogic(str, Enum):
    inductive = "inductive"
    deductive = "deductive"
    hypothetico_deductive = "hypothetico_deductive"
    abductive = "abductive"
    mixed = "mixed"


class ResearchType(str, Enum):
    exploratory = "exploratory"
    confirmatory = "confirmatory"
    explanatory = "explanatory"
    descriptive = "descriptive"
    correlational = "correlational"
    phenomenological = "phenomenological"
    comparative = "comparative"
    experimental = "experimental"
    quasi_experimental = "quasi_experimental"
    mixed = "mixed"


class Approach(str, Enum):
    qualitative = "qualitative"
    quantitative = "quantitative"
    mixed_methods = "mixed_methods"


class DiagnosisStatus(str, Enum):
    proposal_to_validate_with_student = "proposal_to_validate_with_student"


class Diagnosis(StrictModel):
    matrix_row_id: str = ""                    # identifiant d'une ligne de la matrice §4.4A
    matrix_row_label: str = ""
    semantic_indicators: list[str] = Field(default_factory=list)   # formulations repérées dans le sujet
    reasoning_logic: ReasoningLogic = ReasoningLogic.mixed
    research_type: ResearchType = ResearchType.mixed
    approach: Approach = Approach.mixed_methods
    techniques: list[str] = Field(default_factory=list)
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)
    alignment_alerts: list[str] = Field(default_factory=list)
    evidence_from_corpus: str = ""             # ce que l'état des connaissances du corpus suggère
    missing_to_decide: list[str] = Field(default_factory=list)
    status: DiagnosisStatus = DiagnosisStatus.proposal_to_validate_with_student
    confidence: Confidence = Field(default_factory=Confidence)
