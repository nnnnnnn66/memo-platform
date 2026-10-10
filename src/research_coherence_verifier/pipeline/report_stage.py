"""Étage P2 — rédaction du rapport et DÉCLARATION DE PORTÉE (SPEC §9 étape 4).

Le programme établit le verdict, les constats et la portée statique/dynamique ; le modèle rédige la
synthèse, les recommandations rattachées et peut AJOUTER des éléments non vérifiables.
"""

from pathlib import Path

from ..schemas.stages import ReportOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_report_system.md").read_text(encoding="utf-8")


def _checks(obj: ReportOutput) -> list[str]:
    violations: list[str] = []
    if not str(obj.report.synthese or "").strip():
        violations.append("report.synthese est vide")
    for recommandation in obj.report.recommandations:
        if not str(recommandation.action or "").strip():
            violations.append("une recommandation sans action")
            break
    for item in obj.non_verifiable_supplementaire:
        if not str(item.element or "").strip() or not str(item.raison or "").strip():
            violations.append("un élément non vérifiable sans libellé ou sans raison")
            break
    return violations


def run(llm, request, annotations, dossier_state, faits, constats_llm, portee, extra: str = ""):
    system = load_system()
    lignes = ["<constats_consolides>", "CONSTATS DE L'AUDIT (à reprendre, sans en inventer) :"]
    for constat in list(faits) + list(constats_llm):
        lignes.append(f"- [{constat.code or 'LIBRE'}] ({constat.severite.value}, axe "
                      f"{constat.axe.value}) {constat.constat}")
        lignes.append(f"    preuve : {constat.preuve}")
    lignes.append("</constats_consolides>")
    lignes.append("<portee_deja_etablie>")
    lignes.append("ÉLÉMENTS DÉJÀ DÉCLARÉS NON VÉRIFIABLES (le programme) :")
    for item in portee:
        lignes.append(f"- {item.element} — {item.raison}")
    lignes.append("</portee_deja_etablie>")
    context = [
        security_layer.dossier_block(request),
        "\n".join(lignes),
        "Étapes absentes : " + (", ".join(dossier_state.etapes_absentes) or "aucune")
        + ". Le rapport DOIT dire ce qui n'a pas pu être vérifié.",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, ReportOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
