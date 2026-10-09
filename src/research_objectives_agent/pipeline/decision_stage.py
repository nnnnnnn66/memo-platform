"""Étapes [5] — portillon humain : décision de l'étudiant (SPEC §12, §13).

L'agent ne peut JAMAIS s'attribuer `validated` : seule une décision explicite de l'étudiant, après
vérification, produit ce statut.
"""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.output import ObjectiveStatus
from . import objectives_checks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations)."""
    if output.status not in (ObjectiveStatus.awaiting_human_validation,
                             ObjectiveStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"la sortie n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "les objectifs doivent d'abord être validés par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = ObjectiveStatus.validated
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = ObjectiveStatus.blocked
        return output, False, []

    # modified — l'étudiant propose un objectif général et/ou des objectifs spécifiques.
    general = (decision.modified_general_objective or "").strip()
    specifics = [str(o).strip() for o in (decision.modified_specific_objectives or []) if str(o).strip()]
    if not general and not specifics:
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans objectif modifié (champs modified_general_objective / "
            "modified_specific_objectives requis)")

    if general:
        output.general_objective = general
    if specifics:
        output.specific_objectives = specifics
    violations = objectives_checks.apply(output, request)
    if violations:
        # Les objectifs de l'étudiant passent les mêmes contrôles de neutralité : on ne valide pas en
        # silence une formulation à présupposé.
        return output, True, violations
    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = ObjectiveStatus.ready_for_verification
    return output, True, []
