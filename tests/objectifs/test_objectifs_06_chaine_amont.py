"""Passation amont : la sortie RÉELLE de l'Agent Question de recherche (étape 5) alimente l'agent 6."""

from research_objectives_agent.pipeline import campaign
from objectifs_helpers import StubLLM, upstream_question


def test_question_amont_extrait_le_texte():
    from research_objectives_agent.schemas.input import ObjectivesRequest
    payload = upstream_question()
    req = ObjectivesRequest(student_id="e", upstream_question=payload, discipline="Gestion")
    # La question principale est extraite de la sortie de l'agent 5.
    assert "télétravail" in req.effective_question().lower()
    # Le sujet vient du champ `subject` faute de `subject_text`.
    assert req.effective_subject()


def test_campagne_depuis_une_sortie_amont_reelle(settings):
    from research_objectives_agent.schemas.input import ObjectivesRequest
    req = ObjectivesRequest(student_id="e", session_id="s", discipline="Sciences de gestion",
                            academic_level="Master 2", upstream_question=upstream_question())
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.main_research_question
    assert result.output.general_objective
    assert result.output.specific_objectives
