"""Bornes de consommation, isolation et surface HTTP."""

import pytest
from litterature_helpers import (
    DEFAULT_RESPONSES,
    FakeApiFetcher,
    FakeDownloader,
    SmartStubLLM,
)

from literature_review_agent.core.sessions import session_dir
from literature_review_agent.pipeline import campaign
from literature_review_agent.storage import workspace


def test_requetes_bornees_par_la_phase_1(settings, request_factory):
    """Le nombre de requêtes exécutées ne dépasse jamais MAX_SEARCH_QUERIES."""
    fetcher = FakeApiFetcher(DEFAULT_RESPONSES)
    result = campaign.run(request_factory(), settings, SmartStubLLM(), fetcher=fetcher,
                          downloader=FakeDownloader())

    queries = result.output.corpus.queries
    assert len(queries) <= settings.limits.max_search_queries
    assert result.stages["retrieval"]["documents_collected"] > 0


def test_lots_d_analyse_plafonnes(settings, request_factory):
    """Au plus MAX_SCORING_BATCHES lots : le budget LLM reste borné."""
    result = campaign.run(request_factory(), settings, SmartStubLLM(),
                          fetcher=FakeApiFetcher(DEFAULT_RESPONSES), downloader=FakeDownloader())
    max_analyzed = settings.limits.documents_per_scoring_batch * settings.limits.max_scoring_batches
    assert len(result.output.corpus.documents) <= max_analyzed


def test_appels_llm_plafonnes(settings, request_factory):
    llm = SmartStubLLM()
    campaign.run(request_factory(), settings, llm,
                 fetcher=FakeApiFetcher(DEFAULT_RESPONSES), downloader=FakeDownloader())
    assert llm.calls <= settings.limits.max_llm_calls


def test_plafond_de_documents_respecte(settings, request_factory):
    result = campaign.run(request_factory(), settings, SmartStubLLM(),
                          fetcher=FakeApiFetcher(DEFAULT_RESPONSES), downloader=FakeDownloader())
    assert len(result.output.corpus.documents) <= settings.limits.max_documents


def test_isolation_des_espaces_de_travail(settings):
    ws = settings.workspace_dir
    workspace.save(ws, "etu-1", "s1", "review_output", {"x": 1})
    workspace.save(ws, "etu-2", "s1", "review_output", {"x": 2})

    assert workspace.load(ws, "etu-1", "s1", "review_output") == {"x": 1}
    assert workspace.load(ws, "etu-2", "s1", "review_output") == {"x": 2}
    assert workspace.load(ws, "etu-1", "s2", "review_output") is None


def test_traversee_de_chemin_neutralisee(settings):
    path = session_dir(settings.workspace_dir, "../../etc", "../../passwd")
    assert ".." not in str(path)
    assert str(settings.workspace_dir) in str(path)


def test_configuration_propre_a_l_agent():
    import pathlib

    from literature_review_agent.core.config import Settings

    agent = Settings().paths
    assert agent["audit_db"] == "workspace/audit-litterature.db"
    assert agent["cache_db"] == "workspace/documents-cache.db"
    assert pathlib.Path("config/settings-litterature.yaml").name in str(
        pathlib.Path("config") / "settings-litterature.yaml")


def test_endpoints_http(settings):
    from fastapi.testclient import TestClient

    from literature_review_agent.main import app

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["agent"] == "literature_review_agent"

        invalid = client.post("/literature/review", json={"student_id": "", "subject_text": "x"})
        assert invalid.status_code == 422

        missing = client.get("/literature/etu-1/session-x")
        assert missing.status_code == 404

        manifest = client.get("/literature/etu-1/session-x/documents")
        assert manifest.status_code == 404
