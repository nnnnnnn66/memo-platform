"""Contrat de la phase 1 : concepts, mots-clés, stratégie de recherche (SPEC §9.1–9.3)."""

from enum import Enum

from pydantic import Field

from .common import Confidence, StrictModel, SubjectReference


class QueryKind(str, Enum):
    """Famille de sources visée : oriente la sélection déterministe des fournisseurs."""

    publications = "publications"
    theses = "theses"
    repositories = "repositories"
    statistics = "statistics"
    any = "any"


class QueryScope(str, Enum):
    """Niveau de la cascade géographique visé par la requête."""

    ivory_coast = "ivory_coast"
    west_africa = "west_africa"
    africa = "africa"
    international = "international"


class ConceptBlock(StrictModel):
    concept: str
    keywords_fr: list[str] = Field(default_factory=list)
    keywords_en: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)


class SearchQuery(StrictModel):
    query: str
    concepts: list[str] = Field(default_factory=list)
    kind: QueryKind = QueryKind.any
    scope: QueryScope = QueryScope.international
    language: str = ""
    rationale: str = ""


class SearchStrategy(StrictModel):
    combinations: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    period: str = ""
    languages: list[str] = Field(default_factory=list)
    selection_criteria: list[str] = Field(default_factory=list)
    cascade_justification: str = ""


class KeywordsOutput(StrictModel):
    agent: str = "literature_review_agent"
    version: str = "1.0"
    subject_reference: SubjectReference = Field(default_factory=SubjectReference)
    concepts: list[ConceptBlock] = Field(default_factory=list)
    strategy: SearchStrategy = Field(default_factory=SearchStrategy)
    queries: list[SearchQuery] = Field(default_factory=list)
    subject_is_too_broad: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
