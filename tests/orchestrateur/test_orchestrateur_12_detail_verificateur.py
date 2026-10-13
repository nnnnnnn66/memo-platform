"""Le pourquoi d'une vérification qui échoue ne doit jamais être perdu.

Défaut constaté en répétition générale (sujet neuf, étape 1) : l'agent renvoyait bien son
vérificateur (verdict + corrections demandées), mais l'orchestrateur ne recopiait que le mot
« verification_failed ». L'étudiant lisait donc « le contrôle indépendant n'a pas pu aboutir »
sans aucune raison, et personne ne pouvait savoir ce qui bloquait.

Règle : l'orchestrateur TRANSPORTE le détail du vérificateur tel quel, sans l'interpréter.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from orchestrator.pipeline import campaign  # noqa: E402


def test_le_detail_du_verificateur_est_transporte():
    """Un vérificateur qui demande des corrections doit être visible dans la réponse de l'étape."""
    reponse = {
        "verifier_status": "corrections_requested",
        "output": {"status": "ready_for_verification"},
        "verifier": {
            "verdict": "corrections_requested",
            "corrections": ["Préciser le périmètre géographique", "Justifier la période"],
            "motif": "Le périmètre reste trop large pour être opérationnel.",
        },
    }

    detail = campaign.detail_du_verificateur(reponse)

    assert detail is not None, "le détail du vérificateur a été perdu"
    assert detail["verdict"] == "corrections_requested"
    assert detail["corrections"] == ["Préciser le périmètre géographique",
                                     "Justifier la période"]
    assert "trop large" in detail["motif"]


def test_une_reponse_sans_verificateur_ne_casse_rien():
    """Toutes les étapes n'ont pas de vérificateur : l'absence doit rester propre."""
    assert campaign.detail_du_verificateur({"output": {}}) is None
    assert campaign.detail_du_verificateur({"verificateur": {}}) is None
