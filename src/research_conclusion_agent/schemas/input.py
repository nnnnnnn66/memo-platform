"""Contrat d'entrée de l'Agent Conclusion (SPEC §6).

Le point de départ est constitué des éléments VALIDÉS des étapes précédentes — en particulier les
résultats et analyses VÉRIFIÉS de l'étape 10. Un chapitre n'est jamais « validé » parce qu'un agent
l'a produit : il l'est si son vérificateur l'a validé (SPEC §5).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import StrList, UpstreamValidation


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont, lue de façon TOLÉRANTE (structure réelle, pas supposée)."""

    model_config = ConfigDict(extra="allow")

    # La clé de vérification DÉPEND DE L'ÉMETTEUR : `validation` (étapes 1-4),
    # `verification_result` (étapes 5-10).
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    verification_result: UpstreamValidation | None = None
    subject: Any = None

    main_research_question: str = ""
    secondary_research_questions: StrList = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: StrList = Field(default_factory=list)
    identified_problem: dict = Field(default_factory=dict)
    research_problem: str = ""
    problematique_note: dict = Field(default_factory=dict)
    validated_problematic: str = ""
    research_hypotheses: list = Field(default_factory=list)
    hypotheses_decision: str = ""
    synthesis: Any = None
    literature_review: Any = None
    diagnostic_status: str = ""
    diagnosis: dict = Field(default_factory=dict)
    protocol: dict = Field(default_factory=dict)

    # --- étape 10 : résultats et analyse ---
    computed_results: dict = Field(default_factory=dict)
    plan: dict = Field(default_factory=dict)
    interpretation: dict = Field(default_factory=dict)
    draft: dict = Field(default_factory=dict)
    synthese_pour_conclusion: StrList = Field(default_factory=list)
    document_status: str = ""
    student_validation: dict = Field(default_factory=dict)

    @property
    def is_verified(self) -> bool:
        if self.validation.verified:
            return True
        return bool(self.verification_result and self.verification_result.verified)

    def subject_line(self) -> str:
        if isinstance(self.subject, str):
            return self.subject.strip()
        if isinstance(self.subject, dict):
            for key in ("intitule", "titre", "subject", "texte"):
                value = str(self.subject.get(key, "") or "").strip()
                if value:
                    return value
        return ""

    def problem_line(self) -> str:
        for candidate in (self.research_problem,
                          (self.identified_problem or {}).get("statement", "")):
            if str(candidate or "").strip():
                return str(candidate).strip()
        return ""

    def problematic_line(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        note = self.problematique_note or {}
        return str(note.get("texte_complet", "") if isinstance(note, dict) else "").strip()

    def hypothesis_formulations(self) -> StrList:
        out: list[str] = []
        for item in self.research_hypotheses or []:
            text = (item.get("formulation") or item.get("statement") or "") \
                if isinstance(item, dict) else item
            text = str(text).strip()
            if text:
                out.append(text)
        return out

    # --- lectures de l'étape 10 (résultats VÉRIFIÉS) ---
    def computed_resultats(self) -> list[dict]:
        resultats = (self.computed_results or {}).get("resultats")
        return [r for r in (resultats or []) if isinstance(r, dict)]

    def computed_ids(self) -> set[str]:
        return {str(r.get("id", "")).strip() for r in self.computed_resultats()}

    def computed_valeurs(self) -> set[str]:
        return {str(r.get("valeur", "")).strip() for r in self.computed_resultats()
                if str(r.get("valeur", "")).strip()}

    def resultats_retenus(self) -> list[dict]:
        resultats = (self.plan or {}).get("resultats")
        return [r for r in (resultats or []) if isinstance(r, dict)]

    def hypotheses_examinees(self) -> list[dict]:
        hypotheses = (self.plan or {}).get("hypotheses")
        return [h for h in (hypotheses or []) if isinstance(h, dict)]

    def plan_seulement(self) -> bool:
        return bool((self.plan or {}).get("plan_seulement"))

    def conclusion_synthese(self) -> StrList:
        """La synthèse préparée par l'étape 10 pour CETTE étape (contrat de passation 10 → 11)."""
        return [str(s).strip() for s in (self.synthese_pour_conclusion or []) if str(s).strip()]

    def sources_litterature(self) -> StrList:
        """Sources réellement disponibles (étape 3) : seules celles-ci peuvent être citées."""
        out: StrList = []
        synthesis = self.synthesis if isinstance(self.synthesis, dict) else {}
        for key in ("references", "bibliographie", "sources"):
            value = synthesis.get(key)
            if isinstance(value, list):
                for item in value:
                    text = str(item.get("reference", "") if isinstance(item, dict) else item).strip()
                    if text:
                        out.append(text)
        if isinstance(self.literature_review, dict):
            for key in ("references", "bibliographie"):
                value = self.literature_review.get(key)
                if isinstance(value, list):
                    out.extend(str(v).strip() for v in value if str(v).strip())
        return out


class ConclusionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str = ""

    subject_text: str = ""
    discipline: str = ""
    academic_level: str = "Master 2"

    # --- consignes (NON fiables : jamais transformées en règle inventée) ---
    university_instructions: str = ""
    supervisor_instructions: str = ""
    student_constraints: str = ""
    student_comments: str = ""
    previous_answers: StrList = Field(default_factory=list)

    # --- sorties amont vérifiées ---
    upstream_subject: UpstreamPayload | None = None
    upstream_problem: UpstreamPayload | None = None
    upstream_literature: UpstreamPayload | None = None
    upstream_problematic: UpstreamPayload | None = None
    upstream_question: UpstreamPayload | None = None
    upstream_objectives: UpstreamPayload | None = None
    upstream_hypotheses: UpstreamPayload | None = None
    upstream_methodology_diagnostic: UpstreamPayload | None = None
    upstream_methodology: UpstreamPayload | None = None
    upstream_results: UpstreamPayload | None = None

    # --- helpers de lecture (chaîne vide si absent : jamais d'invention) ---
    def effective_subject(self) -> str:
        for source in (self.subject_text,
                       self.upstream_subject.subject_line() if self.upstream_subject else "",
                       self.upstream_results.subject_line() if self.upstream_results else ""):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_question(self) -> str:
        for payload in (self.upstream_question, self.upstream_results, self.upstream_methodology):
            if payload is not None and str(payload.main_research_question or "").strip():
                return str(payload.main_research_question).strip()
        return ""

    def effective_secondary_questions(self) -> StrList:
        for payload in (self.upstream_question, self.upstream_results):
            if payload is not None and payload.secondary_research_questions:
                return list(payload.secondary_research_questions)
        return []

    def effective_general_objective(self) -> str:
        for payload in (self.upstream_objectives, self.upstream_results,
                        self.upstream_methodology):
            if payload is not None and str(payload.general_objective or "").strip():
                return str(payload.general_objective).strip()
        return ""

    def effective_specific_objectives(self) -> StrList:
        for payload in (self.upstream_objectives, self.upstream_results,
                        self.upstream_methodology):
            if payload is not None and payload.specific_objectives:
                return list(payload.specific_objectives)
        return []

    def effective_hypotheses(self) -> StrList:
        payload = self.upstream_hypotheses
        return payload.hypothesis_formulations() if payload is not None else []

    def hypotheses_not_required(self) -> bool:
        payload = self.upstream_hypotheses
        if payload is not None and str(payload.hypotheses_decision or "").strip():
            return payload.hypotheses_decision.upper().endswith("NOT_REQUIRED")
        return False

    def effective_problem(self) -> str:
        for payload in (self.upstream_problem, self.upstream_results):
            if payload is not None and payload.problem_line():
                return payload.problem_line()
        return ""

    def effective_problematic(self) -> str:
        for payload in (self.upstream_problematic, self.upstream_question, self.upstream_results):
            if payload is not None and payload.problematic_line():
                return payload.problematic_line()
        return ""

    def methodology_protocol(self) -> dict:
        payload = self.upstream_methodology
        return payload.protocol if payload is not None and isinstance(payload.protocol, dict) else {}

    def results_status(self) -> str:
        payload = self.upstream_results
        return str(payload.document_status or "").strip() if payload is not None else ""

    def results_accepted(self) -> bool:
        payload = self.upstream_results
        if payload is None:
            return False
        decision = (payload.student_validation or {}).get("decision", "")
        return str(decision).lower() in {"accepted", "modified"}

    def computed_ids(self) -> set[str]:
        payload = self.upstream_results
        return payload.computed_ids() if payload is not None else set()

    def computed_valeurs(self) -> set[str]:
        payload = self.upstream_results
        return payload.computed_valeurs() if payload is not None else set()

    def available_results(self) -> bool:
        return bool(self.computed_ids())

    def untrusted_texts(self) -> dict:
        return {
            "subject_text": self.subject_text,
            "university_instructions": self.university_instructions,
            "supervisor_instructions": self.supervisor_instructions,
            "student_constraints": self.student_constraints,
            "student_comments": self.student_comments,
        }

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
