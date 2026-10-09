"""Analyse du dossier de recherche (SPEC §9.1-9.2)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class Provenance(str, Enum):
    provided = "provided"
    inferred = "inferred"
    unknown = "unknown"


class DossierAnalysis(StrictModel):
    """Ce que l'agent dégage AVANT de proposer des choix méthodologiques."""

    phenomene: str = ""
    visee: str = ""                     # ce que l'étudiant cherche réellement à faire
    nature_du_travail: str = ""         # exploratoire / descriptif / explicatif / comparatif…
    elements_disponibles: list[str] = Field(default_factory=list)
    elements_manquants: list[str] = Field(default_factory=list)     # BLOQUANTS uniquement
    contradictions: list[str] = Field(default_factory=list)
    provenance: Provenance = Provenance.unknown
