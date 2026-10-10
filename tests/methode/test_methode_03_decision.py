"""Portillon humain (SPEC §12) : l'agent ne s'attribue jamais « validé »."""

import pytest
from methode_helpers import StubLLM

from methodology_agent.core.errors import PipelineError
from methodology_agent.pipeline import campaign
from methodology_agent.schemas.decision import DecisionRequest, DecisionValue


def _campaign(settings, request_factory, **kw):
    return campaign.run(request_factory(), settings, StubLLM(**kw), allow_network=False)


def test_acceptation_pose_validated(settings, request_factory):
    result = _campaign(settings, request_factory)
    assert result.output.status.value == "awaiting_human_validation"
    # L'agent ne pose JAMAIS « validated » de lui-même.
    assert result.output.status.value != "validated"

    request = request_factory()
    decided = campaign.decide(request, settings, StubLLM(), result.output,
                              DecisionRequest(decision=DecisionValue.accepted,
                                              student_comment="protocole accepté"))
    assert decided.output.status.value == "validated"
    assert decided.output.document_status.value == "valide"
    assert decided.output.student_validation.decision == DecisionValue.accepted


def test_refus_bloque(settings, request_factory):
    result = _campaign(settings, request_factory)
    decided = campaign.decide(request_factory(), settings, StubLLM(), result.output,
                              DecisionRequest(decision=DecisionValue.refused,
                                              student_comment="pas d'accord sur l'échantillon"))
    assert decided.output.status.value == "blocked"
    assert decided.output.document_status.value == "a_reviser"
    assert decided.output.student_validation.decision == DecisionValue.refused


def test_modification_sans_changement_refusee(settings, request_factory):
    result = _campaign(settings, request_factory)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(request_factory(), settings, StubLLM(), result.output,
                        DecisionRequest(decision=DecisionValue.modified))
    assert exc.value.state.value == "INVALID_INPUT"


def test_modification_avec_information_fournie(settings, request_factory):
    """Fournir une information fait repasser le protocole par le vérificateur."""
    result = _campaign(settings, request_factory)
    decided = campaign.decide(
        request_factory(), settings, StubLLM(), result.output,
        DecisionRequest(decision=DecisionValue.modified,
                        provided_information="Effectif accessible : 48 développeurs."))
    assert decided.output.status.value in ("awaiting_human_validation", "verification_failed")
    assert decided.verifier_status in ("verified", "verification_failed")


def test_acceptation_exige_la_verification(settings, request_factory):
    """Un protocole dont la vérification a échoué ne peut pas être accepté."""
    result = _campaign(settings, request_factory, verdict="corrections_requested",
                       corrections=["C2 : la méthode ne répond pas à l'objectif 2"])
    assert result.output.verification_result.verified is False
    assert result.output.status.value == "verification_failed"
    with pytest.raises(PipelineError) as exc:
        campaign.decide(request_factory(), settings, StubLLM(), result.output,
                        DecisionRequest(decision=DecisionValue.accepted))
    assert exc.value.state.value == "INVALID_INPUT"


def test_acceptation_refusee_si_non_verifie(settings, request_factory):
    """Même en attente de validation, un protocole non vérifié ne peut pas être accepté."""
    from methodology_agent.pipeline import decision_stage
    result = _campaign(settings, request_factory)
    result.output.verification_result.verified = False
    with pytest.raises(PipelineError) as exc:
        decision_stage.apply(result.output,
                             DecisionRequest(decision=DecisionValue.accepted),
                             request_factory())
    assert exc.value.state.value == "MISSING_INFORMATION"


def test_statut_hors_portillon_refuse(settings, request_factory):
    result = _campaign(settings, request_factory)
    result.output.status = result.output.status.__class__.blocked
    with pytest.raises(PipelineError):
        campaign.decide(request_factory(), settings, StubLLM(), result.output,
                        DecisionRequest(decision=DecisionValue.accepted))
