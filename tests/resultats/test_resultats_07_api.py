"""API HTTP : analyse, récupération, décision (TestClient, LLM simulé)."""

import dataclasses

import pytest
from fastapi.testclient import TestClient
from resultats_helpers import CSV, StubLLM


@pytest.fixture
def client(tmp_path):
    from research_results_analysis_agent.core.config import Settings
    from research_results_analysis_agent.main import app

    with TestClient(app) as test_client:
        config = Settings()
        config.paths = dict(config.paths)
        config.paths["workspace"] = str(tmp_path / "ws")
        config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
        config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
        config.limits = dataclasses.replace(config.limits, max_llm_calls=24)
        app.state.settings = config
        app.state.llm = StubLLM()
        app.state.verifier_llm = app.state.llm
        from research_results_analysis_agent.storage import audit
        audit.init(config.audit_db)
        yield test_client


def _body(**overrides):
    from resultats_helpers import upstream_methodology

    body = {
        "student_id": "etu-api", "session_id": "sess-1",
        "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
        "discipline": "Sciences de gestion", "academic_level": "Master 2",
        "data_origin": "Questionnaire administré", "data_period": "2024",
        "datasets": [{"nom": "enquete", "format": "csv", "contenu": CSV,
                      "source": "Questionnaire administré", "periode": "2024"}],
        "upstream_methodology": upstream_methodology(),
    }
    body.update(overrides)
    return body


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "research_results_analysis_agent"


def test_analyze_puis_decision(client):
    resp = client.post("/results/analyze", json=_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["document_status"] == "en_attente_de_validation"
    assert data["verifier_status"] == "verified"
    assert data["calculs"] > 0
    assert data["output"]["computed_results"]["resultats"]

    got = client.get("/results/etu-api/sess-1")
    assert got.status_code == 200

    dec = client.post("/results/etu-api/sess-1/decision",
                      json={"decision": "accepted", "student_comment": "ok"})
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "validated"
    assert dec.json()["document_status"] == "valide"


def test_analyze_sans_methodologie_needs_clarification(client):
    body = {k: v for k, v in _body().items() if k != "upstream_methodology"}
    resp = client.post("/results/analyze", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_clarification"
    assert resp.json()["output"]["questions_for_human"]


def test_methodologie_non_verifiee_422(client):
    from resultats_helpers import upstream_methodology
    resp = client.post("/results/analyze",
                       json=_body(upstream_methodology=upstream_methodology(verified=False)))
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "MISSING_INFORMATION"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/results/inconnu/inexistant/decision", json={"decision": "accepted"})
    assert resp.status_code == 404
