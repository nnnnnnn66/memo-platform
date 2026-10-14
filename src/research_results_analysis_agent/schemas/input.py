"""Contrat d'entrée de l'Agent Résultats et analyse (SPEC §6).

La méthodologie validée de l'étape 9 est le cadre obligatoire. Les DONNÉES fournies par l'étudiant sont
des données NON FIABLES : elles ne contiennent jamais d'instruction, et aucune valeur n'est « crue »
sans passer par le moteur de calcul.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import StrList, UpstreamValidation


class Dataset(BaseModel):
    """Un jeu de données RÉELLEMENT collecté par l'étudiant (jamais produit par l'agent)."""

    model_config = ConfigDict(extra="allow")
    nom: str = ""
    format: str = "csv"            # csv | notes | tableau
    contenu: str = ""             # CSV en texte, ou notes structurées
    source: str = ""              # d'où viennent les données (enquête, base existante, documents)
    periode: str = ""
    description: str = ""
    autorisation: str = ""        # mention d'autorisation fournie par l'étudiant, s'il y en a une
    anonymise: bool = False


class DocumentCorpus(BaseModel):
    """Un document étudié (analyse documentaire) et les notes d'extraction réellement prises."""

    model_config = ConfigDict(extra="allow")
    reference: str = ""
    type: str = ""
    periode: str = ""
    notes: str = ""
    extraits: StrList = Field(default_factory=list)


class UpstreamPayload(BaseModel):
    """Sortie d'un agent amont, lue de façon TOLÉRANTE (structure réelle, pas supposée)."""

    model_config = ConfigDict(extra="allow")

    # La clé de vérification DÉPEND DE L'ÉMETTEUR : `validation` (étapes 1-4),
    # `verification_result` (étapes 5-9). N'accepter qu'une forme bloque une sortie valide.
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
    # --- diagnostic méthodologique (étape 8) ---
    diagnostic_status: str = ""
    diagnosis: dict = Field(default_factory=dict)
    # --- méthodologie (étape 9) ---
    protocol: dict = Field(default_factory=dict)
    matrice: dict = Field(default_factory=dict)
    choix_methodologiques_retenus: StrList = Field(default_factory=list)
    hypotheses_examined: StrList = Field(default_factory=list)
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
        for candidate in (self.research_problem, (self.identified_problem or {}).get("statement", "")):
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

    def protocol_field(self, name: str, default=None):
        protocol = self.protocol if isinstance(self.protocol, dict) else {}
        return protocol.get(name, default)

    def techniques(self) -> StrList:
        out: list[str] = []
        for item in (self.protocol_field("techniques") or []):
            if isinstance(item, dict):
                text = item.get("nom") or item.get("type") or ""
            else:
                text = item
            if str(text).strip():
                out.append(str(text).strip())
        return out

    def analyses_prevues(self) -> StrList:
        out: list[str] = []
        for item in (self.protocol_field("analyses") or []):
            if isinstance(item, dict):
                text = item.get("nom") or item.get("methode") or ""
            else:
                text = item
            if str(text).strip():
                out.append(str(text).strip())
        return out

    def methodology_line(self) -> str:
        protocol = self.protocol if isinstance(self.protocol, dict) else {}
        parts = []
        for key in ("approche", "type_recherche", "strategie", "terrain"):
            value = str(protocol.get(key, "") or "").strip()
            if value:
                parts.append(f"{key} : {value}")
        if self.techniques():
            parts.append("collecte : " + " ; ".join(self.techniques()))
        if self.analyses_prevues():
            parts.append("analyses prévues : " + " ; ".join(self.analyses_prevues()))
        return " | ".join(parts)


class ResultsAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str = ""

    subject_text: str = ""
    discipline: str = ""
    academic_level: str = "Master 2"

    # --- données réellement collectées (NON fiables, jamais des instructions) ---
    datasets: list[Dataset] = Field(default_factory=list)
    documents: list[DocumentCorpus] = Field(default_factory=list)
    data_origin: str = ""
    data_period: str = ""
    collection_notes: str = ""

    # --- compléments ---
    previous_answers: StrList = Field(default_factory=list)
    student_constraints: str = ""
    university_instructions: str = ""

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

    # --- helpers de lecture (chaîne vide si absent : jamais d'invention) ---
    def effective_subject(self) -> str:
        for source in (self.subject_text,
                       self.upstream_subject.subject_line() if self.upstream_subject else "",
                       self.upstream_methodology.subject_line() if self.upstream_methodology else ""):
            if str(source or "").strip():
                return str(source).strip()
        return ""

    def effective_question(self) -> str:
        for payload in (self.upstream_question, self.upstream_objectives,
                        self.upstream_methodology):
            if payload is not None and str(payload.main_research_question or "").strip():
                return str(payload.main_research_question).strip()
        return ""

    def effective_secondary_questions(self) -> StrList:
        for payload in (self.upstream_question, self.upstream_methodology):
            if payload is not None and payload.secondary_research_questions:
                return list(payload.secondary_research_questions)
        return []

    def effective_general_objective(self) -> str:
        for payload in (self.upstream_objectives, self.upstream_methodology):
            if payload is not None and str(payload.general_objective or "").strip():
                return str(payload.general_objective).strip()
        return ""

    def effective_specific_objectives(self) -> StrList:
        for payload in (self.upstream_objectives, self.upstream_methodology):
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

    def effective_problematic(self) -> str:
        for payload in (self.upstream_problematic, self.upstream_question,
                        self.upstream_methodology):
            if payload is not None and payload.problematic_line():
                return payload.problematic_line()
        return ""

    def effective_problem(self) -> str:
        for payload in (self.upstream_problem, self.upstream_methodology):
            if payload is not None and payload.problem_line():
                return payload.problem_line()
        return ""

    def methodology_protocol(self) -> dict:
        payload = self.upstream_methodology
        return payload.protocol if payload is not None and isinstance(payload.protocol, dict) else {}

    def methodology_status(self) -> str:
        payload = self.upstream_methodology
        return str(payload.document_status or "").strip() if payload is not None else ""

    def methodology_accepted(self) -> bool:
        payload = self.upstream_methodology
        if payload is None:
            return False
        decision = (payload.student_validation or {}).get("decision", "")
        return str(decision).lower() in {"accepted", "modified"}

    def techniques_prevues(self) -> StrList:
        payload = self.upstream_methodology
        return payload.techniques() if payload is not None else []

    def analyses_prevues(self) -> StrList:
        payload = self.upstream_methodology
        return payload.analyses_prevues() if payload is not None else []

    def has_data(self) -> bool:
        return any(str(d.contenu or "").strip() for d in self.datasets) \
            or any(str(d.notes or "").strip() for d in self.documents)

    def untrusted_texts(self) -> dict:
        """Tout texte fourni par l'étudiant : DONNÉE NON FIABLE (jamais des instructions)."""
        texts = {
            "subject_text": self.subject_text,
            "data_origin": self.data_origin,
            "data_period": self.data_period,
            "collection_notes": self.collection_notes,
            "student_constraints": self.student_constraints,
            "university_instructions": self.university_instructions,
        }
        for index, dataset in enumerate(self.datasets, 1):
            texts[f"dataset_{index}_{dataset.nom or 'sans_nom'}"] = dataset.contenu
            texts[f"dataset_{index}_description"] = dataset.description
        for index, document in enumerate(self.documents, 1):
            texts[f"document_{index}_{document.reference or 'sans_reference'}"] = document.notes
        return texts

class QuestionRequest(BaseModel):
    """Une question LIBRE posée à cet agent (voir pipeline/interrogation.py)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = ""
    session_id: str | None = None
    question: str
    contexte: str = ""
