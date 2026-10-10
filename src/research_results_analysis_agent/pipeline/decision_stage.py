"""Portillon humain : décision de l'étudiant / de l'encadreur (SPEC §12)."""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.output import DocumentStatus, ResultsStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations)."""
    if output.status not in (ResultsStatus.awaiting_human_validation,
                             ResultsStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"la production n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "la production doit d'abord être validée par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = ResultsStatus.validated
        output.document_status = DocumentStatus.valide
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = ResultsStatus.blocked
        output.document_status = DocumentStatus.a_reviser
        return output, False, []

    # modified — l'étudiant corrige ou fournit des informations manquantes.
    modified = decision.modified or {}
    if not modified and not (decision.provided_information or "").strip():
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans changement fourni (champ `modified` ou "
            "`provided_information` requis)")

    if isinstance(modified.get("synthese_pour_conclusion"), list):
        valeurs = [str(v).strip() for v in modified["synthese_pour_conclusion"] if str(v).strip()]
        if valeurs:
            output.synthese_pour_conclusion = valeurs
            output.draft.synthese_pour_conclusion = valeurs
    if (decision.provided_information or "").strip():
        output.informations_a_confirmer.append(
            "informations complémentaires fournies par l'étudiant : "
            + decision.provided_information.strip())
    output.historique_corrections.append(
        f"modification étudiante le {_now()} : {decision.student_comment or 'sans commentaire'}")

    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = ResultsStatus.ready_for_verification
    output.document_status = DocumentStatus.a_verifier
    return output, True, []
