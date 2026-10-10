"""Contrat de sortie — dossier de preuve (SPEC §16).

Aucun champ ne permet d'introduire un NOUVEAU résultat : la conclusion ne fait que synthétiser ceux
de l'étape 10, en les citant par leur identifiant.
"""

from enum import Enum

from pydantic import Field

from .common import Confidence, StrictModel, StrList, Validation
from .decision import StudentValidation
from .draft import ConclusionDraft
from .plan import ConclusionPlan
from .synthesis import Synthesis


class ConclusionStatus(str, Enum):
    needs_clarification = "needs_clarification"
    blocked = "blocked"
    ready_for_verification = "ready_for_verification"
    verification_failed = "verification_failed"
    awaiting_human_validation = "awaiting_human_validation"
    validated = "validated"


class DocumentStatus(str, Enum):
    """Statut RÉEL du document (SPEC §9 étape 5 et §12)."""

    brouillon = "brouillon"
    a_corriger = "a_corriger"
    verifie = "verifie"
    en_attente_de_validation = "en_attente_de_validation"
    valide = "valide"
    a_reviser = "a_reviser"


class Evidence(StrictModel):
    llm_calls: int = 0
    network_requests: int = 0
    reformulations: int = 0
    affirmations: int = 0


class ConclusionOutput(StrictModel):
    agent: str = "research_conclusion_agent"
    version: str = "1.0"
    status: ConclusionStatus

    # --- dossier de preuve (SPEC §16) ---
    research_id: str = ""
    generated_at: str = ""
    version_elements_consultes: StrList = Field(default_factory=list)
    question_utilisee: str = ""
    objectifs_utilises: StrList = Field(default_factory=list)
    references_resultats: StrList = Field(default_factory=list)   # identifiants R… utilisés
    lacunes_et_incertitudes: StrList = Field(default_factory=list)
    corrections_effectuees: StrList = Field(default_factory=list)
    historique_versions: StrList = Field(default_factory=list)
    document_status: DocumentStatus = DocumentStatus.brouillon
    document_version: str = "1.0"

    # --- rappel du dossier ---
    subject: str = ""
    main_research_question: str = ""
    general_objective: str = ""
    specific_objectives: StrList = Field(default_factory=list)
    hypotheses: StrList = Field(default_factory=list)

    # --- le produit de l'étape 11 ---
    synthesis: Synthesis = Field(default_factory=Synthesis)
    plan: ConclusionPlan = Field(default_factory=ConclusionPlan)
    draft: ConclusionDraft = Field(default_factory=ConclusionDraft)

    # --- honnêteté et contrôle ---
    informations_a_confirmer: StrList = Field(default_factory=list)
    missing_information: StrList = Field(default_factory=list)
    incoherences: StrList = Field(default_factory=list)
    unknowns: StrList = Field(default_factory=list)
    questions_for_human: StrList = Field(default_factory=list)
    limits_of_this_output: StrList = Field(default_factory=list)
    coherence_controls: StrList = Field(default_factory=list)
    verification_result: Validation = Field(default_factory=Validation)
    student_validation: StudentValidation = Field(default_factory=StudentValidation)
    confidence: Confidence = Field(default_factory=Confidence)
    evidence: Evidence = Field(default_factory=Evidence)
