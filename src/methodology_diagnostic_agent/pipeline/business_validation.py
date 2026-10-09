"""Validation métier : statuts, statut du diagnostic, honnêteté (SPEC §10, §13)."""

from ..schemas.methodology import DiagnosticStatusEnum
from ..schemas.output import MethodologyOutput, MethodologyStatus


def validate_semantics(output: MethodologyOutput, request) -> list[str]:
    violations: list[str] = []

    # R1 — franchise du socle : le diagnostic s'appuie sur un sujet et une question fournis.
    if not request.effective_subject().strip():
        violations.append("R1: aucun sujet de référence")
    if not request.effective_question().strip():
        violations.append("R1: aucune question de recherche de référence")

    # R2 — cohérence du statut de diagnostic.
    if output.status in (MethodologyStatus.ready_for_verification,
                         MethodologyStatus.awaiting_human_validation, MethodologyStatus.validated):
        if not output.diagnosis.approche.proposition.strip():
            violations.append("R2: diagnostic sans approche proposée")
        if not output.diagnosis.analyse:
            violations.append("R2: diagnostic sans méthode d'analyse proposée")
    if output.status == MethodologyStatus.awaiting_human_validation \
            and not output.verification_result.verified:
        violations.append("R2: awaiting_human_validation sans vérification réussie")

    # R3 — le diagnostic provisoire est DÉCLARÉ comme tel.
    if output.missing_information and not output.provisional:
        violations.append("R3: informations manquantes mais diagnostic non marqué provisoire")
    if output.provisional and output.diagnostic_status == DiagnosticStatusEnum.valide:
        violations.append("R3: diagnostic provisoire ne peut pas être « valide »")

    # R4 — l'agent ne s'auto-vérifie jamais.
    if output.status == MethodologyStatus.ready_for_verification and output.verification_result.verified:
        violations.append("R4: verification_result.verified posé par l'agent (réservé au vérificateur)")
    if output.status == MethodologyStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append(
                "R4: statut 'validated' sans acceptation étudiante (réservé au portillon humain)")

    return violations


def validate_final(output: MethodologyOutput) -> list[str]:
    violations: list[str] = []
    if output.status == MethodologyStatus.needs_clarification and not output.clarification_questions:
        violations.append("R5: needs_clarification sans question posée à l'étudiant")
    if output.status == MethodologyStatus.validated:
        accepted = output.student_validation.decision is not None and \
            output.student_validation.decision.value == "accepted"
        if not accepted or not output.verification_result.verified:
            violations.append("R5: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == MethodologyStatus.blocked and not (
            output.student_validation.decision
            and output.student_validation.decision.value == "refused"):
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("R5: 'blocked' sans explication (unknowns/limites)")
    return violations
