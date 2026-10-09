"""API HTTP : analyse, récupération, décision (TestClient, LLM simulé)."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from objectifs_helpers import StubLLM, upstream_question


@pytest.fixture
def client(tmp_path):
    from research_objectives_agent.core.config import Settings
    from research_objectives_agent.main import app

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
        from research_objectives_agent.storage import audit
        audit.init(config.audit_db)
        yield test_client


BODY = {
    "student_id": "etu-api", "session_id": "sess-1",
    "subject_text": "Le télétravail et la productivité des développeurs",
    "discipline": "Sciences de gestion", "academic_level": "Master 2",
    "main_research_question": "Dans quelle mesure le télétravail influence-t-il la productivité ?",
    "validated_problematic": "Le lien entre télétravail et productivité reste discuté.",
}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "research_objectives_agent"


def test_analyze_puis_decision(client):
    resp = client.post("/objectives/analyze", json=BODY)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["verifier_status"] == "verified"
    assert data["output"]["general_objective"]
    assert data["output"]["specific_objectives"]

    got = client.get("/objectives/etu-api/sess-1")
    assert got.status_code == 200

    dec = client.post("/objectives/etu-api/sess-1/decision",
                      json={"decision": "accepted", "student_comment": "ok"})
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "validated"


def test_analyze_sans_question_renvoie_needs_clarification(client):
    body = dict(BODY, main_research_question="")
    resp = client.post("/objectives/analyze", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_clarification"


def test_chaine_upstream_question_verifiee(client):
    body = dict(BODY, main_research_question="", upstream_question=upstream_question())
    resp = client.post("/objectives/analyze", json=body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "awaiting_human_validation"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/objectives/inconnu/inexistant/decision", json={"decision": "accepted"})
    assert resp.status_code == 404
