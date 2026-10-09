"""Modèles partagés entre les contrats de l'Agent Objectifs de recherche."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Confidence(StrictModel):
    overall: float = 0.0
    rationale: str = ""

    @field_validator("overall")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class Validation(StrictModel):
    """Résultat de la vérification indépendante. Posé par le vérificateur, jamais par l'agent."""

    verified: bool = False
    verifier_status: str = "pending"


class UpstreamValidation(BaseModel):
    model_config = ConfigDict(extra="allow")
    verified: bool = False
    verifier_status: str = "pending"
