"""Étage P3 — instruments de collecte et matrice de cohérence (SPEC §9 étape 3)."""

from pathlib import Path

from ..schemas.stages import InstrumentsOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p3_matrix_system.md").read_text(encoding="utf-8")


def _checks(obj: InstrumentsOutput) -> list[str]:
    violations: list[str] = []
    if not obj.instruments:
        violations.append("instruments est vide (instruments de collecte attendus)")
    for instrument in obj.instruments:
        if not str(instrument.type or "").strip():
            violations.append("un instrument sans type (questionnaire, guide d'entretien…)")
        if not str(instrument.objet or "").strip():
            violations.append(
                f"instrument « {instrument.type} » sans objet (à quoi il sert, pour quel objectif)")
    if not obj.matrice.lignes:
        violations.append("matrice.lignes est vide (une ligne par objectif est attendue)")
    return violations


def run(llm, request, annotations, protocol, extra: str = "", sources_bloc: str = ""):
    system = load_system()
    objectives = [request.effective_general_objective(), *request.effective_specific_objectives()]
    objectives = [o for o in objectives if str(o).strip()]
    context = [
        "Objectifs à couvrir, UN PAR LIGNE de la matrice (dans cet ordre) :\n"
        + "\n".join(f"- {o}" for o in objectives),
        "Protocole déjà établi (à ne pas contredire) :\n" + protocol.model_dump_json(indent=2)[:12000],
        ("Aucune hypothèse n'est pertinente pour ce travail (décision de l'étape 7) : ne pas en "
         "introduire dans les instruments.") if request.hypotheses_not_required() else "",
    ]
    if sources_bloc:
        context = list(context) + [sources_bloc]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, InstrumentsOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
