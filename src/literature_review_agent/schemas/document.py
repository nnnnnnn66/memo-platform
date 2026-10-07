"""Contrat d'un document du corpus : métadonnées vérifiées, texte intégral, extraits ancrés."""

from enum import Enum

from pydantic import Field, field_validator

from .common import StrictModel


class SourceType(str, Enum):
    """Priorité documentaire de la SPEC §7."""

    scientific = "scientific"
    peer_reviewed = "peer_reviewed"
    thesis = "thesis"
    book = "book"
    preprint = "preprint"
    research_org = "research_org"
    university = "university"
    governmental = "governmental"
    international_org = "international_org"
    institutional = "institutional"


class DocumentType(str, Enum):
    article = "article"
    thesis = "thesis"
    book = "book"
    report = "report"
    dataset = "dataset"
    preprint = "preprint"
    other = "other"


class GeographicScope(str, Enum):
    ivory_coast = "ivory_coast"
    west_africa = "west_africa"
    africa = "africa"
    international = "international"
    unclear = "unclear"


class VerificationStatus(str, Enum):
    verified = "verified"
    not_verified = "not_verified"


class ExtractionScope(str, Enum):
    """D'où vient l'information extraite — le modèle ne doit jamais prétendre avoir lu plus."""

    full_text = "full_text"          # texte intégral téléchargé et lu
    abstract_only = "abstract_only"  # seul le résumé était disponible
    metadata_only = "metadata_only"  # ni texte intégral ni résumé


class FullTextInfo(StrictModel):
    available: bool = False          # accès libre annoncé (Unpaywall / fournisseur)
    downloaded: bool = False
    file_name: str = ""              # nom du fichier dans documents/
    file_path: str = ""              # chemin relatif dans l'espace de session
    sha256: str = ""
    bytes: int = 0
    pages: int = 0
    text_chars: int = 0
    text_layer: bool = True          # False = document scanné sans couche texte
    source_url: str = ""             # URL réellement téléchargée
    license: str = ""
    extraction_tool: str = ""
    download_error: str = ""


class Excerpt(StrictModel):
    """Passage réel extrait d'un document, transmis au modèle (donnée non fiable)."""

    section: str = ""                # abstract | introduction | method | results | discussion | conclusion | limits
    page: int = 0
    text: str = ""


class AnchoredClaim(StrictModel):
    """Affirmation extraite d'un document, ancrée par une citation verbatim du texte réel."""

    claim: str = ""
    quote: str = ""
    locator_section: str = ""
    locator_page: int = 0

    @field_validator("quote")
    @classmethod
    def _trim(cls, v: str) -> str:
        return (v or "").strip()[:400]


class DocumentRecord(StrictModel):
    doc_id: str
    provider: str = ""
    source_type: SourceType = SourceType.scientific
    document_type: DocumentType = DocumentType.article
    authors: list[str] = Field(default_factory=list)
    title: str = ""
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    language: str = ""
    abstract: str = ""
    geographic_scope: GeographicScope = GeographicScope.unclear
    geographic_evidence: str = ""     # ce qui a fait conclure à cette portée (titre, affiliation…)
    relevance: float = 0.0
    theme: str = ""
    extraction_scope: ExtractionScope = ExtractionScope.metadata_only
    method: str = ""
    field_site: str = ""              # terrain / population étudiés
    findings: list[AnchoredClaim] = Field(default_factory=list)
    limits: list[AnchoredClaim] = Field(default_factory=list)
    full_text: FullTextInfo = Field(default_factory=FullTextInfo)
    reference: str = ""               # rendu déterministe par bibliography/styles.py
    retrieved: bool = True
    verification_status: VerificationStatus = VerificationStatus.verified

    @field_validator("relevance")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("year", mode="before")
    @classmethod
    def _year(cls, v):
        if v in (None, "", 0):
            return None
        try:
            return int(str(v)[:4])
        except (TypeError, ValueError):
            return None
