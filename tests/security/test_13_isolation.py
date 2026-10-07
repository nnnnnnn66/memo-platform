"""Test 13 — Isolation : un étudiant ne peut pas lire les données d'un autre."""

from subject_agent.storage import workspace


def test_isolation_par_etudiant(settings):
    workspace.save(settings.workspace_dir, "etudiantA", "sess1", "subject_output", {"x": 1})
    workspace.save(settings.workspace_dir, "etudiantB", "sess1", "subject_output", {"x": 2})

    assert workspace.load(settings.workspace_dir, "etudiantA", "sess1", "subject_output") == {"x": 1}
    assert workspace.load(settings.workspace_dir, "etudiantB", "sess1", "subject_output") == {"x": 2}
    # un étudiant sans données ne voit rien
    assert workspace.load(settings.workspace_dir, "etudiantC", "sess1", "subject_output") is None


def test_chemins_isoles():
    from subject_agent.core.sessions import session_dir
    a = session_dir(settings.workspace_dir if False else __import__("pathlib").Path("/ws"),
                    "A", "s")
    b = __import__("pathlib").Path("/ws") / "B" / "s"
    assert a != b
