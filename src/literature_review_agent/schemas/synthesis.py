"""Contrat de la phase 3 : comparaison des travaux et synthèse critique."""

from pydantic import Field

from .common import StrictModel
from .output import Comparison, Synthesis


class SynthesisOutput(StrictModel):
    agent: str = "literature_review_agent"
    version: str = "1.0"
    comparison: Comparison = Field(default_factory=Comparison)
    synthesis: Synthesis = Field(default_factory=Synthesis)
    unknowns: list[str] = Field(default_factory=list)
    limits_of_this_review: list[str] = Field(default_factory=list)
