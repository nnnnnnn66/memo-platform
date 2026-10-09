"""Étape [1] — LLM P1 : analyse de la question et des objectifs (SPEC §9.1)."""

from pathlib import Path

from ..schemas.stages import AnalysisOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_analysis_system.md").read_text(encoding="utf-8")


def _checks(obj: AnalysisOutput) -> list[str]:
    violations: list[str] = []
    analysis = obj.analysis
    if not analysis.phenomene.strip():
        violations.append("analysis.phenomene est vide")
    if not analysis.action_attendue.strip():
        violations.append("analysis.action_attendue est vide (que cherche la recherche à faire ?)")
    if not analysis.nature_du_travail.strip():
        violations.append("analysis.nature_du_travail est vide (exploratoire/descriptif/explicatif…)")
    return violations


def run(llm, request, annotations, limits, extra: str = ""):
    system = load_system()
    user = security_layer.build_user_message(request, annotations)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, AnalysisOutput, extra_checks=_checks, extra=extra)
    return obj.analysis, attempts
