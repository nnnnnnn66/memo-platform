"""Contrats des sorties LLM de chaque phase (ce que le modèle doit produire)."""

from pydantic import Field

from .common import StrictModel
from .analysis import QuestionAnalysis
from .objectives import FeasibilityAssessment, QuestionObjectiveAlignment


class AnalysisOutput(StrictModel):
    agent: str = "research_objectives_agent"
    version: str = "1.0"
    question_analysis: QuestionAnalysis = Field(default_factory=QuestionAnalysis)


class GeneralOutput(StrictModel):
    agent: str = "research_objectives_agent"
    version: str = "1.0"
    general_objective: str = ""


class SpecificOutput(StrictModel):
    agent: str = "research_objectives_agent"
    version: str = "1.0"
    specific_objectives: list[str] = Field(default_factory=list)
    objective_rationale: str = ""
    question_objective_alignment: QuestionObjectiveAlignment = Field(
        default_factory=QuestionObjectiveAlignment)
    feasibility_assessment: FeasibilityAssessment = Field(default_factory=FeasibilityAssessment)
