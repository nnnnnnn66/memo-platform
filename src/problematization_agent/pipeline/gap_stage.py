"""Phase 3 : identification et classification du gap — la rupture (SPEC §9.3) + ancrage."""

from pathlib import Path

from ..schemas.gap import GapType
from ..schemas.stages import GapOutput
from . import anchor_check, llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"

_VALID_TYPES = {t.value for t in GapType}


def load_system() -> str:
    return (_PROMPT_DIR / "p3_gap_system.md").read_text(encoding="utf-8")


def run(llm, request, annotations: list[dict], index, confrontation, limits,
        extra: str = "", max_attempts: int = 2):
    """Produit le gap, retire les citations non ancrées. Retourne (Gap, attempts, removed)."""
    system = load_system()
    known = index.doc_ids
    confrontation_block = "État des savoirs établi (déjà ancré) :\n" + "\n".join(
        f"- [{s.doc_id}] {s.text} « {(s.quote or '')[:160]} »"
        for s in (confrontation.modeles_dominants + confrontation.consensus
                  + confrontation.divergences + confrontation.statements)
    )
    user = security_layer.build_user_message(request, annotations,
                                             [index.digest(), confrontation_block or ""])
    min_quote = int(getattr(limits, "min_quote_chars", 25))

    def checks(obj) -> list[str]:
        gap = obj.gap
        issues = []
        if gap.type.value not in _VALID_TYPES:
            issues.append(f"type de gap invalide : {gap.type}")
        if not gap.description.strip():
            issues.append("gap.description est vide")
        if not gap.statements:
            issues.append("le gap doit être justifié par au moins une affirmation sourcée")
        for statement in gap.statements:
            if statement.doc_id and statement.doc_id not in known:
                issues.append(f"doc_id inconnu dans le gap : {statement.doc_id}")
        return issues

    obj, attempts = llm_stage.run_json_stage(llm, system, user, GapOutput,
                                             extra_checks=checks, max_attempts=max_attempts,
                                             extra=extra)
    removed = anchor_check.check_statement_list(obj.gap, ("statements",), index, min_chars=min_quote)
    return obj.gap, attempts, removed
