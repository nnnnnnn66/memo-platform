"""Endpoints HTTP de l'orchestrateur.

C'est l'API INTERNE de la plateforme : elle sera consommée par le site web, jamais directement par
l'étudiant. Aucune logique métier ici — les routes traduisent et délèguent.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from ..core.errors import OrchestratorError
from ..pipeline import campaign

router = APIRouter()


class CreationDossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sujet: str
    sujet_contexte: dict = {}


class DecisionEtudiant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    commentaire: str = ""


def _erreur(erreur: OrchestratorError) -> HTTPException:
    """Traduit une erreur métier en réponse HTTP exploitable par la plateforme."""
    statut = {("ETAPE_NON_AUTORISEE"): 409, "QUOTA_DEPASSE": 429,
              "DOSSIER_INCONNU": 404}.get(erreur.etat.value, 400)
    return HTTPException(status_code=statut, detail=erreur.as_dict())


@router.get("/health")
async def health() -> dict:
    return {"agent": "orchestrator", "version": "1.0", "status": "ok"}


@router.post("/dossiers/{etudiant}/{session}")
async def creer_dossier(request: Request, etudiant: str, session: str,
                        body: CreationDossier) -> dict:
    """Ouvre un dossier pour un étudiant (idempotent : un dossier existant n'est jamais écrasé)."""
    settings = request.app.state.settings
    try:
        return campaign.creer_dossier(settings, etudiant, session, body.sujet,
                                      body.sujet_contexte)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.get("/dossiers/{etudiant}/{session}")
async def etat_du_dossier(request: Request, etudiant: str, session: str) -> dict:
    """Où en est l'étudiant : étape ouverte, statut, quota restant, avancement."""
    settings = request.app.state.settings
    try:
        return campaign.etat(settings, etudiant, session)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.post("/dossiers/{etudiant}/{session}/etape")
async def lancer_etape(request: Request, etudiant: str, session: str) -> dict:
    """Lance l'étape ouverte (le parcours décide laquelle — jamais l'appelant)."""
    settings = request.app.state.settings
    try:
        return campaign.lancer_etape(settings, etudiant, session)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.post("/dossiers/{etudiant}/{session}/decision")
async def decider(request: Request, etudiant: str, session: str,
                  body: DecisionEtudiant) -> dict:
    """Enregistre la décision humaine — seule voie d'accès à l'étape suivante."""
    settings = request.app.state.settings
    try:
        return campaign.decider(settings, etudiant, session, body.decision, body.commentaire)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur
