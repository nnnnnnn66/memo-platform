"""API HTTP : analyse, récupération, décision (TestClient, LLM simulé)."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from hypotheses_helpers import StubLLM, upstream_objectives


@pytest.fixture
def client(tmp_path):
    from research_hypotheses_agent.core.config import Settings
    from research_hypotheses_agent.main import app

    with TestClient(app) as test_client:
        config = Settings()
        config.paths = dict(config.paths)
        config.paths["workspace"] = str(tmp_path / "ws")
        config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
        config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
        config.limits = dataclasses.replace(config.limits, max_llm_calls=20)
        config.clarification = {"enabled": False}
        app.state.settings = config
        app.state.llm = StubLLM()
        app.state.verifier_llm = app.state.llm
        from research_hypotheses_agent.storage import audit
        audit.init(config.audit_db)
        yield test_client


BODY = {
    "student_id": "etu-api", "session_id": "sess-1",
    "subject_text": "Le télétravail et la productivité des développeurs",
    "discipline": "Sciences de gestion", "academic_level": "Master 2",
    "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité ?",
    "general_objective": "Analyser la relation entre télétravail et productivité.",
    "specific_objectives": ["Identifier les conditions de travail associées à la productivité."],
    "validated_problematic": "Le lien entre télétravail et productivité reste discuté.",
}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "research_hypotheses_agent"


def test_analyze_puis_decision(client):
    resp = client.post("/hypotheses/analyze", json=BODY)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["verifier_status"] == "verified"
    assert data["output"]["hypotheses_decision"] == "HYPOTHESES_RECOMMENDED"
    assert data["output"]["research_hypotheses"]

    got = client.get("/hypotheses/etu-api/sess-1")
    assert got.status_code == 200

    dec = client.post("/hypotheses/etu-api/sess-1/decision",
                      json={"decision": "accepted", "student_comment": "ok"})
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "validated"


def test_analyze_sans_objectifs_renvoie_needs_clarification(client):
    body = dict(BODY, general_objective="", specific_objectives=[])
    resp = client.post("/hypotheses/analyze", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_clarification"


def test_chaine_upstream_objectifs_verifies(client):
    body = dict(BODY, general_objective="", specific_objectives=[],
                upstream_objectives=upstream_objectives())
    resp = client.post("/hypotheses/analyze", json=body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "awaiting_human_validation"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/hypotheses/inconnu/inexistant/decision", json={"decision": "accepted"})
    assert resp.status_code == 404
