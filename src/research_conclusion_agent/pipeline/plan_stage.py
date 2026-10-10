"""Étage P2 — plan de conclusion (SPEC §9 étape 3)."""

from pathlib import Path

from ..schemas.stages import PlanOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_plan_system.md").read_text(encoding="utf-8")


def _checks(obj: PlanOutput) -> list[str]:
    violations: list[str] = []
    plan = obj.plan
    if not plan.sections:
        violations.append("plan.sections est vide (aucune rubrique proposée)")
    for section in plan.sections:
        if not str(section.titre or "").strip():
            violations.append("une rubrique du plan sans titre")
            break
        if not str(section.fonction or "").strip():
            violations.append(f"rubrique « {section.titre} » : la fonction de la rubrique n'est pas "
                              "indiquée")
            break
    return violations


def run(llm, request, annotations, synthesis, extra: str = ""):
    system = load_system()
    context = [
        "<synthese_etablie>\n" + synthesis.model_dump_json(indent=2)[:12000] + "\n</synthese_etablie>",
        security_layer.results_block(request),
        ("Consignes de l'établissement : AUCUNE fournie. Ne présentez pas la structure proposée comme "
         "une règle officielle de l'université de l'étudiant.")
        if not (request.university_instructions or "").strip() else
        "Consignes de l'établissement fournies : adaptez la structure, sans les étendre.",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, PlanOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
