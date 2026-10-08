"""Les agents doivent lire `~/.hermes/.env`, l'emplacement DOCUMENTÉ des secrets.

Régression constatée en vérifiant la clé OpenAlex : les quatre agents ne chargeaient que le
`.env` **du projet** (qui n'existe pas), jamais le fichier Hermes. Une clé posée dans
`~/.hermes/.env` — comme le demande le README — n'était donc jamais lue : la consigne ne
fonctionnait pas en exécution normale. Le fichier du projet reste prioritaire s'il existe.
"""

import os

import pytest

NOM_VARIABLE = "CLE_FACTICE_POUR_TEST"


def _classes():
    from literature_review_agent.core.config import Settings as S3
    from problematization_agent.core.config import Settings as S4
    from research_problem_agent.core.config import Settings as S2
    from subject_agent.core.config import Settings as S1

    return {"agent1_sujet": S1, "agent2_probleme": S2,
            "agent3_litterature": S3, "agent4_problematique": S4}


@pytest.mark.parametrize("nom", sorted(_classes()))
def test_secret_lu_depuis_hermes_home(tmp_path, monkeypatch, nom):
    (tmp_path / ".env").write_text(f"{NOM_VARIABLE}=valeur-de-test\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv(NOM_VARIABLE, raising=False)

    _classes()[nom]()

    assert os.environ.get(NOM_VARIABLE) == "valeur-de-test"


def test_fichier_du_projet_prioritaire(tmp_path, monkeypatch):
    """Si le projet fournit la variable, c'est elle qui gagne (load_dotenv n'écrase pas)."""
    from subject_agent.core.config import Settings, ROOT

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / ".env").write_text(f"{NOM_VARIABLE}=depuis-hermes\n", encoding="utf-8")
    monkeypatch.delenv(NOM_VARIABLE, raising=False)
    monkeypatch.setenv(NOM_VARIABLE, "deja-definie")
    try:
        Settings(ROOT)
        assert os.environ.get(NOM_VARIABLE) == "deja-definie"
    finally:
        assert ROOT.exists()
