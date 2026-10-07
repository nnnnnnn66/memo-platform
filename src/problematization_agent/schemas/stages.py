"""Contrats des sorties LLM de chaque phase (ce que le modèle doit produire)."""

from pydantic import Field

from .alignment import MethodologicalAlignment
from .common import StrictModel
from .confrontation import LiteratureConfrontation
from .gap import Gap
from .output import Justification, ProblematiqueNote
from .problem import ProblemMapping
from .question import ObjectivesCandidate, ResearchQuestionCandidate


class ProblemMappingOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    problem_mapping: ProblemMapping = Field(default_factory=ProblemMapping)


class ConfrontationOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    literature_confrontation: LiteratureConfrontation = Field(
        default_factory=LiteratureConfrontation)


class GapOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    gap: Gap = Field(default_factory=Gap)


class JustificationOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    justification: Justification = Field(default_factory=Justification)
    problematique_note: ProblematiqueNote = Field(default_factory=ProblematiqueNote)


class QuestionObjectivesOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    research_question: ResearchQuestionCandidate = Field(default_factory=ResearchQuestionCandidate)
    objectives: ObjectivesCandidate = Field(default_factory=ObjectivesCandidate)


class AlignmentOutput(StrictModel):
    agent: str = "problematization_agent"
    version: str = "1.0"
    methodological_alignment: MethodologicalAlignment = Field(
        default_factory=MethodologicalAlignment)
