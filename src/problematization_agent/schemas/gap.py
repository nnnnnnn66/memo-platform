"""Contrat de la phase 3 : identification et classification du gap — SPEC §9.3.

Enum à QUATRE valeurs (décision D2 validée) : la SPEC §9.3 n'en liste que trois, mais §3.5
mentionne explicitement la lacune *méthodologique*.
"""

from enum import Enum

from pydantic import Field

from .common import StrictModel
from .statement import AnchoredStatement


class GapType(str, Enum):
    contextuelle = "contextuelle"
    conceptuelle = "conceptuelle"
    empirique = "empirique"
    methodologique = "methodologique"


class GapCheckResult(str, Enum):
    already_addressed = "already_addressed"
    not_found = "not_found"
    unavailable = "unavailable"


class GapCheckPublication(StrictModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str = ""
    url: str = ""
    provider: str = ""


class GapCheck(StrictModel):
    result: GapCheckResult = GapCheckResult.unavailable
    queries: list[str] = Field(default_factory=list)
    publications: list[GapCheckPublication] = Field(default_factory=list)
    providers_used: list[str] = Field(default_factory=list)
    providers_failed: list[dict] = Field(default_factory=list)
    note: str = ""


class Gap(StrictModel):
    type: GapType = GapType.contextuelle
    description: str = ""
    justification: str = ""
    statements: list[AnchoredStatement] = Field(default_factory=list)
    gap_check: GapCheck = Field(default_factory=GapCheck)
