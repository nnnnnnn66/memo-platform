"""Contrat de sortie du vérificateur indépendant (SPEC §13)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class VerifierVerdict(str, Enum):
    verified = "verified"
    corrections_requested = "corrections_requested"
    rejected = "rejected"


class ControlResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    resultat: str  # "ok" | "echec"
    detail: str = ""


class VerifierOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent: str = "results_verifier"
    version: str = "1.0"
    verdict: VerifierVerdict
    controls: list[ControlResult] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
