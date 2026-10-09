"""Fixtures des tests de l'Agent Hypothèses de recherche (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from research_hypotheses_agent.core.config import Settings  # noqa: E402


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
        max_clarification_queries=2,
        max_results_per_query=3,
        max_external_requests=40,
        max_llm_calls=20,
        max_verification_retries=2,
    )
    config.clarification = {"enabled": False}
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from research_hypotheses_agent.schemas.input import HypothesesRequest

        payload = {
            "student_id": "etu-1",
            "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
            "research_problem": "Les entreprises d'Abidjan constatent des effets contrastés du "
                                "télétravail sur la productivité.",
            "discipline": "Sciences de gestion",
            "academic_level": "Master 2",
            "country": "Côte d'Ivoire",
            "geographical_area": "Abidjan",
            "study_period": "2020-2024",
            "target_population": "développeurs",
            "validated_problematic": "La littérature montre un lien ambivalent entre télétravail et "
                                     "productivité.",
            "main_research_question": "Dans quelle mesure le télétravail influence-t-il la "
                                      "productivité des développeurs ?",
            "general_objective": "Analyser la relation entre le télétravail et la productivité des "
                                 "développeurs.",
            "specific_objectives": [
                "Identifier les conditions de travail associées à la productivité.",
                "Examiner l'effet de la coordination des équipes sur la productivité.",
            ],
        }
        payload.update(overrides)
        return HypothesesRequest(**payload)

    return make
