"""Étapes [5] — portillon humain : décision de l'étudiant (SPEC §12, §13).

L'agent ne peut JAMAIS s'attribuer `validated` : seule une décision explicite de l'étudiant, après
vérification, produit ce statut. L'étudiant peut aussi modifier la décision de pertinence et/ou les
formulations d'hypothèses.
"""

from datetime import datetime, timezone

from ..core.errors import ErrorState, PipelineError
from ..schemas.decision import DecisionValue, StudentValidation
from ..schemas.hypotheses import DecisionCode, Hypothesis
from ..schemas.output import HypothesisStatus
from . import hypotheses_checks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_decision(value: str) -> DecisionCode | None:
    for code in DecisionCode:
        if code.value == str(value).strip().upper():
            return code
    return None


def apply(output, decision, request) -> tuple:
    """Applique la décision. Retourne (output, needs_revision, violations)."""
    if output.status not in (HypothesisStatus.awaiting_human_validation,
                             HypothesisStatus.ready_for_verification):
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            f"la sortie n'est pas en attente de validation (statut={output.status.value})")

    value = decision.decision

    if value == DecisionValue.accepted:
        if not output.verification_result.verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                "les hypothèses (ou la décision de ne pas en formuler) doivent d'abord être validées "
                "par le vérificateur avant acceptation")
        output.student_validation = StudentValidation(
            decision=DecisionValue.accepted, comment=decision.student_comment, at=_now())
        output.status = HypothesisStatus.validated
        return output, False, []

    if value == DecisionValue.refused:
        output.student_validation = StudentValidation(
            decision=DecisionValue.refused, comment=decision.student_comment, at=_now())
        output.status = HypothesisStatus.blocked
        return output, False, []

    # modified — l'étudiant peut changer la décision de pertinence et/ou les hypothèses.
    new_code = _coerce_decision(decision.modified_decision) if decision.modified_decision else None
    new_formulations = [str(h).strip() for h in (decision.modified_hypotheses or []) if str(h).strip()]
    if new_code is None and not new_formulations:
        raise PipelineError(
            ErrorState.INVALID_INPUT,
            "décision « modified » sans changement fourni (modified_decision / modified_hypotheses)")

    if new_code is not None:
        output.hypotheses_decision = new_code
        # Basculer vers « pas d'hypothèses » vide les hypothèses : sinon la décision et le contenu se
        # contrediraient (contrôle H1). Basculer vers « recommandées » exige des hypothèses fournies.
        if new_code == DecisionCode.not_required:
            output.research_hypotheses = []
    if new_formulations:
        existing = {h.formulation: h for h in output.research_hypotheses}
        output.research_hypotheses = [
            existing.get(text, Hypothesis(id=f"H{i}", formulation=text,
                                          justification="Hypothèse proposée par l'étudiant."))
            for i, text in enumerate(new_formulations, start=1)
        ]
    violations = hypotheses_checks.apply(output, request)
    if violations:
        # Les hypothèses de l'étudiant passent les mêmes contrôles : on ne valide pas en silence une
        # question déguisée, une causalité non établie ou un fait présupposé.
        return output, True, violations
    output.student_validation = StudentValidation(
        decision=DecisionValue.modified, comment=decision.student_comment, at=_now())
    output.status = HypothesisStatus.ready_for_verification
    return output, True, []
