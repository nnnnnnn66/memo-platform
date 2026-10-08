"""Compréhension de la problématique et intention de recherche (SPEC §7, §9.1-9.2)."""

from enum import Enum

from pydantic import Field

from .common import StrictModel


class Provenance(str, Enum):
    provided = "provided"   # dit par l'étudiant / présent dans les entrées
    inferred = "inferred"   # interprétation de l'agent, à confirmer
    unknown = "unknown"     # non établi : jamais inventé


class Comprehension(StrictModel):
    phenomene: str = ""
    objet_central: str = ""
    population: str = ""
    zone: str = ""
    periode: str = ""
    reste_a_examiner: str = ""
    provenance: Provenance = Provenance.unknown


class ResearchIntention(StrictModel):
    """Intention de recherche : DÉCRIRE, COMPRENDRE, EXPLIQUER… — jamais une méthode."""

    intention: str = ""
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)
