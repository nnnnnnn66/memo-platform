"""Passation amont : la sortie RÉELLE de l'Agent Hypothèses (étape 7) alimente l'agent 8."""

from methodology_diagnostic_agent.pipeline import campaign
from methodologie_helpers import StubLLM, upstream_agents_5_7, upstream_hypotheses


def test_hypotheses_amont_extraits():
    from methodology_diagnostic_agent.schemas.input import MethodologyRequest
    payload = upstream_hypotheses()
    req = MethodologyRequest(student_id="e", upstream_hypotheses=payload, discipline="Gestion")
    assert "télétravail" in req.effective_question().lower()
    assert req.effective_general_objective()
    assert req.effective_hypotheses()
    assert req.effective_subject()


def test_forme_reelle_verification_result_est_reconnue():
    """La clé `verification_result` (agents 5-7) vaut vérification, comme `validation` (agents 1-4)."""
    from methodology_diagnostic_agent.schemas.input import MethodologyRequest
    from methodology_diagnostic_agent.schemas.input import UpstreamPayload

    reel = UpstreamPayload.model_validate(upstream_agents_5_7())
    assert reel.validation.verified is False       # la clé `validation` est absente
    assert reel.is_verified is True                # ... mais la sortie est bien vérifiée
    # Un amont NON vérifié reste refusé.
    assert UpstreamPayload.model_validate(upstream_agents_5_7(verified=False)).is_verified is False

    req = MethodologyRequest(student_id="e", upstream_hypotheses=upstream_agents_5_7(),
                             discipline="Gestion")
    assert req.effective_subject() and req.effective_question()


def test_fichier_reel_de_l_agent_7_est_ingere(settings):
    """Passation RÉELLE A7 -> A8 : le fichier produit sur disque est ingéré tel quel (sans réseau).

    Ignoré si la campagne réelle de l'Agent 7 n'est pas présente (dépôt fraîchement cloné).
    """
    import json
    import pathlib

    from methodology_diagnostic_agent.schemas.input import MethodologyRequest

    fichier = pathlib.Path(__file__).resolve().parents[2] / "workspace" / "etudiant-demo" / \
        "session-demo" / "hypotheses_output.json"
    if not fichier.exists():
        import pytest
        pytest.skip("sortie réelle de l'Agent 7 absente (campagne non jouée sur ce poste)")

    reel = json.loads(fichier.read_text(encoding="utf-8"))
    assert reel["status"] == "validated"
    assert "validation" not in reel and reel["verification_result"]["verified"] is True

    req = MethodologyRequest(student_id="e", session_id="s", discipline="Sciences de gestion",
                             academic_level="Master 2",
                             available_data="Enquête", field_access="Accès confirmé.",
                             available_resources="6 mois",
                             upstream_hypotheses=reel)
    # Le dossier réel contient 3 hypothèses : le diagnostic doit dire lesquelles il peut examiner (M7).
    from methodologie_helpers import DEFAULT_DIAGNOSIS
    diagnosis = json.loads(json.dumps(DEFAULT_DIAGNOSIS))
    diagnosis["hypotheses_examined"] = [h["formulation"] for h in reel["research_hypotheses"]]
    result = campaign.run(req, settings, StubLLM(diagnosis=diagnosis), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.subject and result.output.main_research_question
    assert result.output.diagnosis.approche.code
    assert len(result.output.hypotheses_examined) == len(reel["research_hypotheses"])


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
