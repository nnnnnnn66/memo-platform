"""Phase 4 : justification scientifique et note de problématisation rédigée (SPEC §9.4-9.5)."""

from pathlib import Path

from ..schemas.stages import JustificationOutput
from . import anchor_check, llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p4_justification_system.md").read_text(encoding="utf-8")


def run(llm, request, annotations: list[dict], index, confrontation, gap, limits,
        extra: str = "", max_attempts: int = 2):
    """Produit la justification et le premier jet rédigé. Retourne (JustificationOutput, attempts,
    removed)."""
    system = load_system()
    block = (
        "Éléments déjà établis et ancrés (à réutiliser, NE PAS réinventer) :\n"
        f"Gap retenu : {gap.type.value} — {gap.description}\n"
        "Affirmations sourcées disponibles :\n"
        + "\n".join(f"- [{s.doc_id}] {s.text} « {(s.quote or '')[:200]} »"
                    for s in (confrontation.modeles_dominants + confrontation.consensus
                              + confrontation.divergences + confrontation.statements
                              + gap.statements))
    )
    user = security_layer.build_user_message(request, annotations, [index.digest(), block])
    min_quote = int(getattr(limits, "min_quote_chars", 25))

    def checks(obj) -> list[str]:
        issues = []
        if not obj.justification.texte.strip():
            issues.append("justification.texte est vide")
        if not obj.justification.statements:
            issues.append("la justification doit porter au moins une affirmation sourcée")
        if not obj.problematique_note.texte_complet.strip():
            issues.append("problematique_note.texte_complet est vide")
        return issues

    obj, attempts = llm_stage.run_json_stage(llm, system, user, JustificationOutput,
                                             extra_checks=checks, max_attempts=max_attempts,
                                             extra=extra)
    removed = anchor_check.check_statements_and_report(obj, index, min_quote)
    return obj, attempts, removed
