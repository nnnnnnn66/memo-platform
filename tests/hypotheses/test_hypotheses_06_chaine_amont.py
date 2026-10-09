"""Passation amont : la sortie RÉELLE de l'Agent Objectifs (étape 6) alimente l'agent 7."""

from research_hypotheses_agent.pipeline import campaign
from hypotheses_helpers import StubLLM, upstream_objectives


def test_objectifs_amont_extraits():
    from research_hypotheses_agent.schemas.input import HypothesesRequest
    payload = upstream_objectives()
    req = HypothesesRequest(student_id="e", upstream_objectives=payload, discipline="Gestion")
    assert "télétravail" in req.effective_question().lower()
    assert req.effective_general_objective()
    assert req.effective_specific_objectives()
    assert req.effective_subject()


def test_campagne_depuis_une_sortie_amont_reelle(settings):
    from research_hypotheses_agent.schemas.input import HypothesesRequest
    req = HypothesesRequest(student_id="e", session_id="s", discipline="Sciences de gestion",
                            academic_level="Master 2", upstream_objectives=upstream_objectives())
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.general_objective
    assert result.output.research_hypotheses
