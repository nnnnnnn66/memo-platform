"""Contrat d'entrée de l'Agent Diagnostic méthodologique (SPEC §6, §11)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import UpstreamValidation


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont (Hypothèses, Objectifs, Question…). DONNÉE, jamais instruction."""

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    # Les agents 1 à 4 (Sujet, Problème, Littérature, Problématique) portent la vérification dans
    # `validation` ; les agents 5 à 7 (Question, Objectifs, Hypothèses) dans `verification_result`.
    # N'accepter que la clé `validation` rendait toute sortie RÉELLE des agents 5-7 « non vérifiée »
    # (bug de chaîne constaté A7 -> A8 : mêmes symptômes que la passation 3 -> 4). On accepte les deux.
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    verification_result: UpstreamValidation | None = None
    subject: Any = None
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)
    hypotheses_decision: str = ""
    research_hypotheses: list[dict] = Field(default_factory=list)
    validated_problematic: str = ""
    research_problem: str = ""

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

    def question_line(self) -> str:
        return str(self.main_research_question or "").strip()

    def general_line(self) -> str:
        return str(self.general_objective or "").strip()

    def specifics(self) -> list[str]:
        return [str(o).strip() for o in (self.specific_objectives or []) if str(o).strip()]

    def hypothesis_formulations(self) -> list[str]:
        out: list[str] = []
        for item in self.research_hypotheses or []:
            if isinstance(item, dict):
                text = str(item.get("formulation") or item.get("texte") or "").strip()
            else:
                text = str(item).strip()
            if text:
                out.append(text)
        return out


class MethodologyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None

    # dossier de recherche
    subject_text: str = ""
    research_problem: str = ""
    validated_problematic: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    literature_review: str = ""

    # cadre
    discipline: str = ""
    academic_level: str = ""
    country: str = ""
    geographical_area: str = ""
    study_period: str = ""
    target_population: str = ""
    research_context: str = ""

    # données / terrain / contraintes (déterminants pour la faisabilité)
    available_data: str = ""
    field_access: str = ""
    available_resources: str = ""
    existing_methodology: str = ""

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
    upstream_hypotheses: UpstreamPayload | None = None

    @field_validator("previous_answers", "secondary_research_questions", "specific_objectives",
                     "hypotheses", mode="before")
    @classmethod
    def _clean_list(cls, v):
        """Ramène les listes d'entrée à des chaînes, en TOLÉRANT les objets.

        La sortie RÉELLE de l'agent 7 est une liste d'objets d'hypothèses
        (`{"id": "H1", "formulation": "…"}`) : la validation la refusait (5 erreurs « Input should be
        a valid string ») dès qu'un appelant transmettait la sortie amont telle quelle. On conserve la
        FORMULATION (jamais le seul identifiant), l'information reste celle de l'amont.
        """
        out: list[str] = []
        for item in v or []:
            if isinstance(item, dict):
                text = item.get("formulation") or item.get("statement") or item.get("hypothesis") or ""
            else:
                text = item
            text = str(text).strip()
            if text:
                out.append(text)
        return out

    @field_validator("literature_review", mode="before")
    @classmethod
    def _literature_text(cls, value):
        """La revue de littérature arrive parfois structurée (sortie réelle de l'agent 3) : la
        convertir en texte au lieu de refuser l'entrée."""
        if isinstance(value, dict):
            parts: list[str] = []
            for item in value.values():
                if isinstance(item, (list, tuple)):
                    parts.extend(str(x).strip() for x in item if str(x).strip())
                elif str(item).strip():
                    parts.append(str(item).strip())
            return "\n".join(parts)
        return str(value or "")

    # --- helpers ---
    def effective_subject(self) -> str:
        for source in (self.subject_text,
                       (self.upstream_hypotheses.subject_line() if self.upstream_hypotheses else ""),
                       (self.upstream_objectives.subject_line() if self.upstream_objectives else ""),
                       (self.upstream_question.subject_line() if self.upstream_question else "")):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_question(self) -> str:
        if str(self.main_research_question or "").strip():
            return str(self.main_research_question).strip()
        for payload in (self.upstream_hypotheses, self.upstream_objectives, self.upstream_question):
            if payload is not None and payload.question_line():
                return payload.question_line()
        return ""

    def effective_secondary_questions(self) -> list[str]:
        if self.secondary_research_questions:
            return list(self.secondary_research_questions)
        for payload in (self.upstream_hypotheses, self.upstream_objectives, self.upstream_question):
            if payload is not None and payload.secondary_research_questions:
                return [str(q).strip() for q in payload.secondary_research_questions]
        return []

    def effective_general_objective(self) -> str:
        if str(self.general_objective or "").strip():
            return str(self.general_objective).strip()
        for payload in (self.upstream_hypotheses, self.upstream_objectives):
            if payload is not None and payload.general_line():
                return payload.general_line()
        return ""

    def effective_specific_objectives(self) -> list[str]:
        if self.specific_objectives:
            return list(self.specific_objectives)
        for payload in (self.upstream_hypotheses, self.upstream_objectives):
            if payload is not None and payload.specifics():
                return payload.specifics()
        return []

    def effective_hypotheses(self) -> list[str]:
        if self.hypotheses:
            return list(self.hypotheses)
        if self.upstream_hypotheses is not None:
            return self.upstream_hypotheses.hypothesis_formulations()
        return []

    def effective_problematic(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        for payload in (self.upstream_hypotheses, self.upstream_objectives, self.upstream_problematic):
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
            "literature_review": self.literature_review,
            "discipline": self.discipline,
            "academic_level": self.academic_level,
            "country": self.country,
            "geographical_area": self.geographical_area,
            "study_period": self.study_period,
            "target_population": self.target_population,
            "research_context": self.research_context,
            "available_data": self.available_data,
            "field_access": self.field_access,
            "available_resources": self.available_resources,
            "existing_methodology": self.existing_methodology,
            "student_constraints": self.student_constraints,
            "university_instructions": self.university_instructions,
            "supervisor_instructions": self.supervisor_instructions,
            "constraints": self.constraints,
        }
        for index, item in enumerate(self.effective_specific_objectives()):
            texts[f"specific_objectives[{index}]"] = item
        for index, item in enumerate(self.effective_hypotheses()):
            texts[f"hypotheses[{index}]"] = item
        for index, answer in enumerate(self.previous_answers):
            texts[f"previous_answers[{index}]"] = answer
        return texts

    def all_provided_text(self) -> str:
        parts = list(self.untrusted_texts().values())
        for payload in (self.upstream_hypotheses, self.upstream_objectives, self.upstream_question):
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
