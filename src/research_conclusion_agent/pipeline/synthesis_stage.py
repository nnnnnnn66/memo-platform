"""Étage P1 — examen du dossier et synthèse scientifique (SPEC §9 étapes 1-2)."""

from pathlib import Path

from ..schemas.stages import SynthesisOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_synthesis_system.md").read_text(encoding="utf-8")


def _checks(obj: SynthesisOutput) -> list[str]:
    violations: list[str] = []
    synthesis = obj.synthesis
    if not synthesis.elements_disponibles and not synthesis.elements_manquants:
        violations.append("synthesis.elements_disponibles est vide (sur quoi la conclusion s'appuie ?)")
    if not synthesis.plan_seulement and not str(synthesis.reponse_question.reponse or "").strip():
        violations.append("synthesis.reponse_question.reponse est vide (la conclusion doit répondre à "
                          "la question de recherche)")
    if not synthesis.plan_seulement and not synthesis.resultats_essentiels:
        violations.append("synthesis.resultats_essentiels est vide (quels résultats sont retenus ?)")
    return violations


def run(llm, request, annotations, extra: str = ""):
    system = load_system()
    context = [security_layer.results_block(request),
               security_layer.methodology_block(request),
               ("Aucune hypothèse n'est pertinente pour ce travail (décision de l'étape 7) : n'en "
                "introduisez pas.") if request.hypotheses_not_required() else ""]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, SynthesisOutput, extra_checks=_checks, extra=extra)
    return obj.synthesis, attempts
