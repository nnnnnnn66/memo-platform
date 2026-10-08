"""Portillon humain : décision de l'étudiant (SPEC §12, §13)."""

import pytest

from research_question_agent.core.errors import PipelineError
from research_question_agent.pipeline import campaign
from research_question_agent.schemas.decision import DecisionRequest, DecisionValue
from question_helpers import StubLLM


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
    decision = DecisionRequest(decision=DecisionValue.modified,
                               modified_question="En quoi le télétravail modifie-t-il la "
                                                 "productivité des développeurs ?")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.main_research_question.startswith("En quoi")
    assert res.output.status.value == "awaiting_human_validation"


def test_modification_presupposee_rejetee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.modified,
                               modified_question="Pourquoi le télétravail est-il inefficace ?")
    with pytest.raises(PipelineError) as exc:
        campaign.decide(req, settings, llm, out, decision)
    assert exc.value.state.value == "INVALID_INPUT"


def test_acceptation_sans_verification_refusee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    out.verification_result.verified = False
    decision = DecisionRequest(decision=DecisionValue.accepted)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(req, settings, llm, out, decision)
    assert exc.value.state.value == "MISSING_INFORMATION"
