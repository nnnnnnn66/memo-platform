"""Étape [5] — portillon humain : décision de l'étudiant / de l'encadreur (SPEC §11, §12).

L'agent ne peut JAMAIS s'attribuer `validated` : seule une décision explicite, après vérification,
produit ce statut. L'étudiant peut accepter, choisir une alternative ou fournir des informations.
"""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.methodology import DiagnosticStatusEnum
from ..schemas.output import MethodologyStatus
from . import diagnosis_checks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply(output, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations)."""
    if output.status not in (MethodologyStatus.awaiting_human_validation,
                             MethodologyStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"le diagnostic n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "le diagnostic doit d'abord être validé par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = MethodologyStatus.validated
        output.diagnostic_status = DiagnosticStatusEnum.valide
        output.provisional = False
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = MethodologyStatus.blocked
        output.diagnostic_status = DiagnosticStatusEnum.a_reviser
        return output, False, []

    # modified — l'étudiant choisit des alternatives et/ou fournit des informations.
    modified = decision.modified or {}
    if not modified and not (decision.provided_information or "").strip():
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans changement fourni (champ `modified` ou "
            "`provided_information` requis)")

    diag = output.diagnosis
    for key, target in (("approche", diag.approche), ("logique", diag.logique),
                        ("type_recherche", diag.type_recherche), ("strategie", diag.strategie)):
        if isinstance(modified.get(key), str) and modified[key].strip():
            target.proposition = modified[key].strip()
    for key in ("collecte", "analyse"):
        values = modified.get(key)
        if isinstance(values, list) and values:
            from ..schemas.methodology import CategoryCode
            setattr(diag, key, [CategoryCode(proposition=str(v).strip()) for v in values
                                if str(v).strip()])
    if (decision.provided_information or "").strip():
        output.limits_of_this_output.append(
            "informations complémentaires fournies par l'étudiant : "
            + decision.provided_information.strip())

    violations = diagnosis_checks.apply(output, request)
    if violations:
        return output, True, violations
    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = MethodologyStatus.ready_for_verification
    output.diagnostic_status = DiagnosticStatusEnum.en_attente_de_validation
    return output, True, []
