"""Contrat de sortie — dossier de preuve (SPEC §16).

Aucun champ ne permet d'ÉCRIRE dans une étape du dossier : l'agent signale, il ne corrige jamais.
"""

from enum import Enum

from pydantic import Field

from .audit import Audit, ElementNonVerifiable, Finding
from .common import Confidence, StrictModel, StrList, Validation
from .decision import StudentValidation
from .report import CoherenceReport, Verdict


class AuditStatus(str, Enum):
    needs_clarification = "needs_clarification"
    blocked = "blocked"
    ready_for_verification = "ready_for_verification"
    verification_failed = "verification_failed"
    awaiting_human_validation = "awaiting_human_validation"
    validated = "validated"


class DocumentStatus(str, Enum):
    brouillon = "brouillon"
    a_corriger = "a_corriger"
    controle = "controle"
    en_attente_de_validation = "en_attente_de_validation"
    valide = "valide"
    a_reviser = "a_reviser"


class Evidence(StrictModel):
    llm_calls: int = 0
    network_requests: int = 0
    reformulations: int = 0
    constats: int = 0
    constats_deterministes: int = 0
    constats_semantiques: int = 0


class CoherenceOutput(StrictModel):
    agent: str = "research_coherence_verifier"
    version: str = "1.0"
    status: AuditStatus

    # --- dossier de preuve (SPEC §16) ---
    research_id: str = ""
    generated_at: str = ""
    version_elements_consultes: StrList = Field(default_factory=list)
    etapes_presentes: StrList = Field(default_factory=list)
    etapes_non_verifiees: StrList = Field(default_factory=list)
    etapes_absentes: StrList = Field(default_factory=list)
    elements_de_service: StrList = Field(default_factory=list)
    constats_retires_ou_reclasses: StrList = Field(default_factory=list)
    corrections_effectuees: StrList = Field(default_factory=list)
    historique_versions: StrList = Field(default_factory=list)
    document_status: DocumentStatus = DocumentStatus.brouillon
    document_version: str = "1.0"

    # --- le produit de l'étape 13 ---
    audit: Audit = Field(default_factory=Audit)
    report: CoherenceReport = Field(default_factory=CoherenceReport)

    # --- honnêteté et contrôle ---
    non_verifiable: list[ElementNonVerifiable] = Field(default_factory=list)
    limites_de_cet_audit: StrList = Field(default_factory=list)
    questions_for_human: StrList = Field(default_factory=list)
    unknowns: StrList = Field(default_factory=list)
    coherence_controls: StrList = Field(default_factory=list)
    verification_result: Validation = Field(default_factory=Validation)
    student_validation: StudentValidation = Field(default_factory=StudentValidation)
    confidence: Confidence = Field(default_factory=Confidence)
    evidence: Evidence = Field(default_factory=Evidence)

    @property
    def constats(self) -> list[Finding]:
        return self.audit.constats

    @property
    def verdict(self) -> Verdict:
        return self.report.verdict
