"""Test 29 — isolation : un étudiant ne peut pas atteindre les données d'un autre."""

import pathlib

import yaml

from research_problem_agent.core.sessions import session_dir
from research_problem_agent.storage import workspace

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def test_espaces_de_travail_separes(settings):
    ws = settings.workspace_dir
    workspace.save(ws, "etu-1", "session-a", "problem_output", {"x": 1})
    workspace.save(ws, "etu-2", "session-a", "problem_output", {"x": 2})

    assert workspace.load(ws, "etu-1", "session-a", "problem_output") == {"x": 1}
    assert workspace.load(ws, "etu-2", "session-a", "problem_output") == {"x": 2}
    assert workspace.load(ws, "etu-1", "session-b", "problem_output") is None


def test_tentative_de_traversee_de_chemin_neutre(settings):
    """Un identifiant hostile est neutralisé : pas de sortie du workspace."""
    path = session_dir(settings.workspace_dir, "../../etc", "../../passwd")
    assert ".." not in str(path)
    assert str(settings.workspace_dir) in str(path)


def test_le_workspace_de_l_agent_sujet_n_est_pas_partage():
    """Cadre propre à l'agent : artefacts, audit et cache distincts de ceux de l'Agent Sujet."""
    from research_problem_agent.core.config import Settings

    agent_probleme = Settings().paths
    sujet = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[2] / "config" / "settings.yaml")
        .read_text(encoding="utf-8"))["paths"]

    assert agent_probleme["audit_db"] == "workspace/audit-probleme.db"
    assert agent_probleme["cache_db"] == "workspace/sources-cache.db"
    assert agent_probleme["audit_db"] != sujet["audit_db"]
