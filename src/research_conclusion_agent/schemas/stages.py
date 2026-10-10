"""Contrats des sorties LLM de chaque étage (ce que le modèle doit produire)."""

from pydantic import Field

from .common import StrictModel
from .draft import ConclusionDraft
from .plan import ConclusionPlan
from .synthesis import Synthesis


class SynthesisOutput(StrictModel):
    agent: str = "research_conclusion_agent"
    version: str = "1.0"
    synthesis: Synthesis = Field(default_factory=Synthesis)


class PlanOutput(StrictModel):
    agent: str = "research_conclusion_agent"
    version: str = "1.0"
    plan: ConclusionPlan = Field(default_factory=ConclusionPlan)


class WritingOutput(StrictModel):
    agent: str = "research_conclusion_agent"
    version: str = "1.0"
    draft: ConclusionDraft = Field(default_factory=ConclusionDraft)
