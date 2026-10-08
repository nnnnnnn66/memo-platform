"""Étape [5] — LLM P1 : compréhension de la problématique (SPEC §9.1)."""

from pathlib import Path

from ..schemas.stages import ComprehensionOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_comprehension_system.md").read_text(encoding="utf-8")


def _checks(obj: ComprehensionOutput) -> list[str]:
    violations: list[str] = []
    comprehension = obj.comprehension
    if not comprehension.objet_central.strip():
        violations.append("comprehension.objet_central est vide")
    if not comprehension.phenomene.strip():
        violations.append("comprehension.phenomene est vide")
    if comprehension.provenance.value == "unknown" and not comprehension.reste_a_examiner.strip():
        violations.append(
            "provenance=unknown mais reste_a_examiner est vide : précise ce qui reste à établir")
    return violations


def run(llm, request, annotations, limits, extra: str = ""):
    system = load_system()
    user = security_layer.build_user_message(request, annotations)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, ComprehensionOutput, extra_checks=_checks, extra=extra)
    return obj.comprehension, attempts
