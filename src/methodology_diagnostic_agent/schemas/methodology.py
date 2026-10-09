"""Contrats du diagnostic méthodologique : six catégories distinctes (SPEC §4, §7, §16)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class CategoryCode(StrictModel):
    """Un choix méthodologique d'une catégorie : proposition + justification + alternatives + limites."""

    code: str = ""                       # clé canonique de l'énumération de la catégorie
    proposition: str = ""                # formulation lisible
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    limites: list[str] = Field(default_factory=list)


class MethodologyDiagnosis(StrictModel):
    """Les six catégories, DISTINCTES les unes des autres (SPEC §7, §10.4)."""

    approche: CategoryCode = Field(default_factory=CategoryCode)
    logique: CategoryCode = Field(default_factory=CategoryCode)
    type_recherche: CategoryCode = Field(default_factory=CategoryCode)
    strategie: CategoryCode = Field(default_factory=CategoryCode)
    collecte: list[CategoryCode] = Field(default_factory=list)
    analyse: list[CategoryCode] = Field(default_factory=list)
    articulation: str = ""               # comment les choix s'articulent entre eux
    coherence_question: str = ""         # en quoi ils répondent à la question de recherche


class Ambiguity(StrictModel):
    description: str = ""
    impact: str = ""
    clarification_question: str = ""


class SourceEvidence(StrictModel):
    query: str = ""
    provider: str = ""
    source_id: str = ""
    title: str = ""
    url: str = ""
    used: bool = False


class DiagnosticStatusEnum(str, Enum):
    """Statut du diagnostic (SPEC §16) — distinct du statut de pipeline."""

    provisoire = "provisoire"
    en_attente_de_validation = "en_attente_de_validation"
    valide = "valide"
    a_reviser = "a_reviser"
