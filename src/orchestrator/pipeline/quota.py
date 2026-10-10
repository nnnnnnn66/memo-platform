"""Quota quotidien par étudiant — protection du portefeuille du porteur.

Sans quota, une plateforme ouverte à plusieurs étudiants épuise le solde du modèle en quelques
heures. Le contrôle se fait **AVANT** l'appel à l'agent : refuser après coup n'aurait servi à rien.
"""

import datetime
import pathlib

from ..core.errors import EtatErreur, OrchestratorError
from ..storage import state


def jour_courant() -> str:
    return datetime.date.today().isoformat()


def restant(chemin_etat: pathlib.Path, etudiant: str, maximum: int, jour: str | None = None) -> int:
    utilisees = state.quota_du_jour(chemin_etat, etudiant, jour or jour_courant())
    return max(0, maximum - utilisees)


def verifier(chemin_etat: pathlib.Path, etudiant: str, maximum: int,
             jour: str | None = None) -> int:
    """Vérifie le quota SANS le consommer (consultation, affichage)."""
    return restant(chemin_etat, etudiant, maximum, jour)


def consommer(chemin_etat: pathlib.Path, etudiant: str, maximum: int,
              jour: str | None = None) -> int:
    """Consomme une analyse. Lève si le quota est atteint — jamais de dépassement silencieux."""
    reference = jour or jour_courant()
    if restant(chemin_etat, etudiant, maximum, reference) <= 0:
        raise OrchestratorError(
            EtatErreur.QUOTA_DEPASSE,
            f"Limite quotidienne atteinte ({maximum} analyses par jour). "
            "Tu pourras reprendre demain : ton dossier est conservé.",
            f"quota {maximum}/jour atteint pour {etudiant} le {reference}")
    return state.incrementer_quota(chemin_etat, etudiant, reference)
