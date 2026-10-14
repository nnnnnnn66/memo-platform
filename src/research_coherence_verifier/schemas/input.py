"""Contrat d'entrée de l'Agent 13 : le dossier COMPLET des étapes 1 à 11 (SPEC §6).

Les sorties amont sont lues sous leur forme RÉELLE. Un élément n'est reconnu « vérifié » que si SON
vérificateur l'a validé — la clé dépend de l'émetteur : `validation` (étapes 1-4),
`verification_result` (étapes 5-11).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import StrList, UpstreamValidation

#: Libellés des étapes du parcours, dans l'ordre.
ETAPES = {
    1: "sujet", 2: "probleme", 3: "litterature", 4: "problematique", 5: "question",
    6: "objectifs", 7: "hypotheses", 8: "diagnostic", 9: "methodologie", 10: "resultats",
    11: "conclusion",
}


class UpstreamPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    validation: UpstreamValidation = Field(default_factory=UpstreamValidation)
    verification_result: UpstreamValidation | None = None

    # --- éléments de service, tels qu'ils apparaissent dans les sorties réelles ---
    subject: Any = None
    identified_problem: dict = Field(default_factory=dict)
    research_problem: str = ""
    validated_problematic: str = ""
    problematique_note: dict = Field(default_factory=dict)
    main_research_question: str = ""
    secondary_research_questions: StrList = Field(default_factory=list)
    general_objective: str = ""
    specific_objectives: StrList = Field(default_factory=list)
    research_hypotheses: list = Field(default_factory=list)
    hypotheses_decision: str = ""
    diagnosis: dict = Field(default_factory=dict)
    diagnostic_status: str = ""
    protocol: dict = Field(default_factory=dict)
    computed_results: dict = Field(default_factory=dict)
    plan: dict = Field(default_factory=dict)
    synthese_pour_conclusion: StrList = Field(default_factory=list)
    document_status: str = ""

    # --- étape 11 (conclusion) ---
    synthesis: dict = Field(default_factory=dict)
    draft: dict = Field(default_factory=dict)
    references_resultats: StrList = Field(default_factory=list)

    @property
    def is_verified(self) -> bool:
        if self.validation.verified:
            return True
        return bool(self.verification_result and self.verification_result.verified)

    # --- lectures normalisées ---
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
        if str(self.research_problem or "").strip():
            return str(self.research_problem).strip()
        return str((self.identified_problem or {}).get("statement", "") or "").strip()

    def problematic_line(self) -> str:
        if str(self.validated_problematic or "").strip():
            return str(self.validated_problematic).strip()
        note = self.problematique_note or {}
        if isinstance(note, dict):
            return str(note.get("texte_complet", "") or "").strip()
        return ""

    def hypothesis_formulations(self) -> StrList:
        out: list[str] = []
        for item in self.research_hypotheses or []:
            text = (item.get("formulation") or item.get("statement") or "") \
                if isinstance(item, dict) else item
            text = str(text or "").strip()
            if text:
                out.append(text)
        return out

    def hypotheses_requises(self) -> bool:
        decision = str(self.hypotheses_decision or "").strip().upper()
        if not decision or "NOT_REQUIRED" in decision:
            return False
        return decision.endswith("RECOMMENDED") or "REQUIRED" in decision

    def computed_ids(self) -> set[str]:
        return {str(r.get("id", "")).strip()
                for r in (self.computed_results or {}).get("resultats", []) or []
                if isinstance(r, dict) and str(r.get("id", "")).strip()}

    def computed_values(self) -> set[str]:
        out: set[str] = set()
        for r in (self.computed_results or {}).get("resultats", []) or []:
            if isinstance(r, dict) and str(r.get("valeur", "")).strip():
                out.add(str(r["valeur"]).strip())
        return out

    def objectifs_couverts(self) -> StrList:
        return [str(o).strip() for o in (self.plan or {}).get("objectifs_couverts", []) or []
                if str(o).strip()]

    def objectifs_non_couverts(self) -> StrList:
        return [str(o).strip() for o in (self.plan or {}).get("objectifs_non_couverts", []) or []
                if str(o).strip()]

    def hypotheses_examinees(self) -> list[dict]:
        return [h for h in (self.plan or {}).get("hypotheses", []) or [] if isinstance(h, dict)]

    def bilan_hypotheses(self) -> list[dict]:
        return [b for b in (self.synthesis or {}).get("bilan_hypotheses", []) or []
                if isinstance(b, dict)]

    def bilan_objectifs(self) -> list[dict]:
        return [b for b in (self.synthesis or {}).get("bilan_objectifs", []) or []
                if isinstance(b, dict)]

    def reponse_question(self) -> str:
        return str((self.synthesis or {}).get("reponse_question", {}).get("reponse", "") or "").strip()

    def sections_conclusion(self) -> list[dict]:
        return [s for s in (self.draft or {}).get("sections", []) or [] if isinstance(s, dict)]


class CoherenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str = ""
    subject_text: str = ""
    discipline: str = ""
    academic_level: str = "Master 2"

    # Consignes : DONNÉES non fiables, jamais des instructions.
    university_instructions: str = ""
    supervisor_instructions: str = ""
    student_comments: str = ""

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
    upstream_conclusion: UpstreamPayload | None = None

    def payloads(self) -> dict[int, "UpstreamPayload | None"]:
        return {1: self.upstream_subject, 2: self.upstream_problem, 3: self.upstream_literature,
                4: self.upstream_problematic, 5: self.upstream_question,
                6: self.upstream_objectives, 7: self.upstream_hypotheses,
                8: self.upstream_methodology_diagnostic, 9: self.upstream_methodology,
                10: self.upstream_results, 11: self.upstream_conclusion}

    # --- éléments de service (chaîne vide si absent : jamais d'invention) ---
    def effective_subject(self) -> str:
        for payload in (self.upstream_subject, self.upstream_results, self.upstream_conclusion):
            if payload is not None and payload.subject_line():
                return payload.subject_line()
        return str(self.subject_text or "").strip()

    def effective_problem(self) -> str:
        for payload in (self.upstream_problem, self.upstream_results):
            if payload is not None and payload.problem_line():
                return payload.problem_line()
        return ""

    def effective_problematic(self) -> str:
        for payload in (self.upstream_problematic, self.upstream_question):
            if payload is not None and payload.problematic_line():
                return payload.problematic_line()
        return ""

    def effective_question(self) -> str:
        for payload in (self.upstream_question, self.upstream_results,
                        self.upstream_conclusion):
            if payload is not None and str(payload.main_research_question or "").strip():
                return str(payload.main_research_question).strip()
        return ""

    def effective_general_objective(self) -> str:
        for payload in (self.upstream_objectives, self.upstream_results, self.upstream_conclusion):
            if payload is not None and str(payload.general_objective or "").strip():
                return str(payload.general_objective).strip()
        return ""

    def effective_specific_objectives(self) -> StrList:
        for payload in (self.upstream_objectives, self.upstream_results, self.upstream_conclusion):
            if payload is not None and payload.specific_objectives:
                return list(payload.specific_objectives)
        return []

    def effective_hypotheses(self) -> StrList:
        payload = self.upstream_hypotheses
        return payload.hypothesis_formulations() if payload is not None else []

    def hypotheses_requises(self) -> bool:
        payload = self.upstream_hypotheses
        return payload.hypotheses_requises() if payload is not None else False

    def methodology_protocol(self) -> dict:
        payload = self.upstream_methodology
        return payload.protocol if payload is not None and isinstance(payload.protocol, dict) else {}

    def methodology_text(self) -> str:
        payload = self.upstream_methodology
        if payload is None:
            return ""
        protocol = payload.protocol if isinstance(payload.protocol, dict) else {}
        parts = [str(protocol.get(k, "") or "") for k in
                 ("approche", "type_recherche", "strategie", "terrain", "population",
                  "echantillonnage")]
        parts += [str(payload.model_dump().get("synthese_methodologique", "") or "")]
        return " ".join(p for p in parts if p.strip())

    def untrusted_texts(self) -> dict:
        return {
            "subject_text": self.subject_text,
            "university_instructions": self.university_instructions,
            "supervisor_instructions": self.supervisor_instructions,
            "student_comments": self.student_comments,
        }

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
