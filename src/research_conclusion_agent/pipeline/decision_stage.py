"""Portillon humain : décision de l'étudiant / de l'encadreur (SPEC §12)."""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.output import ConclusionStatus, DocumentStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations)."""
    if output.status not in (ConclusionStatus.awaiting_human_validation,
                             ConclusionStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"la conclusion n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "la conclusion doit d'abord être validée par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = ConclusionStatus.validated
        output.document_status = DocumentStatus.valide
        output.historique_versions.append(f"version acceptée par l'étudiant le {_now()}")
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = ConclusionStatus.blocked
        output.document_status = DocumentStatus.a_reviser
        output.historique_versions.append(f"version refusée par l'étudiant le {_now()}")
        return output, False, []

    # modified — l'étudiant corrige ou fournit des informations.
    modified = decision.modified or {}
    if not modified and not (decision.provided_information or "").strip():
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans changement fourni (champ `modified` ou "
            "`provided_information` requis)")

    if isinstance(modified.get("points_a_confirmer"), list):
        valeurs = [str(v).strip() for v in modified["points_a_confirmer"] if str(v).strip()]
        if valeurs:
            output.draft.points_a_confirmer = valeurs
    if isinstance(modified.get("limites"), list):
        valeurs = [str(v).strip() for v in modified["limites"] if str(v).strip()]
        if valeurs:
            output.draft.limites = valeurs
    if (decision.provided_information or "").strip():
        output.informations_a_confirmer.append(
            "informations complémentaires fournies par l'étudiant : "
            + decision.provided_information.strip())
    output.corrections_effectuees.append(
        f"modification étudiante le {_now()} : {decision.student_comment or 'sans commentaire'}")
    output.historique_versions.append(f"version révisée le {_now()}")

    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = ConclusionStatus.ready_for_verification
    output.document_status = DocumentStatus.a_corriger
    return output, True, []
