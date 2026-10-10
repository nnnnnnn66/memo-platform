"""Contrat de sortie de l'Agent Méthodologie — dossier de preuve (SPEC §16).

Ce contrat n'offre AUCUN champ permettant de présenter un résultat de recherche : ce n'est pas la
mission de l'étape 9. La recherche est PRÉVUE, jamais « déjà réalisée » sans preuve fournie.
"""

from enum import Enum

from pydantic import Field

from .analysis import Analysis
from .common import Confidence, StrList, StrictModel, Validation
from .decision import StudentValidation
from .draft import MethodologyDraft
from .matrix import CoherenceMatrix
from .protocol import Protocol


class MethodologyStatus(str, Enum):
    needs_clarification = "needs_clarification"
    blocked = "blocked"
    ready_for_verification = "ready_for_verification"
    verification_failed = "verification_failed"
    awaiting_human_validation = "awaiting_human_validation"
    validated = "validated"


class DocumentStatus(str, Enum):
    """Statut RÉEL du document de méthodologie (SPEC §9 étape 5)."""

    brouillon = "brouillon"
    a_verifier = "a_verifier"
    en_attente_de_validation = "en_attente_de_validation"
    valide = "valide"
    a_reviser = "a_reviser"


class Evidence(StrictModel):
    llm_calls: int = 0
    network_requests: int = 0
    reformulations: int = 0


class MethodologyOutput(StrictModel):
    agent: str = "methodology_agent"
    version: str = "1.0"
    status: MethodologyStatus

    # --- dossier de preuve (SPEC §16) ---
    research_id: str = ""
    generated_at: str = ""
    version_diagnostic_utilisee: str = ""
    trace_validation_diagnostic: str = ""
    elements_de_recherche_examines: StrList = Field(default_factory=list)
    choix_methodologiques_retenus: StrList = Field(default_factory=list)
    sources_methodologiques_consultees: StrList = Field(default_factory=list)
    limites_et_risques: StrList = Field(default_factory=list)
    historique_modifications: StrList = Field(default_factory=list)
    document_status: DocumentStatus = DocumentStatus.brouillon
    document_version: str = "1.0"

    # --- rappel du dossier ---
    subject: str = ""
    main_research_question: str = ""
    secondary_research_questions: StrList = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: StrList = Field(default_factory=list)
    hypotheses_examined: StrList = Field(default_factory=list)

    # --- le produit de l'étape 9 ---
    analysis: Analysis = Field(default_factory=Analysis)
    protocol: Protocol = Field(default_factory=Protocol)
    matrice: CoherenceMatrix = Field(default_factory=CoherenceMatrix)
    draft: MethodologyDraft = Field(default_factory=MethodologyDraft)

    # --- honnêteté, limites, contrôle ---
    informations_a_confirmer: StrList = Field(default_factory=list)
    missing_information: StrList = Field(default_factory=list)
    contradictions: StrList = Field(default_factory=list)
    unknowns: StrList = Field(default_factory=list)
    questions_for_human: StrList = Field(default_factory=list)
    limits_of_this_output: StrList = Field(default_factory=list)
    coherence_controls: StrList = Field(default_factory=list)
    verification_result: Validation = Field(default_factory=Validation)
    student_validation: StudentValidation = Field(default_factory=StudentValidation)
    confidence: Confidence = Field(default_factory=Confidence)
    evidence: Evidence = Field(default_factory=Evidence)
