"""Contrat de sortie de l'Agent Revue de littérature (SPEC §3, §4, §7, §16)."""

from enum import Enum

from pydantic import Field

from .common import Confidence, Scope, StrictModel, SubjectReference, Validation
from .diagnosis import Diagnosis
from .document import DocumentRecord


class ReviewStatus(str, Enum):
    needs_clarification = "needs_clarification"
    ready_for_verification = "ready_for_verification"
    blocked = "blocked"


class CorpusSufficiency(str, Enum):
    sufficient = "sufficient"
    partial = "partial"
    insufficient = "insufficient"


class Corpus(StrictModel):
    documents: list[DocumentRecord] = Field(default_factory=list)
    documents_count: int = 0
    corpus_sufficiency: CorpusSufficiency = CorpusSufficiency.insufficient
    duplicates_removed: int = 0
    providers_used: list[str] = Field(default_factory=list)
    providers_failed: list[dict] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    by_language: dict[str, int] = Field(default_factory=dict)
    by_geography: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)
    full_text_downloaded: int = 0


class ThemeComparison(StrictModel):
    theme: str = ""
    doc_ids: list[str] = Field(default_factory=list)
    convergences: list[str] = Field(default_factory=list)
    divergences: list[str] = Field(default_factory=list)
    limits: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class Comparison(StrictModel):
    themes: list[ThemeComparison] = Field(default_factory=list)
    methods_used: list[str] = Field(default_factory=list)
    results_summary: list[str] = Field(default_factory=list)


class Synthesis(StrictModel):
    state_of_knowledge: str = ""
    authors_and_schools: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    caution_notes: list[str] = Field(default_factory=list)


class Bibliography(StrictModel):
    style: str = "apa7"
    entries: list[str] = Field(default_factory=list)
    entries_count: int = 0


class ReviewOutput(StrictModel):
    agent: str = "literature_review_agent"
    version: str = "1.0"
    status: ReviewStatus
    subject_reference: SubjectReference = Field(default_factory=SubjectReference)
    scope: Scope = Field(default_factory=Scope)
    keywords: dict = Field(default_factory=dict)
    corpus: Corpus = Field(default_factory=Corpus)
    comparison: Comparison = Field(default_factory=Comparison)
    synthesis: Synthesis = Field(default_factory=Synthesis)
    diagnosis: Diagnosis = Field(default_factory=Diagnosis)
    bibliography: Bibliography = Field(default_factory=Bibliography)
    unknowns: list[str] = Field(default_factory=list)
    limits_of_this_review: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    validation: Validation = Field(default_factory=Validation)

    def documents_by_id(self) -> dict[str, DocumentRecord]:
        return {d.doc_id: d for d in self.corpus.documents}
