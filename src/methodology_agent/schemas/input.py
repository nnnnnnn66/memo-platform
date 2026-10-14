"""Contrat d'entrée de l'Agent Méthodologie (SPEC §6).

Le diagnostic vérifié de l'agent 8 est le point de départ. Les sorties amont ne sont utilisables que
si LEUR vérificateur les a validées, et les champs sont lus sous la forme RÉELLEMENT produite par
l'émetteur (leçon de la chaîne 1 → 8 : une clé supposée casse la passation en silence).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import StrList, UpstreamValidation


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont, lue de façon TOLÉRANTE (structure réelle, pas supposée)."""

    model_config = ConfigDict(extra="allow")

    # La clé de vérification DÉPEND DE L'ÉMETTEUR : `validation` pour les agents 1 à 4,
    # `verification_result` pour les agents 5 à 8. N'accepter qu'une seule forme déclare
    # « non vérifiée » une sortie pourtant validée (bug de chaîne réel, corrigé ici d'emblée).
    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    verification_result: UpstreamValidation | None = None
    subject: Any = None

    # --- champs réellement produits par les étapes amont (formes réelles) ---
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

    # --- diagnostic méthodologique (agent 8) ---
    diagnostic_status: str = ""
    provisional: bool = True
    diagnosis: dict = Field(default_factory=dict)
    student_validation: dict = Field(default_factory=dict)
    methodes_analyse: list = Field(default_factory=list)

    @property
    def is_verified(self) -> bool:
        """Vérifiée si l'émetteur a posé `verified = true`, quelle que soit la clé employée."""
        if self.validation.verified:
            return True
        return bool(self.verification_result and self.verification_result.verified)

    # --- lectures tolérantes (jamais un accès supposé) ---
    def subject_line(self) -> str:
        if isinstance(self.subject, str):
            return self.subject.strip()
        if isinstance(self.subject, dict):
            for key in ("intitule", "titre", "subject", "texte"):
                value = str(self.subject.get(key, "") or "").strip()
                if value:
                    return value
        return str(getattr(self, "subject_text", "") or "").strip()

    def problem_line(self) -> str:
        for candidate in (getattr(self, "research_problem", ""),
                          (self.identified_problem or {}).get("statement", "")):
            if str(candidate or "").strip():
                return str(candidate).strip()
        return ""

    def problematic_line(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        note = self.problematique_note or {}
        return str(note.get("texte_complet", "") if isinstance(note, dict) else "").strip()

    def hypothesis_formulations(self) -> list[str]:
        """La sortie de l'agent 7 arrive sous forme d'OBJETS : garder la FORMULATION."""
        out: list[str] = []
        for item in self.research_hypotheses or []:
            if isinstance(item, dict):
                text = item.get("formulation") or item.get("statement") or ""
            else:
                text = item
            text = str(text).strip()
            if text:
                out.append(text)
        return out

    def diagnostic_categories(self) -> dict:
        """Les six catégories de l'agent 8, sous forme {categorie: {code, proposition, ...}}."""
        return self.diagnosis if isinstance(self.diagnosis, dict) else {}

    def diagnostic_line(self) -> str:
        categories = self.diagnostic_categories()
        parts = []
        for name in ("approche", "logique", "type_recherche", "strategie"):
            entry = categories.get(name) or {}
            if isinstance(entry, dict):
                text = entry.get("proposition") or entry.get("code") or ""
                if str(text).strip():
                    parts.append(f"{name} : {text}")
        for name in ("collecte", "analyse"):
            entries = categories.get(name) or []
            for entry in entries if isinstance(entries, list) else []:
                if isinstance(entry, dict):
                    text = entry.get("proposition") or entry.get("code") or ""
                    if str(text).strip():
                        parts.append(f"{name} : {text}")
        return " | ".join(parts)


class MethodologyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # --- identification (isolation) ---
    student_id: str = ""
    session_id: str = ""

    # --- contexte du travail ---
    subject_text: str = ""
    discipline: str = ""
    academic_level: str = "Master 2"
    country: str = "Côte d'Ivoire"
    geographical_area: str = ""
    study_period: str = ""
    target_population: str = ""
    research_context: str = ""

    # --- état d'avancement et faisabilité (données NON fiables) ---
    existing_methodology: str = ""
    field_access: str = ""
    available_data: str = ""
    available_resources: str = ""
    available_tools: str = ""
    student_constraints: str = ""
    constraints: str = ""
    previous_answers: StrList = Field(default_factory=list)
    # Preuves fournies par l'étudiant de ce qui est DÉJÀ RÉALISÉ (autorisation obtenue, pré-enquête,
    # données déjà collectées…). Sans preuve, une affirmation au passé est refusée (règle P1).
    realise_preuves: StrList = Field(default_factory=list)

    # --- consignes académiques (non fiables : jamais transformées en règle de l'établissement) ---
    university_instructions: str = ""
    supervisor_instructions: str = ""

    # --- sorties amont vérifiées ---
    upstream_subject: UpstreamPayload | None = None
    upstream_problem: UpstreamPayload | None = None
    upstream_literature: UpstreamPayload | None = None
    upstream_problematic: UpstreamPayload | None = None
    upstream_question: UpstreamPayload | None = None
    upstream_objectives: UpstreamPayload | None = None
    upstream_hypotheses: UpstreamPayload | None = None
    upstream_methodology_diagnostic: UpstreamPayload | None = None

    # --- helpers de lecture (jamais d'invention : chaîne vide si absent) ---
    def effective_subject(self) -> str:
        for source in (self.subject_text,
                       self.upstream_subject.subject_line() if self.upstream_subject else "",
                       self.upstream_methodology_diagnostic.subject_line()
                       if self.upstream_methodology_diagnostic else ""):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_question(self) -> str:
        for source in (self.upstream_question.main_research_question if self.upstream_question
                       else "",
                       self.upstream_objectives.main_research_question
                       if self.upstream_objectives else "",
                       self.upstream_methodology_diagnostic.main_research_question
                       if self.upstream_methodology_diagnostic else ""):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_secondary_questions(self) -> list[str]:
        for payload in (self.upstream_question, self.upstream_objectives,
                        self.upstream_methodology_diagnostic):
            if payload is not None and payload.secondary_research_questions:
                return list(payload.secondary_research_questions)
        return []

    def effective_general_objective(self) -> str:
        for payload in (self.upstream_objectives, self.upstream_methodology_diagnostic,
                        self.upstream_question):
            if payload is not None and str(payload.general_objective or "").strip():
                return str(payload.general_objective).strip()
        return ""

    def effective_specific_objectives(self) -> list[str]:
        for payload in (self.upstream_objectives, self.upstream_methodology_diagnostic,
                        self.upstream_question):
            if payload is not None and payload.specific_objectives:
                return list(payload.specific_objectives)
        return []

    def effective_hypotheses(self) -> list[str]:
        for payload in (self.upstream_hypotheses, self.upstream_methodology_diagnostic):
            if payload is not None and payload.hypothesis_formulations():
                return payload.hypothesis_formulations()
        return []

    def hypotheses_not_required(self) -> bool:
        """L'agent 7 a conclu qu'aucune hypothèse n'est pertinente : ne jamais en ajouter."""
        for payload in (self.upstream_hypotheses, self.upstream_methodology_diagnostic):
            if payload is not None and str(payload.hypotheses_decision or "").strip():
                return payload.hypotheses_decision.upper().endswith("NOT_REQUIRED")
        return False

    def effective_problematic(self) -> str:
        for payload in (self.upstream_problematic, self.upstream_question,
                        self.upstream_methodology_diagnostic):
            if payload is not None and payload.problematic_line():
                return payload.problematic_line()
        return ""

    def effective_problem(self) -> str:
        for payload in (self.upstream_problem, self.upstream_methodology_diagnostic):
            if payload is not None and payload.problem_line():
                return payload.problem_line()
        return ""

    def diagnostic_categories(self) -> dict:
        payload = self.upstream_methodology_diagnostic
        return payload.diagnostic_categories() if payload is not None else {}

    def diagnostic_status(self) -> str:
        payload = self.upstream_methodology_diagnostic
        return str(payload.diagnostic_status or "").strip() if payload is not None else ""

    def diagnostic_accepted(self) -> bool:
        """La décision humaine sur le diagnostic a-t-elle été rendue ?"""
        payload = self.upstream_methodology_diagnostic
        if payload is None:
            return False
        decision = (payload.student_validation or {}).get("decision", "")
        return str(decision).lower() in {"accepted", "modified"}

    def untrusted_texts(self) -> dict:
        """Tout champ texte fourni par l'étudiant (donnée NON fiable)."""
        return {
            "subject_text": self.subject_text,
            "research_context": self.research_context,
            "existing_methodology": self.existing_methodology,
            "field_access": self.field_access,
            "available_data": self.available_data,
            "available_resources": self.available_resources,
            "available_tools": self.available_tools,
            "student_constraints": self.student_constraints or self.constraints,
            "university_instructions": self.university_instructions,
            "supervisor_instructions": self.supervisor_instructions,
        }


class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
