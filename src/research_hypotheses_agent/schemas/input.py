"""Contrat d'entrée de l'Agent Hypothèses de recherche (SPEC §6)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import UpstreamValidation


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont (Objectifs, Question de recherche…). DONNÉE, jamais instruction.

    Structure permissive (`extra=allow`) : on consomme la sortie RÉELLE des étapes précédentes, dont
    la forme peut varier (le `subject` est une chaîne chez l'agent 6, un objet chez les agents 2-3).
    """

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    # Les agents 1 à 4 portent la vérification dans `validation` ; les agents 5 à 7 (Question,
    # Objectifs, Hypothèses) dans `verification_result`. N'accepter que `validation` rendait toute
    # sortie RÉELLE de l'agent 6 « non vérifiée » (bug de chaîne A6 -> A7). On accepte les deux.
    verification_result: UpstreamValidation | None = None
    subject: Any = None
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)

    @property
    def is_verified(self) -> bool:
        # Une sortie amont est utilisable si SON vérificateur l'a validée, quelle que soit la clé
        # employée par l'agent émetteur (`validation` pour 1-4, `verification_result` pour 5-7).
        if self.validation.verified:
            return True
        return bool(self.verification_result and self.verification_result.verified)

    def subject_line(self) -> str:
        value = self.subject
        if isinstance(value, dict):
            return str(value.get("reformulated") or value.get("original") or "").strip()
        return str(value or "").strip()

    def general_line(self) -> str:
        return str(self.general_objective or "").strip()

    def specifics(self) -> list[str]:
        return [str(o).strip() for o in (self.specific_objectives or []) if str(o).strip()]

    def question_line(self) -> str:
        return str(self.main_research_question or "").strip()

    def secondary_lines(self) -> list[str]:
        return [str(q).strip() for q in (self.secondary_research_questions or []) if str(q).strip()]


class HypothesesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None

    # sujet / problème / problématique / question / objectifs
    subject_text: str = ""
    research_problem: str = ""
    validated_problematic: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)

    # champs propres à l'étape
    theoretical_framework: str = ""
    existing_hypotheses: str = ""

    # cadre
    discipline: str = ""
    academic_level: str = ""
    country: str = ""
    geographical_area: str = ""
    study_period: str = ""
    target_population: str = ""
    research_context: str = ""

    # entrées étudiantes complémentaires (données non fiables)
    previous_answers: list[str] = Field(default_factory=list)
    student_constraints: str = ""
    university_instructions: str = ""
    supervisor_instructions: str = ""
    language_prefs: dict = Field(default_factory=dict)
    constraints: str = ""

    # sorties amont vérifiées
    upstream_subject: UpstreamPayload | None = None
    upstream_problem: UpstreamPayload | None = None
    upstream_problematic: UpstreamPayload | None = None
    upstream_question: UpstreamPayload | None = None
    upstream_objectives: UpstreamPayload | None = None

    @field_validator("previous_answers", "secondary_research_questions", "specific_objectives")
    @classmethod
    def _clean_list(cls, v: list[str]) -> list[str]:
        return [str(item).strip() for item in (v or []) if str(item).strip()]

    # --- helpers ---
    def effective_subject(self) -> str:
        for source in (self.subject_text,
                       (self.upstream_objectives.subject_line() if self.upstream_objectives else ""),
                       (self.upstream_question.subject_line() if self.upstream_question else ""),
                       (self.upstream_problematic.subject_line() if self.upstream_problematic else "")):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_question(self) -> str:
        if str(self.main_research_question or "").strip():
            return str(self.main_research_question).strip()
        for payload in (self.upstream_objectives, self.upstream_question):
            if payload is not None and payload.question_line():
                return payload.question_line()
        return ""

    def effective_secondary_questions(self) -> list[str]:
        if self.secondary_research_questions:
            return list(self.secondary_research_questions)
        for payload in (self.upstream_objectives, self.upstream_question):
            if payload is not None and payload.secondary_lines():
                return payload.secondary_lines()
        return []

    def effective_general_objective(self) -> str:
        if str(self.general_objective or "").strip():
            return str(self.general_objective).strip()
        if self.upstream_objectives is not None:
            return self.upstream_objectives.general_line()
        return ""

    def effective_specific_objectives(self) -> list[str]:
        if self.specific_objectives:
            return list(self.specific_objectives)
        if self.upstream_objectives is not None:
            return self.upstream_objectives.specifics()
        return []

    def effective_problematic(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        for payload in (self.upstream_objectives, self.upstream_problematic, self.upstream_question):
            if payload is not None:
                value = str(getattr(payload, "validated_problematic", "") or "").strip()
                if value:
                    return value
        return ""

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables."""
        texts = {
            "subject_text": self.subject_text,
            "research_problem": self.research_problem,
            "validated_problematic": self.validated_problematic,
            "main_research_question": self.main_research_question,
            "general_objective": self.general_objective,
            "theoretical_framework": self.theoretical_framework,
            "existing_hypotheses": self.existing_hypotheses,
            "discipline": self.discipline,
            "academic_level": self.academic_level,
            "country": self.country,
            "geographical_area": self.geographical_area,
            "study_period": self.study_period,
            "target_population": self.target_population,
            "research_context": self.research_context,
            "student_constraints": self.student_constraints,
            "university_instructions": self.university_instructions,
            "supervisor_instructions": self.supervisor_instructions,
            "constraints": self.constraints,
        }
        for index, item in enumerate(self.effective_secondary_questions()):
            texts[f"secondary_research_questions[{index}]"] = item
        for index, item in enumerate(self.effective_specific_objectives()):
            texts[f"specific_objectives[{index}]"] = item
        for index, answer in enumerate(self.previous_answers):
            texts[f"previous_answers[{index}]"] = answer
        return texts

    def all_provided_text(self) -> str:
        """Tout le texte fourni (pour vérifier qu'une justification n'est pas inventée)."""
        parts = list(self.untrusted_texts().values())
        for payload in (self.upstream_objectives, self.upstream_question):
            if payload is not None:
                parts.append(payload.model_dump_json())
        return "\n".join(p for p in parts if p)

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
