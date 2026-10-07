"""Fixtures des tests de l'Agent Problème (aucun réseau, aucun coût)."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from research_problem_agent.core.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    """Réglages de l'agent, workspace et caches isolés dans un dossier temporaire."""
    config = Settings()
    config.paths = dict(config.paths)
    config.paths["workspace"] = str(tmp_path / "ws")
    config.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    config.paths["cache_db"] = str(tmp_path / "ws" / "cache.db")
    config.sources = dict(config.sources)
    return config


@pytest.fixture
def offline(settings):
    """Mode sans recherche externe : le pipeline ne fait AUCUN appel réseau."""
    settings.sources["enabled"] = False
    return settings
