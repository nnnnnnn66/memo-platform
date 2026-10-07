"""Contrat de la phase 2 : notation et extraction par lots (une entrée par document)."""

from pydantic import Field, field_validator

from .common import StrictModel
from .document import AnchoredClaim, ExtractionScope


class DocumentAnalysis(StrictModel):
    doc_id: str
    relevance: float = 0.0
    theme: str = ""
    method: str = ""
    field_site: str = ""
    extraction_scope: ExtractionScope = ExtractionScope.metadata_only
    findings: list[AnchoredClaim] = Field(default_factory=list)
    limits: list[AnchoredClaim] = Field(default_factory=list)

    @field_validator("relevance")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class BatchAnalysis(StrictModel):
    agent: str = "literature_review_agent"
    version: str = "1.0"
    documents: list[DocumentAnalysis] = Field(default_factory=list)
