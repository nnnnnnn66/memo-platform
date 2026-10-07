"""Contrat de la phase 1 : cartographie du problème réel (le constat) — SPEC §9.1."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class Provenance(str, Enum):
    provided = "provided"   # fourni par l'étudiant
    inferred = "inferred"   # déduit des entrées (jamais inventé)
    unknown = "unknown"     # non renseigné : à questionner


class ProblemMapping(StrictModel):
    phenomene: str = ""
    population: str = ""
    zone_geographique: str = ""
    dysfonctionnement: str = ""
    provenance: Provenance = Provenance.unknown
    assumptions: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
