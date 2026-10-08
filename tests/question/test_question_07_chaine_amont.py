"""Passation amont : la sortie RÉELLE de l'Agent Problématique (étape 4) alimente l'agent 5."""

from research_question_agent.pipeline import campaign
from question_helpers import StubLLM, upstream_problematic


def test_problematique_amont_extrait_le_texte():
    from research_question_agent.schemas.input import QuestionRequest
    payload = upstream_problematic()
    req = QuestionRequest(student_id="e", upstream_problematic=payload, discipline="Gestion")
    # Le texte de la problématique est extrait de `problematique_note.texte_complet`.
    assert "télétravail" in req.effective_problematic().lower()
    # Le sujet vient de `subject_reference` faute de `subject_text`.
    assert req.effective_subject()


def test_campagne_depuis_une_sortie_amont_reelle(settings):
    from research_question_agent.schemas.input import QuestionRequest
    req = QuestionRequest(student_id="e", session_id="s", discipline="Sciences de gestion",
                          academic_level="Master 2", upstream_problematic=upstream_problematic())
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.validated_problematic
    assert result.output.main_research_question
