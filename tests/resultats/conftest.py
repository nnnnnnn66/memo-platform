"""Fixtures des tests de l'Agent Résultats et analyse (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from research_results_analysis_agent.core.config import Settings  # noqa: E402

from resultats_helpers import CSV  # noqa: E402,F401


@pytest.fixture
def settings(tmp_path):
    config = Settings()
    config.paths = dict(config.paths)
    config.paths["workspace"] = str(tmp_path / "ws")
    config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    config.limits = dataclasses.replace(
        config.limits, max_llm_calls=24, max_verification_retries=2, max_external_requests=0)
    config.security = {"fail_on_injection": False}
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from resultats_helpers import upstream_methodology

        from research_results_analysis_agent.schemas.input import Dataset, ResultsAnalysisRequest

        payload = {
            "student_id": "etu-1",
            "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
            "discipline": "Sciences de gestion",
            "academic_level": "Master 2",
            "data_origin": "Enquête par questionnaire auprès de six développeurs.",
            "data_period": "2024",
            "collection_notes": "Questionnaires administrés en présentiel.",
            "datasets": [Dataset(nom="enquete-developpeurs", format="csv", contenu=CSV,
                                 source="Questionnaire administré", periode="2024",
                                 description="Réponses de six développeurs.")],
            "upstream_methodology": upstream_methodology(),
        }
        payload.setdefault("upstream_objectives", {
            "agent": "research_objectives_agent", "status": "validated",
            "general_objective": "Analyser la relation entre le télétravail et la productivité.",
            "specific_objectives": ["Décrire l'intensité du télétravail déclarée."],
            "verification_result": {"verified": True, "verifier_status": "verified"},
        })
        payload.setdefault("upstream_question", {
            "agent": "research_question_agent", "status": "validated",
            "main_research_question": "Dans quelle mesure le télétravail influence-t-il la "
                                      "productivité déclarée des développeurs ?",
            "verification_result": {"verified": True, "verifier_status": "verified"},
        })
        payload.update(overrides)
        return ResultsAnalysisRequest(**payload)

    return make
