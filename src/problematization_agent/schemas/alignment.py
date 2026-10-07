"""Contrat de l'amorce d'alignement méthodologique — SPEC §9.8.

La logique, le type de recherche et l'approche sont issus d'une matrice stockée en données
(`theory/matrix.py`). L'amorce est une PROPOSITION, cohérente avec le diagnostic de l'étape 3 ou
avec divergence déclarée.
"""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class ReasoningLogic(str, Enum):
    inductive = "inductive"
    deductive = "deductive"
    hypothetico_deductive = "hypothetico_deductive"
    abductive = "abductive"
    mixed = "mixed"


class UpstreamCoherence(str, Enum):
    consistent = "consistent"
    divergent = "divergent"
    absent = "absent"


class MethodologicalAlignment(StrictModel):
    logic: ReasoningLogic = ReasoningLogic.mixed
    research_type: str = ""
    approach: str = ""
    techniques: list[str] = Field(default_factory=list)
    justification: str = ""
    matrix_row_id: str = ""
    upstream_coherence: UpstreamCoherence = UpstreamCoherence.absent
    coherence_note: str = ""
    alternatives: list[str] = Field(default_factory=list)
    status: str = "proposal_to_validate_with_student"
