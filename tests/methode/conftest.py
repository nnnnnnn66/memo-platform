"""Fixtures des tests de l'Agent Méthodologie (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from methodology_agent.core.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    """Réglages de l'agent, workspace et journal isolés, bornes resserrées."""
    config = Settings()
    config.paths = dict(config.paths)
    config.paths["workspace"] = str(tmp_path / "ws")
    config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    config.limits = dataclasses.replace(
        config.limits,
        max_llm_calls=24,
        max_verification_retries=2,
        max_external_requests=0,
    )
    config.security = {"fail_on_injection": False}
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from methodology_agent.schemas.input import MethodologyRequest
        from methode_helpers import upstream_diagnostic

        payload = {
            "student_id": "etu-1",
            "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
            "discipline": "Sciences de gestion",
            "academic_level": "Master 2",
            "country": "Côte d'Ivoire",
            "geographical_area": "Abidjan",
            "study_period": "2020-2024",
            "target_population": "développeurs en télétravail",
            "research_context": "Entreprises de services numériques d'Abidjan.",
            "field_access": "Accès confirmé à deux entreprises par un réseau professionnel.",
            "available_data": "Questionnaires et entretiens à réaliser auprès des développeurs.",
            "available_resources": "Six mois de terrain, budget limité.",
            "available_tools": "Tableur et outil d'analyse de données.",
            "upstream_methodology_diagnostic": upstream_diagnostic(),
        }
        payload.setdefault("upstream_question", {
            "agent": "research_question_agent", "status": "validated",
            "main_research_question": "Dans quelle mesure le télétravail influence-t-il la "
                                      "productivité des développeurs ?",
            "secondary_research_questions": ["Quels facteurs modèrent cette relation ?"],
            "verification_result": {"verified": True, "verifier_status": "verified"},
        })
        payload.setdefault("upstream_objectives", {
            "agent": "research_objectives_agent", "status": "validated",
            "general_objective": "Analyser la relation entre le télétravail et la productivité des "
                                 "développeurs.",
            "specific_objectives": ["Identifier les conditions de travail associées à la "
                                    "productivité.",
                                    "Examiner l'effet de la coordination des équipes."],
            "verification_result": {"verified": True, "verifier_status": "verified"},
        })
        payload.update(overrides)
        return MethodologyRequest(**payload)

    return make
