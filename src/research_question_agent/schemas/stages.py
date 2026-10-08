"""Contrats des sorties LLM de chaque phase (ce que le modèle doit produire)."""

from pydantic import Field

from .common import StrictModel
from .comprehension import Comprehension, ResearchIntention
from .question import FeasibilityAssessment, ScopeAndBoundaries


class ComprehensionOutput(StrictModel):
    agent: str = "research_question_agent"
    version: str = "1.0"
    comprehension: Comprehension = Field(default_factory=Comprehension)


class IntentionOutput(StrictModel):
    agent: str = "research_question_agent"
    version: str = "1.0"
    research_intention: ResearchIntention = Field(default_factory=ResearchIntention)


class FormulationOutput(StrictModel):
    agent: str = "research_question_agent"
    version: str = "1.0"
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    formulation_rationale: str = ""
    scope_and_boundaries: ScopeAndBoundaries = Field(default_factory=ScopeAndBoundaries)
    feasibility_assessment: FeasibilityAssessment = Field(default_factory=FeasibilityAssessment)
