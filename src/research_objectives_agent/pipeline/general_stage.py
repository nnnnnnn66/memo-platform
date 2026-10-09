"""Étape [2] — LLM P2 : objectif général (SPEC §9.2)."""

from pathlib import Path

from ..analysis import objective_rules
from ..schemas.stages import GeneralOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_general_system.md").read_text(encoding="utf-8")


def _checks(obj: GeneralOutput) -> list[str]:
    violations: list[str] = []
    text = (obj.general_objective or "").strip()
    if not text:
        return ["general_objective est vide"]
    if not objective_rules.has_action_verb(text):
        violations.append(
            "l'objectif général doit s'ouvrir par un verbe d'action adapté (identifier, décrire, "
            "analyser, comparer, examiner, mesurer, comprendre, explorer, déterminer, évaluer, "
            "expliquer, interpréter…)")
    forbidden = objective_rules.forbidden_verb_hits(text)
    if forbidden:
        violations.append(
            "l'objectif présuppose un résultat (verbe interdit : " + ", ".join(forbidden)
            + ") : reformule-le de façon neutre")
    if objective_rules.looks_like_hypothesis(text):
        violations.append("l'objectif ressemble à une hypothèse : un objectif n'annonce aucun résultat")
    if objective_rules.is_too_short(text):
        violations.append("l'objectif général est trop court pour être précis")
    return violations


def run(llm, request, annotations, analysis, limits, extra: str = ""):
    system = load_system()
    context = [
        f"Action intellectuelle attendue : {analysis.action_attendue}"
        if analysis.action_attendue else "",
        ("Dimensions à examiner : " + " ; ".join(analysis.dimensions)) if analysis.dimensions else "",
        ("Ce qui reste à examiner : " + analysis.perimetre) if analysis.perimetre else "",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, GeneralOutput, extra_checks=_checks, extra=extra)
    return obj.general_objective.strip(), attempts
