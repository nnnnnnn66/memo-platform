"""Portillon humain de l'audit (SPEC §12) : l'étudiant arbitre, l'agent ne valide jamais seul."""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.output import AuditStatus, CoherenceOutput, DocumentStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output: CoherenceOutput, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_recontrole, violations)."""
    if output.status not in (AuditStatus.awaiting_human_validation,
                             AuditStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"l'audit n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "l'audit doit d'abord être contrôlé avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = AuditStatus.validated
        output.document_status = DocumentStatus.valide
        output.historique_versions.append(f"audit accepté par l'étudiant le {_now()}")
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = AuditStatus.blocked
        output.document_status = DocumentStatus.a_reviser
        output.historique_versions.append(f"audit refusé par l'étudiant le {_now()}")
        return output, False, []

    # modified — l'étudiant conteste un constat ou apporte des informations.
    modified = decision.modified or {}
    if not modified and not (decision.provided_information or "").strip():
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans changement fourni (`modified` ou `provided_information`)")

    contestes = [str(c).strip() for c in modified.get("constats_contestes", []) if str(c).strip()]
    if contestes:
        output.constats_retires_ou_reclasses.append(
            "constats contestés par l'étudiant (à réexaminer) : " + " ; ".join(contestes[:8]))
    acceptes = [str(c).strip() for c in modified.get("constats_acceptes", []) if str(c).strip()]
    if acceptes:
        output.corrections_effectuees.append(
            "constats acceptés par l'étudiant : " + " ; ".join(acceptes[:8]))
    if (decision.provided_information or "").strip():
        output.corrections_effectuees.append(
            "information fournie par l'étudiant : " + decision.provided_information.strip())
    output.historique_versions.append(f"audit révisé le {_now()}")

    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = AuditStatus.ready_for_verification
    output.document_status = DocumentStatus.a_corriger
    return output, True, []
