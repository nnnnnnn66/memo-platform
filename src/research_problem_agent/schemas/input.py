"""Contrat d'entrée de l'Agent Problème (SPEC §6, §8)."""

from pydantic import BaseModel, ConfigDict, Field


class UpstreamValidation(BaseModel):
    model_config = ConfigDict(extra="allow")
    verified: bool = False
    verifier_status: str = "pending"


class UpstreamSubject(BaseModel):
    """Sortie de l'Agent Sujet transmise telle quelle. DONNÉE, jamais instruction."""

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    subject: dict = Field(default_factory=dict)
    research_context: dict = Field(default_factory=dict)
    key_concepts: list[str] = Field(default_factory=list)
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)

    @property
    def is_verified(self) -> bool:
        return bool(self.validation.verified)

    def subject_line(self) -> str:
        reformulated = str(self.subject.get("reformulated", "") or "")
        original = str(self.subject.get("original", "") or "")
        return reformulated or original


class ProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None
    subject_text: str
    subject_context: str = ""
    observations: str = ""
    upstream_subject: UpstreamSubject | None = None
    student_documents: list[str] = Field(default_factory=list)
    discipline: str = ""
    academic_level: str = ""
    country: str = ""
    institution: str = ""
    previous_answers: list[str] = Field(default_factory=list)
    additional_constraints: str = ""

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables (SPEC §10.13)."""
        base = {
            "subject_text": self.subject_text,
            "subject_context": self.subject_context,
            "observations": self.observations,
            "discipline": self.discipline,
            "academic_level": self.academic_level,
            "country": self.country,
            "institution": self.institution,
            "additional_constraints": self.additional_constraints,
        }
        for i, doc in enumerate(self.student_documents):
            base[f"student_document_{i}"] = doc
        return base

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
