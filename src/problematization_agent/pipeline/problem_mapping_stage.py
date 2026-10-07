"""Phase 1 : cartographie du problème réel — le constat (SPEC §9.1)."""

from pathlib import Path

from ..schemas.stages import ProblemMappingOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p1_problem_mapping_system.md").read_text(encoding="utf-8")


def run(llm, request, annotations: list[dict], index, limits, extra: str = "", max_attempts: int = 2):
    """Produit et valide la cartographie du problème. Retourne (ProblemMapping, attempts)."""
    system = load_system()
    user = security_layer.build_user_message(request, annotations, [index.digest()])

    def checks(obj) -> list[str]:
        mapping = obj.problem_mapping
        issues = []
        if not mapping.phenomene.strip():
            issues.append("problem_mapping.phenomene est vide")
        if not mapping.dysfonctionnement.strip():
            issues.append("problem_mapping.dysfonctionnement est vide")
        return issues

    obj, attempts = llm_stage.run_json_stage(llm, system, user, ProblemMappingOutput,
                                             extra_checks=checks, max_attempts=max_attempts,
                                             extra=extra)
    return obj.problem_mapping, attempts
