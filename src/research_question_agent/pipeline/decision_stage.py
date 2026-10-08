"""Étapes [13-14] — portillon humain : décision de l'étudiant (SPEC §12, §13).

L'agent ne peut JAMAIS s'attribuer `validated` : seule une décision explicite de l'étudiant, après
vérification, produit ce statut.
"""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.output import QuestionStatus
from . import formulation_checks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output, decision, request, problematic_text: str) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations_neutralite)."""
    if output.status not in (QuestionStatus.awaiting_human_validation,
                             QuestionStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"la sortie n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "la question doit d'abord être validée par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = QuestionStatus.validated
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = QuestionStatus.blocked
        return output, False, []

    # modified
    question = (decision.modified_question or "").strip()
    if not question:
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans question modifiée (champ modified_question requis)")
    context_text = " ".join(filter(None, [request.all_provided_text(), problematic_text or ""]))
    violations = formulation_checks.check_question_text(question, context_text)
    if violations:
        # La question de l'étudiant passe les mêmes contrôles de neutralité : on ne valide pas en
        # silence une formulation à présupposé.
        return output, True, violations
    output.main_research_question = question
    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = QuestionStatus.ready_for_verification
    return output, True, []
