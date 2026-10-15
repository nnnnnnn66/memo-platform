"""API HTTP : rédaction, récupération, décision (TestClient, LLM simulé)."""

import dataclasses

import pytest
from conclusion_helpers import StubLLM, upstream_question, upstream_results
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    from research_conclusion_agent.core.config import Settings
    from research_conclusion_agent.main import app

    with TestClient(app) as test_client:
        config = Settings()
        config.paths = dict(config.paths)
        config.paths["workspace"] = str(tmp_path / "ws")
        config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
        config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
        config.limits = dataclasses.replace(config.limits, max_llm_calls=22)
        app.state.settings = config
        app.state.llm = StubLLM()
        app.state.verifier_llm = app.state.llm
        from research_conclusion_agent.storage import audit
        audit.init(config.audit_db)
        yield test_client


def _body(**overrides):
    body = {
        "student_id": "etu-api", "session_id": "sess-1",
        "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "discipline": "Sciences de gestion", "academic_level": "Master 2",
        "upstream_question": upstream_question(),
        "upstream_results": upstream_results(),
        "upstream_objectives": {
            "agent": "research_objectives_agent", "status": "validated",
            "general_objective": "Analyser la relation entre le télétravail et la productivité.",
            "specific_objectives": ["Décrire l'intensité du télétravail déclarée."],
            "verification_result": {"verified": True, "verifier_status": "verified"}},
        "upstream_methodology": {
            "agent": "methodology_agent", "status": "validated", "document_status": "valide",
            "protocol": {"approche": "quantitative", "type_recherche": "explicative"},
            "verification_result": {"verified": True, "verifier_status": "verified"},
            "student_validation": {"decision": "accepted", "comment": ""}},
    }
    body.update(overrides)
    return body


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "research_conclusion_agent"


def test_write_puis_decision(client):
    resp = client.post("/conclusion/write", json=_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["verifier_status"] == "verified"
    assert data["resultats_retenus"] > 0
    assert data["references_resultats"] > 0
    assert data["output"]["synthesis"]["reponse_question"]["reponse"]

    got = client.get("/conclusion/etu-api/sess-1")
    assert got.status_code == 200

    dec = client.post("/conclusion/etu-api/sess-1/decision",
                      json={"decision": "accepted", "student_comment": "ok"})
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "validated"
    assert dec.json()["document_status"] == "valide"


def test_write_sans_resultats_produit_un_plan(client):
    """Sans résultats, la réponse est un PLAN déclaré — jamais une question renvoyée à l'étudiante.

    Même défaut que celui décrit dans tests/conclusion/test_conclusion_02_campagne.py : le test
    décrivait l'ancien renvoi à la copie, qui bloquait la dernière étape d'un dossier complet.
    """
    body = {k: v for k, v in _body().items() if k != "upstream_results"}
    resp = client.post("/conclusion/write", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] != "needs_clarification"
    assert resp.json()["output"]["synthesis"]["plan_seulement"] is True


def test_resultats_non_verifies_422(client):
    resp = client.post("/conclusion/write",
                       json=_body(upstream_results=upstream_results(verified=False)))
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "MISSING_INFORMATION"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/conclusion/inconnu/inexistant/decision", json={"decision": "accepted"})
    assert resp.status_code == 404
