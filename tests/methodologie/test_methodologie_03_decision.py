"""Portillon humain : décision de l'étudiant / de l'encadreur (SPEC §11, §12)."""

import pytest

from methodology_diagnostic_agent.core.errors import PipelineError
from methodology_diagnostic_agent.pipeline import campaign
from methodology_diagnostic_agent.schemas.decision import DecisionRequest, DecisionValue
from methodologie_helpers import StubLLM


def _proposal(settings, request_factory, **llm_kwargs):
    llm = StubLLM(**llm_kwargs)
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    return request_factory(), llm, result.output


def test_acceptation_produit_validated(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.accepted, student_comment="d'accord")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.status.value == "validated"
    assert res.output.diagnostic_status.value == "valide"
    assert res.output.provisional is False
    assert res.output.student_validation.decision.value == "accepted"


def test_refus_produit_blocked_et_a_reviser(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.refused, student_comment="non")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.status.value == "blocked"
    assert res.output.diagnostic_status.value == "a_reviser"


def test_modification_choix_alternative_reverifiee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.modified,
                               modified={"approche": "Approche mixte",
                                         "strategie": "Étude de cas comparative"},
                               student_comment="je préfère une approche mixte")
    res = campaign.decide(req, settings, llm, out, decision)
    assert res.output.diagnosis.approche.proposition == "Approche mixte"
    assert res.output.status.value == "awaiting_human_validation"


def test_modification_sans_contenu_refusee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.modified)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(req, settings, llm, out, decision)
    assert exc.value.state.value == "INVALID_INPUT"


def test_information_fournie_consignee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    decision = DecisionRequest(decision=DecisionValue.modified,
                               provided_information="La productivité est mesurée par le nombre de "
                                                    "tickets traités par jour.")
    res = campaign.decide(req, settings, llm, out, decision)
    assert any("informations complémentaires" in n.lower()
               for n in res.output.limits_of_this_output)


def test_acceptation_sans_verification_refusee(settings, request_factory):
    req, llm, out = _proposal(settings, request_factory)
    out.verification_result.verified = False
    decision = DecisionRequest(decision=DecisionValue.accepted)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(req, settings, llm, out, decision)
    assert exc.value.state.value == "MISSING_INFORMATION"
