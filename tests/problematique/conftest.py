"""Fixtures des tests de l'Agent Problématique (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from problematization_agent.core.config import Settings  # noqa: E402


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
        max_documents_read=10,
        max_gap_check_queries=2,
        max_results_per_query=3,
        max_external_requests=40,  # 8 fournisseurs × 2 requêtes × 2 tentatives
        max_llm_calls=30,
        max_verification_retries=2,
    )
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from problematization_agent.schemas.input import ProblemRequest
        from problematique_helpers import literature_payload

        payload = {
            "student_id": "etu-1",
            "subject_text": "Effets du télétravail sur la productivité des développeurs d'Abidjan, "
                            "2020-2024",
            "research_problem": "Les entreprises d'Abidjan constatent une baisse de performance "
                                "depuis le passage au télétravail.",
            "discipline": "Sciences de gestion",
            "academic_level": "Master 2",
            "country": "Côte d'Ivoire",
            "geographical_scope": "Abidjan",
            "population": "développeurs",
            "field_observations": "Des équipes de développement peinent à tenir leurs délais.",
            "upstream_literature": literature_payload(),
        }
        payload.update(overrides)
        return ProblemRequest(**payload)

    return make
