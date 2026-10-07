"""Interface HTTP : /health, /problematique/analyze, lecture de la note."""

import pathlib

from fastapi.testclient import TestClient
from problematique_helpers import StubLLM, literature_payload

from problematization_agent.main import app
from problematization_agent.storage import audit


def _client_with_stub(tmp_path):
    client = TestClient(app)
    client.__enter__()
    settings = client.app.state.settings
    settings.paths = dict(settings.paths)
    settings.paths["workspace"] = str(tmp_path / "ws")
    settings.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    settings.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    settings.sources = dict(settings.sources or {})
    settings.sources["enabled"] = False  # aucun réseau pendant les tests
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    audit.init(settings.audit_db)
    stub = StubLLM()
    client.app.state.llm = stub
    client.app.state.verifier_llm = stub
    return client


def _body(**overrides):
    body = {
        "student_id": "etu-1",
        "subject_text": "Effets du télétravail sur la productivité des développeurs d'Abidjan",
        "research_problem": "Les délais ne sont plus tenus depuis le passage au télétravail.",
        "discipline": "Sciences de gestion",
        "academic_level": "Master 2",
        "country": "Côte d'Ivoire",
        "geographical_scope": "Abidjan",
        "upstream_literature": literature_payload(),
    }
    body.update(overrides)
    return body


def test_health(tmp_path):
    client = _client_with_stub(tmp_path)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["agent"] == "problematization_agent"
    finally:
        client.__exit__(None, None, None)


def test_analyze_puis_lecture(tmp_path):
    client = _client_with_stub(tmp_path)
    try:
        response = client.post("/problematique/analyze", json=_body())
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "ready_for_verification"
        assert payload["verifier_status"] == "verified"
        assert payload["gap"] == "contextuelle"
        assert payload["output"]["validation"]["verified"] is True

        session_id = payload["session_id"]
        read = client.get(f"/problematique/etu-1/{session_id}")
        assert read.status_code == 200
        assert read.json()["agent"] == "problematization_agent"
    finally:
        client.__exit__(None, None, None)


def test_analyze_sans_revue_verifiee_422(tmp_path):
    client = _client_with_stub(tmp_path)
    try:
        response = client.post("/problematique/analyze",
                              json=_body(upstream_literature=literature_payload(verified=False)))
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "MISSING_INFORMATION"
    finally:
        client.__exit__(None, None, None)
