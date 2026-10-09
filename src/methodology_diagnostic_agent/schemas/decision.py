"""Décision de l'étudiant / de l'encadreur (portillon humain, SPEC §11, §12)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict

from .common import StrictModel


class DecisionValue(str, Enum):
    accepted = "accepted"
    modified = "modified"
    refused = "refused"


class StudentValidation(StrictModel):
    decision: DecisionValue | None = None
    comment: str = ""
    at: str | None = None


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionValue
    student_comment: str = ""
    # L'étudiant peut choisir des alternatives ou fournir les informations manquantes.
    provided_information: str = ""
    modified: dict = {}
