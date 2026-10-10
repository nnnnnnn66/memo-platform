"""Étage P3 — interprétation, présentation et limites (SPEC §9 étape 4)."""

from pathlib import Path

from ..schemas.stages import InterpretationOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p3_interpretation_system.md").read_text(encoding="utf-8")


def _checks(obj: InterpretationOutput) -> list[str]:
    violations: list[str] = []
    interpretation = obj.interpretation
    if not interpretation.lectures and not obj.interpretation.points_non_resolus:
        violations.append("interpretation.lectures est vide (aucune lecture proposée)")
    for lecture in interpretation.lectures:
        if not str(lecture.observation or "").strip():
            violations.append("une lecture sans observation (le fait constaté)")
            break
        if not str(lecture.interpretation or "").strip():
            violations.append("une lecture sans interprétation (ce que l'on en propose)")
            break
    return violations


def run(llm, request, annotations, computed, plan, extra: str = ""):
    system = load_system()
    context = [security_layer.methodology_block(request),
               ("<analyse_etablie>\nRésultats retenus et examen des hypothèses :\n"
                + plan.model_dump_json(indent=2)[:12000] + "\n</analyse_etablie>"),
               ("<valeurs_autorisees>\n"
                + " ; ".join(f"{r.id}={r.valeur}{r.unite}" for r in computed.resultats[:120])
                + "\n</valeurs_autorisees>"),
               ("Littérature disponible (étape 3) — ne citer que ce qui s'y trouve :\n"
                + str(request.upstream_literature.synthesis if request.upstream_literature
                      and not isinstance(request.upstream_literature.synthesis, str)
                      else (request.upstream_literature.synthesis
                            if request.upstream_literature else "non transmise"))[:6000]),
               ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, InterpretationOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
