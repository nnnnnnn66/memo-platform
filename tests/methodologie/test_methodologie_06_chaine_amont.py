"""Passation amont : la sortie RÉELLE de l'Agent Hypothèses (étape 7) alimente l'agent 8."""

from methodology_diagnostic_agent.pipeline import campaign
from methodologie_helpers import StubLLM, upstream_hypotheses


def test_hypotheses_amont_extraits():
    from methodology_diagnostic_agent.schemas.input import MethodologyRequest
    payload = upstream_hypotheses()
    req = MethodologyRequest(student_id="e", upstream_hypotheses=payload, discipline="Gestion")
    assert "télétravail" in req.effective_question().lower()
    assert req.effective_general_objective()
    assert req.effective_hypotheses()
    assert req.effective_subject()


def test_campagne_depuis_une_sortie_amont_reelle(settings):
    from methodology_diagnostic_agent.schemas.input import MethodologyRequest
    req = MethodologyRequest(student_id="e", session_id="s", discipline="Sciences de gestion",
                             academic_level="Master 2",
                             available_data="Enquête", field_access="Accès confirmé.",
                             available_resources="6 mois",
                             upstream_hypotheses=upstream_hypotheses(with_hypotheses=False))
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.diagnosis.approche.code
    assert result.output.hypotheses_examined == []


def test_hypotheses_amont_traitees_par_le_diagnostic(settings):
    from methodology_diagnostic_agent.schemas.input import MethodologyRequest
    diagnosis = {"resume": "r", "diagnosis": {
        "approche": {"code": "quantitative", "proposition": "Approche quantitative",
                     "justification": "j"},
        "logique": {"code": "hypothetico_deductive", "proposition": "Démarche déductive",
                    "justification": "j"},
        "type_recherche": {"code": "explicative", "proposition": "Recherche explicative",
                           "justification": "j"},
        "strategie": {"code": "enquete", "proposition": "Enquête", "justification": "j",
                      "conditions": ["accès"]},
        "collecte": [{"proposition": "Questionnaire", "justification": "j"}],
        "analyse": [{"proposition": "Corrélation", "justification": "j"}],
        "articulation": "a", "coherence_question": "c"},
        "hypotheses_examined": ["H1 : coordination ↔ productivité"],
        "feasibility_controls": [], "limits_of_this_output": [], "questions_for_human": []}
    req = MethodologyRequest(student_id="e", session_id="s", discipline="Gestion",
                             available_data="Enquête", field_access="Accès confirmé.",
                             available_resources="6 mois",
                             upstream_hypotheses=upstream_hypotheses())
    result = campaign.run(req, settings, StubLLM(diagnosis=diagnosis), allow_network=False)
    assert result.output.hypotheses_examined
