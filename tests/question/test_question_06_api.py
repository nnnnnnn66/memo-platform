"""API HTTP : analyse, récupération, décision (TestClient, LLM simulé)."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from question_helpers import StubLLM, upstream_problematic


@pytest.fixture
def client(tmp_path):
    from research_question_agent.core.config import Settings
    from research_question_agent.main import app

    with TestClient(app) as test_client:
        config = Settings()
        config.paths = dict(config.paths)
        config.paths["workspace"] = str(tmp_path / "ws")
        config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
        config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
        config.limits = dataclasses.replace(config.limits, max_llm_calls=16)
        config.clarification = {"enabled": False}
        app.state.settings = config
        app.state.llm = StubLLM()
        app.state.verifier_llm = app.state.llm
        from research_question_agent.storage import audit
        audit.init(config.audit_db)
        yield test_client


BODY = {
    "student_id": "etu-api", "session_id": "sess-1",
    "subject_text": "Le télétravail et la productivité des développeurs",
    "discipline": "Sciences de gestion", "academic_level": "Master 2",
    "validated_problematic": "Le lien entre télétravail et productivité reste discuté.",
}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "research_question_agent"


def test_analyze_puis_decision(client):
    resp = client.post("/question/analyze", json=BODY)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["verifier_status"] == "verified"
    assert data["output"]["main_research_question"]

    got = client.get("/question/etu-api/sess-1")
    assert got.status_code == 200

    dec = client.post("/question/etu-api/sess-1/decision",
                      json={"decision": "accepted", "student_comment": "ok"})
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "validated"


def test_analyze_sans_problematique_renvoie_needs_clarification(client):
    body = dict(BODY, validated_problematic="")
    resp = client.post("/question/analyze", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_clarification"


def test_chaine_upstream_problematique_verifiee(client):
    body = dict(BODY, validated_problematic="", upstream_problematic=upstream_problematic())
    resp = client.post("/question/analyze", json=body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "awaiting_human_validation"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/question/inconnu/inexistant/decision", json={"decision": "accepted"})
    assert resp.status_code == 404
