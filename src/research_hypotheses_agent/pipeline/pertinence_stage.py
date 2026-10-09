"""Étape [2] — LLM P2 : décision de pertinence des hypothèses (SPEC §9.2).

L'agent choisit entre HYPOTHESES_RECOMMENDED, HYPOTHESES_NOT_REQUIRED et
HYPOTHESES_REQUIRE_CLARIFICATION, avec une justification. Il ne force jamais des hypothèses.
"""

from pathlib import Path

from ..schemas.hypotheses import DecisionCode
from ..schemas.stages import DecisionOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_decision_system.md").read_text(encoding="utf-8")


def _checks(obj: DecisionOutput) -> list[str]:
    violations: list[str] = []
    if not isinstance(obj.hypotheses_decision, DecisionCode):
        violations.append("hypotheses_decision hors enum (HYPOTHESES_RECOMMENDED / "
                          "HYPOTHESES_NOT_REQUIRED / HYPOTHESES_REQUIRE_CLARIFICATION)")
    if not (obj.decision_rationale or "").strip():
        violations.append("decision_rationale est vide (la décision doit être justifiée)")
    if obj.hypotheses_decision == DecisionCode.require_clarification \
            and not [q for q in obj.clarification_questions if str(q).strip()]:
        violations.append(
            "décision 'HYPOTHESES_REQUIRE_CLARIFICATION' sans question de clarification : précise "
            "ce qui manque à l'étudiant (liste `clarification_questions`)")
    return violations


def run(llm, request, annotations, analysis, limits, extra: str = ""):
    system = load_system()
    context = [
        f"Nature du travail dégagée : {analysis.nature_du_travail}"
        if analysis.nature_du_travail else "",
        f"Action attendue : {analysis.action_attendue}" if analysis.action_attendue else "",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, DecisionOutput, extra_checks=_checks, extra=extra)
    questions = [str(q).strip() for q in obj.clarification_questions if str(q).strip()]
    return obj.hypotheses_decision, obj.decision_rationale.strip(), questions, attempts
