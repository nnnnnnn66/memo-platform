"""Aides de test de l'orchestrateur : AUCUN réseau, AUCUN modèle, AUCUN agent lancé.

Un agent simulé enregistre ce qu'il reçoit — c'est ainsi qu'on vérifie que le pont entre étapes
transmet bien des sorties RÉELLES et non un payload fabriqué.
"""

import dataclasses
import pathlib
import sys

import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
if str(RACINE / "src") not in sys.path:
    sys.path.insert(0, str(RACINE / "src"))

from orchestrator.core.config import charger  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    """Configuration réelle, état et espace isolés dans un dossier temporaire."""
    return dataclasses.replace(charger(), state_db=tmp_path / "etat.db", workspace_dir=tmp_path)


class AgentSimule:
    """Agent de test : répond sans réseau et sans modèle, et retient chaque appel reçu."""

    def __init__(self, verdict="verified", resultat=None):
        self.appels: list[tuple[str, dict]] = []
        self.verdict = verdict
        self.resultat = resultat or {"status": "awaiting_human_validation",
                                     "proposition": "proposition simulée"}

    def __call__(self, url: str, charge: dict) -> dict:
        self.appels.append((url, charge))
        return {"output": self.resultat, "verifier_status": self.verdict}

    @property
    def derniere_entree(self) -> dict:
        return self.appels[-1][1] if self.appels else {}


@pytest.fixture
def agent():
    return AgentSimule()


def avancer(settings, etudiant, session, agent, nombre=1, decision="accepted"):
    """Fait avancer un dossier de `nombre` étapes (lancer puis décider), pour les tests."""
    from orchestrator.pipeline import campaign

    for _ in range(nombre):
        campaign.lancer_etape(settings, etudiant, session, transport=agent)
        campaign.decider(settings, etudiant, session, decision, transport=agent)
    return campaign.etat(settings, etudiant, session)
