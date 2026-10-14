"""Contrat d'entrée de l'Agent Sujet (SPEC §8)."""

from pydantic import BaseModel, ConfigDict, Field


class SubjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None
    subject_text: str
    student_context: str = ""
    discipline: str = ""
    academic_level: str = ""
    country: str = ""
    institution: str = ""
    previous_answers: list[str] = Field(default_factory=list)
    additional_constraints: str = ""

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables (§21)."""
        return {
            "subject_text": self.subject_text,
            "student_context": self.student_context,
            "discipline": self.discipline,
            "academic_level": self.academic_level,
            "country": self.country,
            "institution": self.institution,
            "additional_constraints": self.additional_constraints,
        }


class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
