"""Contrat de la phase 1 (analyse + intentions de recherche) — SPEC §9.1, §9.3."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class IntentKind(str, Enum):
    """Famille de sources visée : oriente la sélection déterministe des fournisseurs."""

    publications = "publications"
    statistics = "statistics"
    repository = "repository"
    any = "any"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreliminaryAnalysis(_Strict):
    phenomenon: str = ""
    population: str = ""
    context: str = ""
    geographical_scope: str = ""
    temporal_scope: str = ""
    main_concepts: list[str] = Field(default_factory=list)


class SearchIntent(_Strict):
    query: str
    purpose: str = ""
    kind: IntentKind = IntentKind.any
    language: str = ""


class Phase1Output(_Strict):
    agent: str = "research_problem_agent"
    version: str = "1.0"
    preliminary_analysis: PreliminaryAnalysis = Field(default_factory=PreliminaryAnalysis)
    needs_search: bool = True
    search_intents: list[SearchIntent] = Field(default_factory=list)
