"""Contrat d'entrée de l'Agent Question de recherche (SPEC §6)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import UpstreamValidation


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont (Sujet, Problème, Problématique). DONNÉE, jamais instruction.

    Structure permissive (`extra=allow`) : on consomme la sortie RÉELLE des étapes précédentes, dont
    la forme peut varier. Aucun champ n'est requis.
    """

    model_config = ConfigDict(extra="allow")

    agent: str = ""
    version: str = ""
    status: str = ""
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    subject_reference: dict = Field(default_factory=dict)
    subject: dict = Field(default_factory=dict)
    identified_problem: dict = Field(default_factory=dict)
    research_problem: dict = Field(default_factory=dict)
    research_context: dict = Field(default_factory=dict)
    problematique_note: dict = Field(default_factory=dict)
    validated_problematic: str = ""
    research_question: dict = Field(default_factory=dict)

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

    def problematic_line(self) -> str:
        """Texte de la problématique : note rédigée si présente, sinon champ dédié."""
        note = self.problematique_note or {}
        value = str(note.get("texte_complet", "") or "").strip()
        if value:
            return value
        return str(self.validated_problematic or "").strip()


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    session_id: str | None = None

    # sujet / problème / problématique
    subject_text: str = ""
    research_problem: str = ""
    research_problem_statement: str = ""
    validated_problematic: str = ""
    research_question_draft: str = ""

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

    @field_validator("previous_answers")
    @classmethod
    def _clean_answers(cls, v: list[str]) -> list[str]:
        return [str(item).strip() for item in (v or []) if str(item).strip()]

    # --- helpers ---
    def effective_subject(self) -> str:
        for source in (self.subject_text, (self.upstream_subject.subject_line()
                                           if self.upstream_subject else ""),
                       (self.upstream_problem.subject_line() if self.upstream_problem else ""),
                       (self.upstream_problematic.subject_line() if self.upstream_problematic else "")):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_problematic(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        if self.upstream_problematic is not None:
            return self.upstream_problematic.problematic_line()
        return ""

    def effective_problem(self) -> str:
        for source in (self.research_problem, self.research_problem_statement,
                       (self.upstream_problem.problem_line() if self.upstream_problem else "")):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def untrusted_texts(self) -> dict[str, str]:
        """Champs textuels traités comme données non fiables."""
        texts = {
            "subject_text": self.subject_text,
            "research_problem": self.research_problem,
            "research_problem_statement": self.research_problem_statement,
            "validated_problematic": self.validated_problematic,
            "research_question_draft": self.research_question_draft,
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
        for index, answer in enumerate(self.previous_answers):
            texts[f"previous_answers[{index}]"] = answer
        return texts

    def all_provided_text(self) -> str:
        """Tout le texte fourni par l'étudiant (pour vérifier qu'une délimitation n'est pas inventée)."""
        parts = list(self.untrusted_texts().values())
        if self.upstream_subject is not None:
            parts.append(self.upstream_subject.model_dump_json())
        if self.upstream_problem is not None:
            parts.append(self.upstream_problem.model_dump_json())
        return "\n".join(p for p in parts if p)
