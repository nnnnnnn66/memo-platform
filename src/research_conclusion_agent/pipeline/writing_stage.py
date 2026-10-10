"""Étage P3 — rédation du brouillon de conclusion et des justifications (SPEC §9 étape 4)."""

from pathlib import Path

from ..schemas.stages import WritingOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p3_writing_system.md").read_text(encoding="utf-8")


def _checks(obj: WritingOutput) -> list[str]:
    violations: list[str] = []
    draft = obj.draft
    if not draft.sections and not draft.points_a_confirmer:
        violations.append("draft.sections est vide (aucune section rédigée ni point à confirmer)")
    for section in draft.sections:
        if not str(section.titre or "").strip():
            violations.append("une section sans titre")
            break
        if not str(section.contenu or "").strip():
            violations.append(f"section « {section.titre} » sans contenu")
            break
        if not str(section.justification or "").strip():
            violations.append(f"section « {section.titre} » : la justification de l'affirmation "
                              "n'est pas indiquée")
            break
    return violations


def run(llm, request, annotations, synthesis, plan, extra: str = ""):
    system = load_system()
    context = [
        "<synthese_etablie>\n" + synthesis.model_dump_json(indent=2)[:10000] + "\n</synthese_etablie>",
        "<plan_etabli>\n" + plan.model_dump_json(indent=2)[:6000] + "\n</plan_etabli>",
        security_layer.results_block(request),
        "Distinguez explicitement le CONSTAT (ce que les données montrent), l'INTERPRÉTATION et la "
        "PERSPECTIVE. Aucun résultat nouveau : uniquement ceux de l'étape 10, cités par leur "
        "identifiant.",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, WritingOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
