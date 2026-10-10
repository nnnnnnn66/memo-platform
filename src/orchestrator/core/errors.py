"""Erreurs propres de l'orchestrateur : chaque refus doit être EXPLICABLE à l'étudiant."""

from enum import Enum


class EtatErreur(str, Enum):
    ETAPE_INCONNUE = "ETAPE_INCONNUE"
    ETAPE_NON_AUTORISEE = "ETAPE_NON_AUTORISEE"
    DECISION_INVALIDE = "DECISION_INVALIDE"
    QUOTA_DEPASSE = "QUOTA_DEPASSE"
    AGENT_INDISPONIBLE = "AGENT_INDISPONIBLE"
    AGENT_EN_ECHEC = "AGENT_EN_ECHEC"
    SORTIE_AMONT_MANQUANTE = "SORTIE_AMONT_MANQUANTE"
    DOSSIER_INCONNU = "DOSSIER_INCONNU"
    ENTREE_INVALIDE = "ENTREE_INVALIDE"


class OrchestratorError(Exception):
    """Erreur portée à l'étudiant en langage clair.

    `message_etudiant` est rédigé pour être AFFICHÉ tel quel : jamais un code technique, jamais
    une trace d'exécution, jamais un nom de fichier interne.
    """

    def __init__(self, etat: EtatErreur, message_etudiant: str, detail: str = ""):
        super().__init__(f"{etat.value}: {detail or message_etudiant}")
        self.etat = etat
        self.message_etudiant = message_etudiant
        self.detail = detail or message_etudiant

    def as_dict(self) -> dict:
        return {"error": self.etat.value, "message": self.message_etudiant,
                "detail": self.detail}
