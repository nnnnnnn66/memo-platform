"""Fixtures des tests de l'Agent 13 (aucun réseau, aucun coût)."""

import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from research_coherence_verifier.core.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    config = Settings()
    config.paths = dict(config.paths)
    config.paths["workspace"] = str(tmp_path / "ws")
    config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    config.limits = dataclasses.replace(
        config.limits, max_llm_calls=16, max_verification_retries=2, max_external_requests=0)
    config.security = {"fail_on_injection": False}
    return config


@pytest.fixture
def request_factory():
    def make(**overrides):
        from coherence_helpers import dossier_complet

        from research_coherence_verifier.schemas.input import CoherenceRequest

        payload = dossier_complet()
        payload.update(overrides)
        return CoherenceRequest(**payload)

    return make
