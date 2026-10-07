"""Contrat de sortie de l'Agent Problème de recherche (SPEC §16 : preuves A–H)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProblemStatus(str, Enum):
    needs_clarification = "needs_clarification"
    ready_for_verification = "ready_for_verification"
    blocked = "blocked"


class SourceType(str, Enum):
    """Ordre de priorité des sources (SPEC §7)."""

    institutional = "institutional"
    scientific = "scientific"
    university = "university"
    international_org = "international_org"
    governmental = "governmental"
    professional = "professional"
    secondary = "secondary"
    student_document = "student_document"


class VerificationStatus(str, Enum):
    verified = "verified"
    not_verified = "not_verified"


class Provenance(str, Enum):
    provided = "provided"      # fourni par l'étudiant
    external = "external"      # provient d'une source réellement récupérée (source_id)
    inferred = "inferred"      # déduit/interprété par l'agent
    unknown = "unknown"        # inconnu


class Nature(str, Enum):
    fact = "fact"
    interpretation = "interpretation"
    unknown = "unknown"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubjectReference(_Strict):
    original: str = ""
    reformulated: str = ""


class IdentifiedProblem(_Strict):
    statement: str = ""
    situation: str = ""
    why_problematic: str = ""
    actors_concerned: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)
    stakes: list[str] = Field(default_factory=list)


class JustifyingElement(_Strict):
    element: str = ""
    source_id: str = ""
    provenance: Provenance = Provenance.unknown
    nature: Nature = Nature.unknown


class SourceEvidence(_Strict):
    source_id: str
    source: str = ""
    title: str = ""
    url: str = ""
    doi: str = ""
    publication_date: str = ""
    access_date: str = ""
    information_used: str = ""
    source_type: SourceType = SourceType.secondary
    confidence: float = 0.0
    verification_status: VerificationStatus = VerificationStatus.not_verified

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Delimitation(_Strict):
    population: str = ""
    geographical_scope: str = ""
    temporal_scope: str = ""
    context: str = ""


class Confidence(_Strict):
    overall: float = 0.0
    rationale: str = ""

    @field_validator("overall")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Validation(_Strict):
    verified: bool = False
    verifier_status: str = "pending"


class ProblemOutput(_Strict):
    agent: str = "research_problem_agent"
    version: str = "1.0"
    status: ProblemStatus
    subject_reference: SubjectReference = Field(default_factory=SubjectReference)
    identified_problem: IdentifiedProblem = Field(default_factory=IdentifiedProblem)   # A
    justifying_elements: list[JustifyingElement] = Field(default_factory=list)         # B
    sources: list[SourceEvidence] = Field(default_factory=list)                        # C
    unknown_information: list[str] = Field(default_factory=list)                       # D
    gaps: list[str] = Field(default_factory=list)                                      # E
    remaining_questions: list[str] = Field(default_factory=list)                       # F
    provisional_formulation: str = ""                                                  # G
    delimitation: Delimitation = Field(default_factory=Delimitation)
    search_queries_used: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)                         # H
    validation: Validation = Field(default_factory=Validation)
