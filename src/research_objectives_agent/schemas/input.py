"""Contrat d'entrée de l'Agent Objectifs de recherche (SPEC §6)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import UpstreamValidation


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont (Question de recherche, Problématique…). DONNÉE, jamais instruction.

    Structure permissive (`extra=allow`) : on consomme la sortie RÉELLE des étapes précédentes, dont
    la forme peut varier (le `subject` est une chaîne chez l'agent 5, un objet chez les agents 2-3).
    """

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    # Les agents 1 à 4 (Sujet, Problème, Littérature, Problématique) portent la vérification dans
    # `validation` ; les agents 5 à 7 (Question, Objectifs, Hypothèses) dans `verification_result`.
    # N'accepter que `validation` rendait toute sortie RÉELLE de l'agent 5 « non vérifiée » (bug de
    # chaîne constaté A5 -> A6, mêmes symptômes que 3 -> 4 et 7 -> 8). On accepte les deux.
    verification_result: UpstreamValidation | None = None
    subject: Any = None
    # Champs des sorties RÉELLES des étapes amont, tels qu'ils sont réellement produits :
    # l'agent 2 publie `identified_problem.statement` (pas `research_problem`), l'agent 4 publie
    # `problematique_note.texte_complet` (pas `validated_problematic`). Les lire « en dur » faisait
    # échouer la passation 2 -> 6 sur un simple AttributeError (chaîne réelle).
    research_problem: str = ""
    identified_problem: dict = Field(default_factory=dict)
    problematique_note: dict = Field(default_factory=dict)
    validated_problematic: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    research_intention: dict = Field(default_factory=dict)

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
        """Question de recherche transmise (champ direct, ou imbriquée `research_question.main`)."""
        direct = str(self.main_research_question or "").strip()
        if direct:
            return direct
        nested = getattr(self, "research_question", None)
        if isinstance(nested, dict):
            return str(nested.get("main") or "").strip()
        return ""

    def secondary_lines(self) -> list[str]:
        direct = [str(q).strip() for q in (self.secondary_research_questions or []) if str(q).strip()]
        if direct:
            return direct
        nested = getattr(self, "research_question", None)
        if isinstance(nested, dict):
            return [str(q).strip() for q in (nested.get("secondary") or []) if str(q).strip()]
        return []


class ObjectivesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None

    # sujet / problème / problématique / question de recherche
    subject_text: str = ""
    research_problem: str = ""
    validated_problematic: str = ""
    main_research_question: str = ""
    secondary_research_questions: list[str] = Field(default_factory=list)
    objectives_draft: str = ""

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

    @field_validator("previous_answers", "secondary_research_questions")
    @classmethod
    def _clean_list(cls, v: list[str]) -> list[str]:
        return [str(item).strip() for item in (v or []) if str(item).strip()]

    # --- helpers ---
    def effective_subject(self) -> str:
        for source in (self.subject_text,
                       (self.upstream_question.subject_line() if self.upstream_question else ""),
                       (self.upstream_subject.subject_line() if self.upstream_subject else ""),
                       (self.upstream_problematic.subject_line() if self.upstream_problematic else "")):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_question(self) -> str:
        """Question de recherche principale : champ direct, sinon sortie amont vérifiée."""
        if str(self.main_research_question or "").strip():
            return str(self.main_research_question).strip()
        if self.upstream_question is not None:
            return self.upstream_question.question_line()
        return ""

    def effective_secondary_questions(self) -> list[str]:
        if self.secondary_research_questions:
            return list(self.secondary_research_questions)
        if self.upstream_question is not None:
            return self.upstream_question.secondary_lines()
        return []

    def effective_problematic(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        # `validated_problematic` vient de l'agent 5 ; l'agent 4 publie la même matière sous
        # `problematique_note.texte_complet` (forme réelle de sa sortie).
        for candidate in (self.upstream_problematic, self.upstream_question):
            if candidate is None:
                continue
            direct = str(getattr(candidate, "validated_problematic", "") or "").strip()
            if direct:
                return direct
            note = getattr(candidate, "problematique_note", None) or {}
            text = str(note.get("texte_complet", "") if isinstance(note, dict) else "").strip()
            if text:
                return text
        return ""

    def effective_problem(self) -> str:
        if str(self.research_problem or "").strip():
            return str(self.research_problem).strip()
        for candidate in (self.upstream_problem, self.upstream_question):
            if candidate is None:
                continue
            direct = str(getattr(candidate, "research_problem", "") or "").strip()
            if direct:
                return direct
            problem = getattr(candidate, "identified_problem", None) or {}
            statement = str(problem.get("statement", "") if isinstance(problem, dict)
                            else "").strip()
            if statement:
                return statement
        return ""

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables."""
        texts = {
            "subject_text": self.subject_text,
            "research_problem": self.research_problem,
            "validated_problematic": self.validated_problematic,
            "main_research_question": self.main_research_question,
            "objectives_draft": self.objectives_draft,
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
        for index, question in enumerate(self.effective_secondary_questions()):
            texts[f"secondary_research_questions[{index}]"] = question
        for index, answer in enumerate(self.previous_answers):
            texts[f"previous_answers[{index}]"] = answer
        return texts

    def all_provided_text(self) -> str:
        """Tout le texte fourni (pour vérifier qu'une délimitation n'est pas inventée)."""
        parts = list(self.untrusted_texts().values())
        if self.upstream_question is not None:
            parts.append(self.upstream_question.model_dump_json())
        if self.upstream_problematic is not None:
            parts.append(self.upstream_problematic.model_dump_json())
        return "\n".join(p for p in parts if p)

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
