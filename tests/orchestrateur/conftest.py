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
    """Configuration réelle, état et espace isolés dans un dossier temporaire.

    `validation_automatique` est FORCÉE à False : la configuration de production est en mode
    autonome (consigne du porteur), mais les tests du mécanisme de décision humaine doivent pouvoir
    l'exercer. Le mode autonome a ses propres tests (`test_orchestrateur_11_autonomie.py`), qui
    rallument l'interrupteur. Sans cela, un test dépendrait du réglage de production — et changer
    la production ferait tomber des tests qui ne parlent pas d'elle.
    """
    return dataclasses.replace(charger(), state_db=tmp_path / "etat.db", workspace_dir=tmp_path,
                               validation_automatique=False)


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
