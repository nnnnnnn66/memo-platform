"""Contrat de sortie de l'Agent Sujet (SPEC §10). Schéma strict (extra=forbid)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubjectStatus(str, Enum):
    needs_clarification = "needs_clarification"
    ready_for_verification = "ready_for_verification"
    blocked = "blocked"


class SourceType(str, Enum):
    user = "user"
    external = "external"
    model_inference = "model_inference"


class VerificationStatus(str, Enum):
    verified = "verified"
    not_verified = "not_verified"


class FeasibilityStatus(str, Enum):
    unknown = "unknown"
    ok = "ok"
    concerning = "concerning"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubjectCore(_Strict):
    original: str = ""
    reformulated: str = ""


class ResearchContext(_Strict):
    domain: str = ""
    object_of_study: str = ""
    population: str = ""
    geographical_scope: str = ""
    temporal_scope: str = ""
    phenomenon: str = ""


class Feasibility(_Strict):
    status: FeasibilityStatus = FeasibilityStatus.unknown
    concerns: list[str] = Field(default_factory=list)


class EvidenceItem(_Strict):
    source: str = ""
    title: str = ""
    url: str = ""
    publication_date: str = ""
    access_date: str = ""
    information_used: str = ""
    source_type: SourceType = SourceType.model_inference
    confidence: float = 0.0
    verification_status: VerificationStatus = VerificationStatus.not_verified

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Confidence(_Strict):
    overall: float = 0.0

    @field_validator("overall")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Validation(_Strict):
    verified: bool = False
    verifier_status: str = "pending"


class SubjectOutput(_Strict):
    agent: str = "subject_agent"
    version: str = "1.0"
    status: SubjectStatus
    subject: SubjectCore = Field(default_factory=SubjectCore)
    research_context: ResearchContext = Field(default_factory=ResearchContext)
    key_concepts: list[str] = Field(default_factory=list)
    initial_justification: str = ""
    feasibility: Feasibility = Field(default_factory=Feasibility)
    missing_information: list[str] = Field(default_factory=list)
    questions_for_student: list[str] = Field(default_factory=list)
    identified_ambiguities: list[str] = Field(default_factory=list)
    identified_limits: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    validation: Validation = Field(default_factory=Validation)
