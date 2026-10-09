"""Étape [2-3] — LLM P2 : proposition du diagnostic méthodologique (SPEC §9.3)."""

from pathlib import Path

from ..schemas.stages import DiagnosisOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p2_diagnosis_system.md").read_text(encoding="utf-8")


def _checks(obj: DiagnosisOutput) -> list[str]:
    violations: list[str] = []
    diagnosis = obj.diagnosis
    for name, choice in (("approche", diagnosis.approche), ("logique", diagnosis.logique),
                         ("type_recherche", diagnosis.type_recherche),
                         ("strategie", diagnosis.strategie)):
        if not (choice.proposition or "").strip():
            violations.append(f"diagnosis.{name}.proposition est vide")
        if not (choice.justification or "").strip():
            violations.append(f"diagnosis.{name}.justification est vide (tout choix est justifié)")
    if not diagnosis.collecte:
        violations.append("diagnosis.collecte est vide (techniques de collecte attendues)")
    if not diagnosis.analyse:
        violations.append("diagnosis.analyse est vide (méthodes d'analyse attendues)")
    if not (obj.resume or "").strip():
        violations.append("resume est vide (résumé de la situation de recherche)")
    return violations


def run(llm, request, annotations, analysis, limits, extra: str = ""):
    system = load_system()
    context = [
        f"Visiée dégagée : {analysis.visee}" if analysis.visee else "",
        f"Nature du travail : {analysis.nature_du_travail}" if analysis.nature_du_travail else "",
        ("Hypothèses à examiner, le cas échéant : " + " ; ".join(request.effective_hypotheses()))
        if request.effective_hypotheses() else "",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, DiagnosisOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
