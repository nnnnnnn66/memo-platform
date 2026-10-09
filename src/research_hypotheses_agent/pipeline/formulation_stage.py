"""Étape [3] — LLM P3 : formulation des hypothèses (SPEC §9.3), si elles sont pertinentes."""

from pathlib import Path

from ..analysis import hypothesis_rules
from ..schemas.stages import FormulationOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p3_formulation_system.md").read_text(encoding="utf-8")


def _checks(obj: FormulationOutput) -> list[str]:
    violations: list[str] = []
    hypotheses = obj.research_hypotheses
    if not hypotheses:
        violations.append("research_hypotheses est vide alors que des hypothèses sont recommandées")
    for index, h in enumerate(hypotheses, start=1):
        text = (h.formulation or "").strip()
        if not text:
            violations.append(f"hypothèse {index} : formulation vide")
            continue
        if hypothesis_rules.looks_like_question(text):
            violations.append(f"hypothèse {index} : c'est une question, pas une proposition")
        if hypothesis_rules.looks_like_objective(text):
            violations.append(f"hypothèse {index} : c'est un objectif (verbe d'action), pas une hypothèse")
        if not (h.justification or "").strip():
            violations.append(f"hypothèse {index} : justification vide (elle doit être traçable)")
    if not (obj.hypothesis_objective_alignment.general_to_objectives or "").strip():
        violations.append("hypothesis_objective_alignment.general_to_objectives est vide")
    return violations


def run(llm, request, annotations, analysis, limits, extra: str = ""):
    system = load_system()
    context = [
        f"Nature du travail : {analysis.nature_du_travail}" if analysis.nature_du_travail else "",
        ("Objectifs spécifiques à couvrir : "
         + " ; ".join(request.effective_specific_objectives()))
        if request.effective_specific_objectives() else "",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, FormulationOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
