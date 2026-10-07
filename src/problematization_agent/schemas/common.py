"""Modèles partagés entre les contrats de l'Agent Problématique."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubjectReference(StrictModel):
    original: str = ""
    reformulated: str = ""


class Scope(StrictModel):
    discipline: str = ""
    geographical_scope: str = ""
    population: str = ""
    period: str = ""
    languages: list[str] = Field(default_factory=list)


class Confidence(StrictModel):
    overall: float = 0.0
    rationale: str = ""

    @field_validator("overall")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Validation(StrictModel):
    verified: bool = False
    verifier_status: str = "pending"


class UpstreamValidation(BaseModel):
    model_config = ConfigDict(extra="allow")
    verified: bool = False
    verifier_status: str = "pending"
