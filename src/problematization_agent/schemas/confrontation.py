"""Contrat de la phase 2 : confrontation littéraire (l'état des savoirs) — SPEC §9.2."""

from pydantic import Field

from .common import StrictModel
from .statement import AnchoredStatement


class LiteratureConfrontation(StrictModel):
    modeles_dominants: list[AnchoredStatement] = Field(default_factory=list)
    consensus: list[AnchoredStatement] = Field(default_factory=list)
    divergences: list[AnchoredStatement] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    statements: list[AnchoredStatement] = Field(default_factory=list)
