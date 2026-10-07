"""Fixtures et aides de test (zéro coût : LLM simulé déterministe)."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest  # noqa: E402

from subject_agent.core.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    s = Settings()
    s.paths = dict(s.paths)
    s.paths["workspace"] = str(tmp_path / "ws")
    s.paths["audit_db"] = str(tmp_path / "ws" / "audit.db")
    return s
