"""Contrats des sorties LLM de chaque étage (ce que le modèle doit produire)."""

from pydantic import Field

from .analysis import AnalysisPlan
from .common import StrictModel
from .draft import ResultsDraft
from .interpretation import Interpretation
from .inventory import Inventory


class InventoryOutput(StrictModel):
    agent: str = "research_results_analysis_agent"
    version: str = "1.0"
    inventory: Inventory = Field(default_factory=Inventory)


class AnalysisOutput(StrictModel):
    agent: str = "research_results_analysis_agent"
    version: str = "1.0"
    plan: AnalysisPlan = Field(default_factory=AnalysisPlan)


class InterpretationOutput(StrictModel):
    agent: str = "research_results_analysis_agent"
    version: str = "1.0"
    interpretation: Interpretation = Field(default_factory=Interpretation)


class WritingOutput(StrictModel):
    agent: str = "research_results_analysis_agent"
    version: str = "1.0"
    draft: ResultsDraft = Field(default_factory=ResultsDraft)
