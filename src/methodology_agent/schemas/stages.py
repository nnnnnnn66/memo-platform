"""Contrats des sorties LLM de chaque étage (ce que le modèle doit produire)."""

from pydantic import Field

from .analysis import Analysis
from .common import StrList, StrictModel
from .draft import MethodologyDraft
from .matrix import CoherenceMatrix
from .protocol import Instrument, Protocol


class AnalysisOutput(StrictModel):
    agent: str = "methodology_agent"
    version: str = "1.0"
    analysis: Analysis = Field(default_factory=Analysis)


class ProtocolOutput(StrictModel):
    agent: str = "methodology_agent"
    version: str = "1.0"
    protocol: Protocol = Field(default_factory=Protocol)
    elements_a_confirmer: StrList = Field(default_factory=list)


class InstrumentsOutput(StrictModel):
    agent: str = "methodology_agent"
    version: str = "1.0"
    instruments: list[Instrument] = Field(default_factory=list)
    matrice: CoherenceMatrix = Field(default_factory=CoherenceMatrix)
    elements_a_confirmer: StrList = Field(default_factory=list)


class WritingOutput(StrictModel):
    agent: str = "methodology_agent"
    version: str = "1.0"
    draft: MethodologyDraft = Field(default_factory=MethodologyDraft)
