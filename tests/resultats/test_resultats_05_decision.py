"""Portillon humain (SPEC §12) : l'agent ne s'attribue jamais « validé »."""

import pytest
from resultats_helpers import StubLLM

from research_results_analysis_agent.core.errors import PipelineError
from research_results_analysis_agent.pipeline import campaign, decision_stage
from research_results_analysis_agent.schemas.decision import DecisionRequest, DecisionValue


def _campagne(settings, request_factory, **kw):
    return campaign.run(request_factory(), settings, StubLLM(**kw), allow_network=False)


def test_acceptation_pose_validated(settings, request_factory):
    result = _campagne(settings, request_factory)
    assert result.output.status.value == "awaiting_human_validation"
    decided = campaign.decide(request_factory(), settings, StubLLM(), result.output,
                              DecisionRequest(decision=DecisionValue.accepted,
                                              student_comment="résultats acceptés"))
    assert decided.output.status.value == "validated"
    assert decided.output.document_status.value == "valide"


def test_refus_bloque(settings, request_factory):
    result = _campagne(settings, request_factory)
    decided = campaign.decide(request_factory(), settings, StubLLM(), result.output,
                              DecisionRequest(decision=DecisionValue.refused,
                                              student_comment="données mal recueillies"))
    assert decided.output.status.value == "blocked"
    assert decided.output.document_status.value == "a_reviser"


def test_acceptation_exige_la_verification(settings, request_factory):
    result = _campagne(settings, request_factory)
    result.output.verification_result.verified = False
    with pytest.raises(PipelineError) as exc:
        decision_stage.apply(result.output, DecisionRequest(decision=DecisionValue.accepted),
                             request_factory())
    assert exc.value.state.value == "MISSING_INFORMATION"


def test_modification_sans_changement_refusee(settings, request_factory):
    result = _campagne(settings, request_factory)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(request_factory(), settings, StubLLM(), result.output,
                        DecisionRequest(decision=DecisionValue.modified))
    assert exc.value.state.value == "INVALID_INPUT"


def test_modification_avec_information_fournie(settings, request_factory):
    result = _campagne(settings, request_factory)
    decided = campaign.decide(
        request_factory(), settings, StubLLM(), result.output,
        DecisionRequest(decision=DecisionValue.modified,
                        provided_information="Effectif réel de la population accessible : 48."))
    assert decided.output.status.value in ("awaiting_human_validation", "verification_failed")
    assert decided.output.historique_corrections
