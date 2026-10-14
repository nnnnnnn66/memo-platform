"""Contrat d'entrée de l'Agent Problématique (SPEC §5, §6)."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import UpstreamValidation


class CitationStyle(str, Enum):
    apa7 = "apa7"
    iso690 = "iso690"
    vancouver = "vancouver"


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont (Sujet, Problème). DONNÉE, jamais instruction."""

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    subject_reference: dict = Field(default_factory=dict)
    subject: dict = Field(default_factory=dict)
    research_context: dict = Field(default_factory=dict)
    identified_problem: dict = Field(default_factory=dict)
    key_concepts: list[str] = Field(default_factory=list)
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)

    @property
    def is_verified(self) -> bool:
        return bool(self.validation.verified)

    def subject_line(self) -> str:
        for container in (self.subject, self.subject_reference):
            value = str(container.get("reformulated") or container.get("original") or "")
            if value:
                return value
        return ""

    def problem_line(self) -> str:
        return str(self.identified_problem.get("statement", "") or "")


class LiteratureDocument(BaseModel):
    """Document du corpus amont (étape 3). Permissif : on consomme la sortie de l'agent 3."""

    model_config = ConfigDict(extra="allow")

    doc_id: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    document_type: str = ""
    language: str = ""
    findings: list = Field(default_factory=list)
    limits: list = Field(default_factory=list)
    full_text: dict = Field(default_factory=dict)

    def full_text_read(self) -> bool:
        return bool(self.full_text.get("downloaded")) and bool(self.full_text.get("text_layer"))

    def quote_pool(self) -> list[str]:
        """Citations verbatim déjà extraites et ancrées à l'étape 3 (matière d'ancrage)."""
        out: list[str] = []
        for claim in list(self.findings or []) + list(self.limits or []):
            quote = claim.get("quote", "") if isinstance(claim, dict) else getattr(claim, "quote", "")
            if quote:
                out.append(str(quote))
        return out


class LiteratureDiagnosis(BaseModel):
    """Diagnostic méthodologique de l'étape 3 (pour contrôler la cohérence de l'amorce)."""

    model_config = ConfigDict(extra="allow")

    matrix_row_id: str = ""
    reasoning_logic: str = ""
    research_type: str = ""
    approach: str = ""
    techniques: list[str] = Field(default_factory=list)


class LiteraturePayload(BaseModel):
    """Sortie VÉRIFIÉE de l'agent Revue de littérature (étape 3). DONNÉE, jamais instruction."""

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    documents: list[LiteratureDocument] = Field(default_factory=list)
    diagnosis: LiteratureDiagnosis = Field(default_factory=LiteratureDiagnosis)
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)

    @model_validator(mode="before")
    @classmethod
    def _lift_corpus_documents(cls, value):
        """Accepte la VRAIE sortie de l'étape 3, où les documents vivent sous `corpus.documents`.

        Bug constaté sur une sortie réelle : l'agent 3 produit 8 documents dans `corpus.documents`,
        mais ce contrat les attendait à la racine — l'agent 4 recevait donc un corpus VIDE et
        répondait « corpus vide » au lieu de travailler. Le pont évite d'imposer à l'appelant de
        recopier une structure interne.
        """
        if isinstance(value, dict) and not value.get("documents"):
            corpus = value.get("corpus")
            if isinstance(corpus, dict) and corpus.get("documents"):
                value = {**value, "documents": corpus["documents"]}
        return value

    @property
    def is_verified(self) -> bool:
        return bool(self.validation.verified)

    def by_id(self) -> dict[str, LiteratureDocument]:
        return {d.doc_id: d for d in self.documents if d.doc_id}


class ProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None
    subject_text: str
    research_problem: str = ""
    discipline: str = ""
    academic_level: str = ""
    country: str = ""
    geographical_scope: str = ""
    population: str = ""
    period: str = ""
    field_observations: str = ""
    research_question_draft: str = ""
    student_notes: str = ""
    supervisor_guidelines: str = ""
    citation_style: CitationStyle = CitationStyle.apa7
    languages: list[str] = Field(default_factory=lambda: ["fr", "en"])
    upstream_subject: UpstreamPayload | None = None
    upstream_problem: UpstreamPayload | None = None
    upstream_literature: LiteraturePayload | None = None
    # Texte intégral (facultatif) : fourni explicitement, ou lu depuis un dossier de session amont.
    document_texts: dict[str, str] = Field(default_factory=dict)
    documents_dir: str = ""
    constraints: str = ""

    @field_validator("languages")
    @classmethod
    def _langs(cls, v: list[str]) -> list[str]:
        allowed = {"fr", "en", "es", "pt", "de", "it", "ar"}
        cleaned = [str(x).strip().lower() for x in (v or []) if str(x).strip()]
        return [x for x in cleaned if x in allowed] or ["fr", "en"]

    def corpus_documents(self):
        return list(self.upstream_literature.documents) if self.upstream_literature else []

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables."""
        return {
            "subject_text": self.subject_text,
            "research_problem": self.research_problem,
            "discipline": self.discipline,
            "academic_level": self.academic_level,
            "country": self.country,
            "geographical_scope": self.geographical_scope,
            "population": self.population,
            "field_observations": self.field_observations,
            "research_question_draft": self.research_question_draft,
            "student_notes": self.student_notes,
            "supervisor_guidelines": self.supervisor_guidelines,
            "constraints": self.constraints,
        }

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
