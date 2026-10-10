"""Étage P4 — rédaction de la section « Résultats et analyse » et synthèse pour l'étape 11."""

from pathlib import Path

from ..schemas.stages import WritingOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p4_writing_system.md").read_text(encoding="utf-8")


def _checks(obj: WritingOutput) -> list[str]:
    violations: list[str] = []
    draft = obj.draft
    if not draft.sections and not draft.elements_a_confirmer:
        violations.append("draft.sections est vide (aucune section rédigée ni élément à confirmer)")
    for section in draft.sections:
        if not str(section.titre or "").strip():
            violations.append("une section sans titre")
            break
        if not str(section.contenu or "").strip():
            violations.append(f"section « {section.titre} » sans contenu")
            break
    return violations


def run(llm, request, annotations, computed, plan, interpretation, extra: str = ""):
    system = load_system()
    context = [
        ("<resultats_calcules>\n"
         + "\n".join(f"- {r.id} : {r.libelle} = {r.valeur}{r.unite} (effectif {r.effectif})"
                     for r in computed.resultats[:150])
         + "\n</resultats_calcules>"),
        ("<analyse_etablie>\n" + plan.model_dump_json(indent=2)[:10000] + "\n</analyse_etablie>"),
        ("<interpretation_etablie>\n" + interpretation.model_dump_json(indent=2)[:12000]
         + "\n</interpretation_etablie>"),
        "Aucune conclusion générale : elle relève de l'étape 11. Rédige uniquement les résultats et "
        "leur analyse, et prépare une synthèse exploitable pour la conclusion.",
    ]
    user = security_layer.build_user_message(request, annotations, extra_blocks=context)
    obj, attempts = llm_stage.run_json_stage(
        llm, system, user, WritingOutput, extra_checks=_checks, extra=extra)
    return obj, attempts
