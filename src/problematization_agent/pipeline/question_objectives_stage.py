"""Phase 5 : question de recherche candidate et objectifs candidats (SPEC §9.6-9.7).

PROPOSITION DE TRANSITION : ces sorties sont distinctes de la problématique et marquées `proposed`.
L'agent ne livre jamais la version validée des étapes 5 (question) et 6 (objectifs).
"""

from pathlib import Path

from ..schemas.question import QuestionStatus
from ..schemas.stages import QuestionObjectivesOutput
from . import llm_stage, security_layer

_PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"


def load_system() -> str:
    return (_PROMPT_DIR / "p5_question_objectives_system.md").read_text(encoding="utf-8")


def run(llm, request, annotations: list[dict], index, gap, note, limits,
        extra: str = "", max_attempts: int = 2):
    """Produit la question candidate et les objectifs candidats. Retourne (output, attempts, issues)."""
    system = load_system()
    block = (
        "Problématique rédigée (à traduire en question centrale) :\n"
        f"{note.texte_complet[:4000]}\n\nGap retenu : {gap.type.value} — {gap.description}"
    )
    user = security_layer.build_user_message(request, annotations, [block])

    def checks(obj) -> list[str]:
        issues = []
        question = obj.research_question.question.strip()
        if not question:
            issues.append("research_question.question est vide")
        if not question.endswith("?"):
            issues.append("la question de recherche doit être une question (terminée par « ? »)")
        if len(obj.objectives.specifics) < 2:
            issues.append("objectives.specifics doit contenir 2 à 3 objectifs spécifiques")
        if len(obj.objectives.specifics) > 3:
            issues.append("objectives.specifics ne doit pas dépasser 3 objectifs")
        if not obj.objectives.general.strip():
            issues.append("objectives.general est vide")
        return issues

    obj, attempts = llm_stage.run_json_stage(llm, system, user, QuestionObjectivesOutput,
                                             extra_checks=checks, max_attempts=max_attempts,
                                             extra=extra)
    # Le statut reste « proposed » par construction du schéma : aucune auto-validation d'étape.
    obj.research_question.status = QuestionStatus.proposed
    obj.objectives.status = QuestionStatus.proposed
    return obj, attempts
