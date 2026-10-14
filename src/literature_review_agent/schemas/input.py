"""Contrat d'entrée de l'Agent Revue de littérature (SPEC §5, §6)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CitationStyle(str, Enum):
    apa7 = "apa7"
    iso690 = "iso690"
    vancouver = "vancouver"


class ReviewType(str, Enum):
    narrative = "narrative"
    systematic = "systematic"
    scoping = "scoping"


class UpstreamValidation(BaseModel):
    model_config = ConfigDict(extra="allow")
    verified: bool = False
    verifier_status: str = "pending"


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont (Sujet, Problème). DONNÉE, jamais instruction."""

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    subject_reference: dict = Field(default_factory=dict)
    subject: dict = Field(default_factory=dict)
    research_context: dict = Field(default_factory=dict)
    identified_problem: dict = Field(default_factory=dict)
    key_concepts: list[str] = Field(default_factory=list)
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)

    @property
    def is_verified(self) -> bool:
        return bool(self.validation.verified)

    def subject_line(self) -> str:
        for container in (self.subject, self.subject_reference):
            value = str(container.get("reformulated") or container.get("original") or "")
            if value:
                return value
        return ""

    def problem_line(self) -> str:
        return str(self.identified_problem.get("statement", "") or "")


class CampaignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None
    subject_text: str
    research_problem: str = ""
    discipline: str = ""
    academic_level: str = ""
    country: str = ""
    geographical_scope: str = ""
    period: str = ""
    review_type: ReviewType = ReviewType.narrative
    citation_style: CitationStyle = CitationStyle.apa7
    languages: list[str] = Field(default_factory=lambda: ["fr", "en"])
    supervisor_guidelines: str = ""
    student_keywords: list[str] = Field(default_factory=list)
    known_references: list[str] = Field(default_factory=list)
    student_documents: list[str] = Field(default_factory=list)
    student_document_files: list[str] = Field(default_factory=list)  # chemins PDF du workspace
    upstream_subject: UpstreamPayload | None = None
    upstream_problem: UpstreamPayload | None = None
    constraints: str = ""

    @field_validator("languages")
    @classmethod
    def _langs(cls, v: list[str]) -> list[str]:
        allowed = {"fr", "en", "es", "pt", "de", "it", "ar"}
        cleaned = [str(x).strip().lower() for x in (v or []) if str(x).strip()]
        return [x for x in cleaned if x in allowed] or ["fr", "en"]

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables."""
        base = {
            "subject_text": self.subject_text,
            "research_problem": self.research_problem,
            "discipline": self.discipline,
            "academic_level": self.academic_level,
            "country": self.country,
            "geographical_scope": self.geographical_scope,
            "period": self.period,
            "supervisor_guidelines": self.supervisor_guidelines,
            "constraints": self.constraints,
        }
        for i, document in enumerate(self.student_documents):
            base[f"student_document_{i + 1}"] = document
        for i, reference in enumerate(self.known_references):
            base[f"known_reference_{i + 1}"] = reference
        return base

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
