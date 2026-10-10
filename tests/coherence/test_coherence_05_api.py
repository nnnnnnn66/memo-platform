"""API HTTP de l'agent d'audit (TestClient, LLM simulé)."""

import dataclasses

import pytest
from coherence_helpers import StubLLM, dossier_complet
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    from research_coherence_verifier.core.config import Settings
    from research_coherence_verifier.main import app
    from research_coherence_verifier.storage import audit

    with TestClient(app) as test_client:
        config = Settings()
        config.paths = dict(config.paths)
        config.paths["workspace"] = str(tmp_path / "ws")
        config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
        config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
        config.limits = dataclasses.replace(config.limits, max_llm_calls=16)
        config.security = {"fail_on_injection": False}
        app.state.settings = config
        app.state.llm = StubLLM()
        app.state.verifier_llm = app.state.llm
        audit.init(config.audit_db)
        yield test_client


def _body(**overrides):
    body = dossier_complet()
    body["student_id"] = "etu-api"
    body["session_id"] = "sess-audit"
    body.update(overrides)
    return body


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "research_coherence_verifier"


def test_audit_puis_decision(client):
    resp = client.post("/coherence/audit", json=_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "awaiting_human_validation"
    assert data["verifier_status"] == "verified"
    assert data["verdict"] == "coherent"
    assert data["non_verifiable"] >= 7
    assert data["etapes_presentes"] == 11
    assert data["llm_calls"] == 3

    got = client.get("/coherence/etu-api/sess-audit")
    assert got.status_code == 200

    decide = client.post("/coherence/etu-api/sess-audit/decision",
                         json={"decision": "accepted", "student_comment": "lu"})
    assert decide.status_code == 200, decide.text
    assert decide.json()["status"] == "validated"
    assert decide.json()["document_status"] == "valide"


def test_audit_d_un_dossier_fusionne_donne_incoherent(client):
    from coherence_helpers import dossier_fusionne
    resp = client.post("/coherence/audit", json=_body(**dossier_fusionne()))
    assert resp.status_code == 200, resp.text
    assert resp.json()["verdict"] == "incoherent"
    assert resp.json()["constats_bloqueurs"] >= 1


def test_dossier_sans_etape_verifiee_422(client):
    body = _body()
    for cle in list(body):
        if cle.startswith("upstream_") and isinstance(body[cle], dict):
            body[cle] = {**body[cle], "verification_result": {"verified": False}}
    resp = client.post("/coherence/audit", json=body)
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "MISSING_INFORMATION"


def test_decision_sur_session_inconnue_404(client):
    resp = client.post("/coherence/inconnu/inexistant/decision", json={"decision": "accepted"})
    assert resp.status_code == 404
