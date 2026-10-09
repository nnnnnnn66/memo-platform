"""Validation métier : décision cohérente, statuts, honnêteté (SPEC §10, §13).

Contrôles déterministes sur la production assemblée, AVANT le vérificateur.
"""

from ..schemas.hypotheses import DecisionCode
from ..schemas.output import HypothesisStatus, HypothesesOutput


def validate_semantics(output: HypothesesOutput, request) -> list[str]:
    violations: list[str] = []

    # R1 — franchise du socle : les hypothèses découlent d'une question ET d'objectifs fournis.
    if not request.effective_question().strip():
        violations.append("R1: aucune question de recherche de référence")
    if not request.effective_general_objective().strip() and not request.effective_specific_objectives():
        violations.append("R1: aucun objectif de recherche de référence (le socle des hypothèses)")

    # R2 — cohérence décision ↔ contenu.
    hypotheses = [h for h in output.research_hypotheses if (h.formulation or "").strip()]
    if output.hypotheses_decision == DecisionCode.recommended and not hypotheses:
        violations.append("R2: 'HYPOTHESES_RECOMMENDED' sans aucune hypothèse formulée")
    if output.hypotheses_decision == DecisionCode.not_required and hypotheses:
        violations.append("R2: 'HYPOTHESES_NOT_REQUIRED' alors que des hypothèses sont présentes")
    if not (output.decision_rationale or "").strip() and output.status in (
            HypothesisStatus.awaiting_human_validation, HypothesisStatus.validated):
        violations.append("R2: décision sans justification (decision_rationale vide)")

    # R3 — complétude selon le statut.
    if output.status in (HypothesisStatus.ready_for_verification,
                         HypothesisStatus.awaiting_human_validation, HypothesisStatus.validated):
        if not (output.decision_rationale or "").strip():
            violations.append("R3: statut de proposition sans justification de la décision")
    if output.status == HypothesisStatus.awaiting_human_validation \
            and not output.verification_result.verified:
        violations.append("R3: awaiting_human_validation sans vérification réussie")

    # R4 — l'agent ne s'auto-vérifie jamais.
    if output.status == HypothesisStatus.ready_for_verification and output.verification_result.verified:
        violations.append("R4: verification_result.verified posé par l'agent (réservé au vérificateur)")
    if output.status == HypothesisStatus.validated:
        accepted = (output.student_validation.decision is not None
                    and output.student_validation.decision.value == "accepted")
        if not accepted:
            violations.append(
                "R4: statut 'validated' sans acceptation étudiante (réservé au portillon humain)")

    return violations


def validate_final(output: HypothesesOutput) -> list[str]:
    violations: list[str] = []
    if output.status == HypothesisStatus.needs_clarification and not output.clarification_questions:
        violations.append("R5: needs_clarification sans question posée à l'étudiant")
    if output.status == HypothesisStatus.validated:
        accepted = output.student_validation.decision is not None and \
            output.student_validation.decision.value == "accepted"
        if not accepted or not output.verification_result.verified:
            violations.append("R5: 'validated' sans acceptation étudiante ET vérification réussie")
    if output.status == HypothesisStatus.blocked and not (
            output.student_validation.decision
            and output.student_validation.decision.value == "refused"):
        if not (output.unknowns or output.limits_of_this_output):
            violations.append("R5: 'blocked' sans explication (unknowns/limites)")
    return violations
