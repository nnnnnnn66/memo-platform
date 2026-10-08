"""Étape [8] — LLM P3 : formulation de la question (SPEC §9.3, §9.4)."""

from pathlib import Path

from ..schemas.stages import FormulationOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p3_formulation_system.md").read_text(encoding="utf-8")


def _checks(obj: FormulationOutput) -> list[str]:
    violations: list[str] = []
    if not obj.main_research_question.strip():
        violations.append("main_research_question est vide")
    if not obj.formulation_rationale.strip():
        violations.append("formulation_rationale est vide (justifie la formulation)")
    return violations


def run(llm, request, annotations, comprehension, intention, limits, extra: str = "",
        student_question: str = ""):
    system = load_system()
    context = [
        f"Intention de recherche retenue : {intention.intention} — {intention.justification}",
        ("Objet central : " + comprehension.objet_central) if comprehension.objet_central else "",
        ("Ce qui reste à examiner : " + comprehension.reste_a_examiner)
        if comprehension.reste_a_examiner else "",
    ]
    if student_question:
        context.append(
            "La question proposée par l'étudiant (à prendre en compte, à neutraliser si besoin) : "
            + student_question)
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, FormulationOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
