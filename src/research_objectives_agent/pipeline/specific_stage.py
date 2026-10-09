"""Étape [3] — LLM P3 : objectifs spécifiques + alignement + faisabilité (SPEC §9.3, §9.4)."""

from pathlib import Path

from ..analysis import objective_rules
from ..schemas.stages import SpecificOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p3_specific_system.md").read_text(encoding="utf-8")


def _checks(obj: SpecificOutput) -> list[str]:
    violations: list[str] = []
    objectives = [str(o).strip() for o in obj.specific_objectives if str(o).strip()]
    if not objectives:
        violations.append("specific_objectives est vide (au moins un objectif spécifique)")
    for index, text in enumerate(objectives, start=1):
        if not objective_rules.has_action_verb(text):
            violations.append(f"objectif spécifique {index} : pas de verbe d'action en tête")
        forbidden = objective_rules.forbidden_verb_hits(text)
        if forbidden:
            violations.append(
                f"objectif spécifique {index} : présuppose un résultat ("
                + ", ".join(forbidden) + ")")
        if objective_rules.looks_like_hypothesis(text):
            violations.append(f"objectif spécifique {index} : ressemble à une hypothèse")
    if not (obj.objective_rationale or "").strip():
        violations.append("objective_rationale est vide (justifie la formulation des objectifs)")
    return violations


def run(llm, request, annotations, analysis, general_objective, limits, extra: str = ""):
    system = load_system()
    secondary = request.effective_secondary_questions()
    context = [
        f"Objectif général retenu : {general_objective}",
        ("Dimensions à couvrir : " + " ; ".join(analysis.dimensions)) if analysis.dimensions else "",
        ("Questions secondaires à couvrir le cas échéant : " + " ; ".join(secondary))
        if secondary else "",
    ]
    if analysis.dimensions and request.student_constraints:
        context.append("Contraintes connues (donnée) : " + request.student_constraints)
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, SpecificOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
