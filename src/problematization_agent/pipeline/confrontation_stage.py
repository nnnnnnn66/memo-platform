"""Phase 2 : confrontation littéraire — l'état des savoirs (SPEC §9.2) + ancrage."""

from pathlib import Path

from ..schemas.stages import ConfrontationOutput
from . import anchor_check, llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"

_STATEMENT_FIELDS = ("modeles_dominants", "consensus", "divergences", "statements")


def load_system() -> str:
    return (_PROMPT_DIR / "p2_confrontation_system.md").read_text(encoding="utf-8")


def run(llm, request, annotations: list[dict], index, limits, extra: str = "", max_attempts: int = 2):
    """Produit la confrontation littéraire, puis RETIRE toute citation non ancrée.

    Retourne (LiteratureConfrontation, attempts, removed).
    """
    system = load_system()
    user = security_layer.build_user_message(request, annotations, [index.digest()])
    min_quote = int(getattr(limits, "min_quote_chars", 25))

    def checks(obj) -> list[str]:
        confrontation = obj.literature_confrontation
        issues = []
        if not (confrontation.modeles_dominants or confrontation.consensus
                or confrontation.statements):
            issues.append("aucune affirmation dans l'état des savoirs")
        return issues

    obj, attempts = llm_stage.run_json_stage(llm, system, user, ConfrontationOutput,
                                             extra_checks=checks, max_attempts=max_attempts,
                                             extra=extra)
    removed = anchor_check.check_statement_list(obj.literature_confrontation, _STATEMENT_FIELDS,
                                                index, min_chars=min_quote)
    return obj.literature_confrontation, attempts, removed
