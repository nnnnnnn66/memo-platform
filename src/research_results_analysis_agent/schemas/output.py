"""Contrat de sortie — dossier de preuve (SPEC §16).

Aucun champ ne permet de saisir une donnée ou un résultat À LA MAIN : les résultats proviennent
exclusivement du moteur déterministe (`computed_results`).
"""

from enum import Enum

from pydantic import Field

from .analysis import AnalysisPlan, ComputedResults
from .common import Confidence, StrictModel, StrList, Validation
from .decision import StudentValidation
from .draft import ResultsDraft
from .interpretation import Interpretation
from .inventory import Inventory


class ResultsStatus(str, Enum):
    needs_clarification = "needs_clarification"
    blocked = "blocked"
    ready_for_verification = "ready_for_verification"
    verification_failed = "verification_failed"
    awaiting_human_validation = "awaiting_human_validation"
    validated = "validated"


class DocumentStatus(str, Enum):
    """Statut RÉEL du document (SPEC §9 étape 5)."""

    brouillon = "brouillon"
    a_verifier = "a_verifier"
    en_attente_de_validation = "en_attente_de_validation"
    valide = "valide"
    a_reviser = "a_reviser"


class Evidence(StrictModel):
    llm_calls: int = 0
    network_requests: int = 0
    reformulations: int = 0
    calculs: int = 0


class ResultsOutput(StrictModel):
    agent: str = "research_results_analysis_agent"
    version: str = "1.0"
    status: ResultsStatus

    # --- dossier de preuve (SPEC §16) ---
    research_id: str = ""
    generated_at: str = ""
    version_methodologie_utilisee: str = ""
    trace_validation_methodologie: str = ""
    objectifs_examines: StrList = Field(default_factory=list)
    hypotheses_examinees: StrList = Field(default_factory=list)
    origine_des_donnees: StrList = Field(default_factory=list)
    periode_et_perimetre: str = ""
    transformations_effectuees: StrList = Field(default_factory=list)
    methodes_et_parametres: StrList = Field(default_factory=list)
    sources_externes_consultees: StrList = Field(default_factory=list)
    anomalies_et_manquants: StrList = Field(default_factory=list)
    historique_corrections: StrList = Field(default_factory=list)
    document_status: DocumentStatus = DocumentStatus.brouillon
    document_version: str = "1.0"

    # --- rappel du dossier ---
    subject: str = ""
    main_research_question: str = ""
    general_objective: str = ""
    specific_objectives: StrList = Field(default_factory=list)

    # --- le produit de l'étape 10 ---
    inventory: Inventory = Field(default_factory=Inventory)
    computed_results: ComputedResults = Field(default_factory=ComputedResults)
    plan: AnalysisPlan = Field(default_factory=AnalysisPlan)
    interpretation: Interpretation = Field(default_factory=Interpretation)
    draft: ResultsDraft = Field(default_factory=ResultsDraft)

    # --- honnêteté et contrôle ---
    informations_a_confirmer: StrList = Field(default_factory=list)
    missing_information: StrList = Field(default_factory=list)
    unknowns: StrList = Field(default_factory=list)
    questions_for_human: StrList = Field(default_factory=list)
    limits_of_this_output: StrList = Field(default_factory=list)
    coherence_controls: StrList = Field(default_factory=list)
    synthese_pour_conclusion: StrList = Field(default_factory=list)
    verification_result: Validation = Field(default_factory=Validation)
    student_validation: StudentValidation = Field(default_factory=StudentValidation)
    confidence: Confidence = Field(default_factory=Confidence)
    evidence: Evidence = Field(default_factory=Evidence)
