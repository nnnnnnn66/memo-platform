"""Fixtures des tests de l'Agent Conclusion (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from research_conclusion_agent.core.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    config = Settings()
    config.paths = dict(config.paths)
    config.paths["workspace"] = str(tmp_path / "ws")
    config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    config.limits = dataclasses.replace(
        config.limits, max_llm_calls=22, max_verification_retries=2, max_external_requests=0)
    config.security = {"fail_on_injection": False}
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from conclusion_helpers import upstream_question, upstream_results

        from research_conclusion_agent.schemas.input import ConclusionRequest

        payload = {
            "student_id": "etu-1",
            "subject_text": "Le télétravail et la productivité des développeurs d'Abidjan, 2020-2024",
            "discipline": "Sciences de gestion",
            "academic_level": "Master 2",
            "upstream_question": upstream_question(),
            "upstream_results": upstream_results(),
        }
        payload.setdefault("upstream_objectives", {
            "agent": "research_objectives_agent", "status": "validated",
            "general_objective": "Analyser la relation entre le télétravail et la productivité.",
            "specific_objectives": ["Décrire l'intensité du télétravail déclarée."],
            "verification_result": {"verified": True, "verifier_status": "verified"},
        })
        payload.setdefault("upstream_methodology", {
            "agent": "methodology_agent", "status": "validated",
            "document_status": "valide",
            "protocol": {"approche": "quantitative", "type_recherche": "explicative",
                         "strategie": "enquete", "terrain": "ESN d'Abidjan"},
            "verification_result": {"verified": True, "verifier_status": "verified"},
            "student_validation": {"decision": "accepted", "comment": ""},
        })
        payload.setdefault("upstream_hypotheses", {
            "agent": "research_hypotheses_agent", "status": "validated",
            "hypotheses_decision": "HYPOTHESES_RECOMMENDED",
            "research_hypotheses": [
                {"id": "H1", "formulation": "L'intensité du télétravail est associée à la "
                                            "productivité déclarée."}],
            "verification_result": {"verified": True, "verifier_status": "verified"},
        })
        payload.update(overrides)
        return ConclusionRequest(**payload)

    return make
