"""Fixtures des tests de l'Agent Revue de littérature (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from literature_review_agent.core.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    """Réglages de l'agent, workspace et caches isolés, bornes resserrées pour les tests."""
    config = Settings()
    config.paths = dict(config.paths)
    config.paths["workspace"] = str(tmp_path / "ws")
    config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    config.limits = dataclasses.replace(
        config.limits,
        max_documents=4,
        min_documents_useful=2,
        documents_per_scoring_batch=2,
        max_scoring_batches=2,
        max_search_queries=3,
        max_results_per_query=2,
        max_external_requests=20,
        max_llm_calls=12,
        unpaywall_max_lookups=2,
        max_thesis_resolvers=1,
        max_downloads=2,
    )
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from literature_review_agent.schemas.input import CampaignRequest

        payload = {
            "student_id": "etu-1",
            "subject_text": "Effets du télétravail sur la productivité des développeurs "
                            "d'Abidjan, 2020-2024",
            "discipline": "Sciences de gestion",
            "academic_level": "Master 2",
            "country": "Côte d'Ivoire",
            "geographical_scope": "Abidjan",
            "period": "2020-2024",
        }
        payload.update(overrides)
        return CampaignRequest(**payload)

    return make
