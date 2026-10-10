"""Contrats des sorties LLM de chaque phase (ce que le modèle doit produire)."""

from pydantic import Field, field_validator

from .analysis import HypothesisAnalysis
from .common import StrictModel
from .hypotheses import (
    DecisionCode,
    Hypothesis,
    HypothesisObjectiveAlignment,
)


def _flatten_strings(items) -> list[str]:
    """Ramène une liste d'éléments hétérogènes à une liste de CHAÎNES.

    Le modèle renvoie régulièrement des OBJETS là où le contrat attend des chaînes
    (« theoretical_or_literature_support » : `{"source": "D54", "appui": "…"}`) : la campagne
    entière échouait sur 17 erreurs de validation, deux tentatives de suite (constaté en exécution
    réelle). On aplatit l'objet en texte au lieu de refuser — l'information est conservée, jamais
    inventée. Même famille de correctif que les agents 3 et 4 (« normalisation défensive »).
    """
    out: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            parts: list[str] = []
            for key, value in item.items():
                if isinstance(value, (list, tuple)):
                    value = ", ".join(str(v) for v in value)
                text = str(value).strip()
                if text:
                    parts.append(f"{key} : {text}" if len(item) > 1 else text)
            out.append(" — ".join(parts))
        else:
            out.append(str(item))
    return [text for text in out if text.strip()]


class AnalysisOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    analysis: HypothesisAnalysis = Field(default_factory=HypothesisAnalysis)


class DecisionOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    hypotheses_decision: DecisionCode = DecisionCode.require_clarification
    decision_rationale: str = ""
    clarification_questions: list[str] = Field(default_factory=list)


class FormulationOutput(StrictModel):
    agent: str = "research_hypotheses_agent"
    version: str = "1.0"
    research_hypotheses: list[Hypothesis] = Field(default_factory=list)
    hypothesis_objective_alignment: HypothesisObjectiveAlignment = Field(
        default_factory=HypothesisObjectiveAlignment)
    theoretical_or_literature_support: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)

    @field_validator("theoretical_or_literature_support", "required_evidence", mode="before")
    @classmethod
    def _accept_objects(cls, value):
        return _flatten_strings(value)
