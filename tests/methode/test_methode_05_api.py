"""API HTTP : analyse, récupération, décision (TestClient, LLM simulé)."""

import dataclasses

import pytest
from fastapi.testclient import TestClient
from methode_helpers import StubLLM, upstream_diagnostic


@pytest.fixture
def client(tmp_path):
    from methodology_agent.core.config import Settings
    from methodology_agent.main import app

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
        from methodology_agent.storage import audit
        audit.init(config.audit_db)
        yield test_client


BODY = {
    "student_id": "etu-api", "session_id": "sess-1",
    "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
    "discipline": "Sciences de gestion", "academic_level": "Master 2",
    "country": "Côte d'Ivoire", "geographical_area": "Abidjan", "study_period": "2020-2024",
    "target_population": "développeurs en télétravail",
    "field_access": "Accès confirmé à deux entreprises.",
    "available_data": "Questionnaires et entretiens à réaliser.",
    "available_resources": "Six mois, budget limité.",
    "upstream_methodology_diagnostic": upstream_diagnostic(),
}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "methodology_agent"


def test_analyze_puis_decision(client):
    resp = client.post("/methodology/protocol/analyze", json=BODY)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["document_status"] == "en_attente_de_validation"
    assert data["verifier_status"] == "verified"
    assert data["objectifs_couverts"] == data["objectifs_total"] > 0
    assert data["output"]["protocol"]["approche"] == "quantitative"
    assert data["output"]["draft"]["sections"]

    got = client.get("/methodology/protocol/etu-api/sess-1")
    assert got.status_code == 200

    dec = client.post("/methodology/protocol/etu-api/sess-1/decision",
                      json={"decision": "accepted", "student_comment": "ok"})
    assert dec.status_code == 200, dec.text
    assert dec.json()["status"] == "validated"
    assert dec.json()["document_status"] == "valide"


def test_analyze_sans_diagnostic_renvoie_needs_clarification(client):
    body = {k: v for k, v in BODY.items() if k != "upstream_methodology_diagnostic"}
    resp = client.post("/methodology/protocol/analyze", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "needs_clarification"
    assert data["output"]["questions_for_human"]


def test_diagnostic_non_verifie_refuse(client):
    body = dict(BODY, upstream_methodology_diagnostic=upstream_diagnostic(verified=False))
    resp = client.post("/methodology/protocol/analyze", json=body)
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "MISSING_INFORMATION"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/methodology/protocol/inconnu/inexistant/decision",
                       json={"decision": "accepted"})
    assert resp.status_code == 404
