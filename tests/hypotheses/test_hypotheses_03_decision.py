"""Portillon humain : décision de l'étudiant (SPEC §12, §13)."""

import pytest

from research_hypotheses_agent.core.errors import PipelineError
from research_hypotheses_agent.pipeline import campaign
from research_hypotheses_agent.schemas.decision import DecisionRequest, DecisionValue
from hypotheses_helpers import StubLLM


def _proposal(settings, request_factory, **llm_kwargs):
    llm = StubLLM(**llm_kwargs)
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    return request_factory(), llm, result.output


def test_acceptation_produit_validated(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.accepted, student_comment="d'accord")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.status.value == "validated"
    assert res.output.student_validation.decision.value == "accepted"


def test_refus_produit_blocked(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.refused, student_comment="non")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.status.value == "blocked"
    assert res.output.student_validation.decision.value == "refused"


def test_modification_neutre_reverifiee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(
        decision=DecisionValue.modified,
        modified_hypotheses=[
            "La coordination des équipes est associée à la productivité des développeurs en "
            "télétravail."])
    res = campaign.decide(req, settings, llm, out, decision)
    assert len(res.output.research_hypotheses) == 1
    assert res.output.status.value == "awaiting_human_validation"


def test_modification_presupposee_rejetee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(
        decision=DecisionValue.modified,
        modified_hypotheses=["Il est démontré que le télétravail réduit la productivité."])
    with pytest.raises(PipelineError) as exc:
        campaign.decide(req, settings, llm, out, decision)
    assert exc.value.state.value == "INVALID_INPUT"


def test_modification_de_decision_vers_sans_hypotheses(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.modified,
                               modified_decision="HYPOTHESES_NOT_REQUIRED")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.hypotheses_decision.value == "HYPOTHESES_NOT_REQUIRED"
    assert res.output.status.value == "awaiting_human_validation"


def test_acceptation_sans_verification_refusee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    out.verification_result.verified = False
    decision = DecisionRequest(decision=DecisionValue.accepted)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(req, settings, llm, out, decision)
    assert exc.value.state.value == "MISSING_INFORMATION"
