"""Sorties de chaque étage LLM."""

from pydantic import Field

from .audit import AuditItem, ElementNonVerifiable
from .common import StrictModel, StrList
from .report import CoherenceReport


class AuditOutput(StrictModel):
    """P1 — audit transversal sémantique (les FAITS sont fournis par le programme)."""

    agent: str = "research_coherence_verifier"
    version: str = "1.0"
    #: Constats supplémentaires, hors liste déterministe.
    constats: list[AuditItem] = Field(default_factory=list)
    #: Codes des faits déterministes infirmés (le motif est exigé dans `motifs`).
    faits_infirmes: StrList = Field(default_factory=list)
    motifs: StrList = Field(default_factory=list)
    #: Éléments de service examinés (traçabilité de l'audit).
    examens: StrList = Field(default_factory=list)


class ReportOutput(StrictModel):
    """P2 — rapport rédigé, portée DÉCLARÉE."""

    agent: str = "research_coherence_verifier"
    version: str = "1.0"
    report: CoherenceReport = Field(default_factory=CoherenceReport)
    #: Éléments non vérifiables que le modèle ajoute à la portée statique.
    non_verifiable_supplementaire: list[ElementNonVerifiable] = Field(default_factory=list)
