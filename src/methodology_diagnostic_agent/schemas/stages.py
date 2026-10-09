"""Contrats des sorties LLM de chaque phase (ce que le modèle doit produire)."""

from pydantic import Field

from .analysis import DossierAnalysis
from .common import StrictModel
from .methodology import MethodologyDiagnosis


class AnalysisOutput(StrictModel):
    agent: str = "methodology_diagnostic_agent"
    version: str = "1.0"
    analysis: DossierAnalysis = Field(default_factory=DossierAnalysis)


class DiagnosisOutput(StrictModel):
    agent: str = "methodology_diagnostic_agent"
    version: str = "1.0"
    resume: str = ""
    diagnosis: MethodologyDiagnosis = Field(default_factory=MethodologyDiagnosis)
    hypotheses_examined: list[str] = Field(default_factory=list)
    feasibility_controls: list[str] = Field(default_factory=list)
    # Faits restés INCONNUS après lecture du dossier (effectif, instruments, autorisations…).
    # Distincts de `limits_of_this_output` (portée du diagnostic) et de `questions_for_human`
    # (décisions à valider) : un champ vide alors que des inconnues existent a été relevé par
    # le vérificateur en campagne réelle (agent 8).
    unknowns: list[str] = Field(default_factory=list)
    limits_of_this_output: list[str] = Field(default_factory=list)
    questions_for_human: list[str] = Field(default_factory=list)
