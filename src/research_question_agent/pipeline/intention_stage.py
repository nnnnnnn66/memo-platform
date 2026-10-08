"""Étape [6] — LLM P2 : identification de l'intention de recherche (SPEC §9.2)."""

from pathlib import Path

from ..analysis import intent as intent_module
from ..schemas.stages import IntentionOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_intention_system.md").read_text(encoding="utf-8")


def _checks(obj: IntentionOutput) -> list[str]:
    violations: list[str] = []
    intention = obj.research_intention
    if not intention.intention.strip():
        violations.append("research_intention.intention est vide")
    elif not intent_module.is_known(intention.intention):
        violations.append(
            "l'intention doit être l'une des valeurs canoniques : " + ", ".join(intent_module.INTENTS))
    if not intention.justification.strip():
        violations.append(
            "research_intention.justification est vide (l'intention doit découler de la problématique)")
    return violations


def run(llm, request, annotations, limits, extra: str = ""):
    system = load_system()
    user = security_layer.build_user_message(request, annotations)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, IntentionOutput, extra_checks=_checks, extra=extra)
    # Normalisation : on ne garde que la clé canonique.
    obj.research_intention.intention = intent_module.normalize_intent(obj.research_intention.intention)
    return obj.research_intention, attempts
