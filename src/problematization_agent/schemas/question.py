"""Contrat de la phase 5 : question de recherche candidate et objectifs candidats — SPEC §9.6-9.7.

PROPOSITION DE TRANSITION : ces champs sont distincts de la problématique et marqués `proposed`.
Ils ne constituent JAMAIS la version validée des étapes 5 (question) et 6 (objectifs).
"""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class QuestionStatus(str, Enum):
    proposed = "proposed"


class ResearchQuestionCandidate(StrictModel):
    question: str = ""
    type: str = ""          # ouverte | fermée | mixte …
    scope: str = ""
    status: QuestionStatus = QuestionStatus.proposed


class ObjectivesCandidate(StrictModel):
    general: str = ""
    specifics: list[str] = Field(default_factory=list)
    status: QuestionStatus = QuestionStatus.proposed
