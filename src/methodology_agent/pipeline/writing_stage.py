"""Étage P4 — proposition de rédaction de la section « Méthodologie » (SPEC §9 étape 4)."""

from pathlib import Path

from ..schemas.stages import WritingOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p4_writing_system.md").read_text(encoding="utf-8")


def _checks(obj: WritingOutput) -> list[str]:
    violations: list[str] = []
    if not obj.draft.sections:
        violations.append("draft.sections est vide (au moins une sous-section attendue)")
    for section in obj.draft.sections:
        if not str(section.titre or "").strip():
            violations.append("une sous-section sans titre")
        if not str(section.contenu or "").strip():
            violations.append(f"sous-section « {section.titre} » sans contenu")
    return violations


def run(llm, request, annotations, protocol, matrix, extra: str = ""):
    system = load_system()
    context = [
        "Protocole établi (le document ne doit rien y ajouter) :\n"
        + protocol.model_dump_json(indent=2)[:14000],
        "Matrice de cohérence :\n" + matrix.model_dump_json(indent=2)[:6000],
        ("Consignes de l'établissement : AUCUNE fournie. Ne jamais présenter la structure proposée "
         "comme une règle officielle de l'université de l'étudiant.")
        if not (request.university_instructions or "").strip() else
        "Consignes de l'établissement fournies : s'y conformer sans les étendre.",
        ("Preuves fournies par l'étudiant (ce qui est DÉJÀ RÉALISÉ) : "
         + " ; ".join(request.realise_preuves)) if request.realise_preuves else
        "Aucune preuve de réalisation fournie : tout le document est PRÉVU (aucun passé).",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, WritingOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
