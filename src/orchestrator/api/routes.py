"""Endpoints HTTP de l'orchestrateur.

C'est l'API INTERNE de la plateforme : elle sera consommée par le site web, jamais directement par
l'étudiant. Aucune logique métier ici — les routes traduisent et délèguent.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, field_validator

from ..core.errors import OrchestratorError
from ..pipeline import campaign, interrogation, registry

router = APIRouter()


class CreationDossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sujet: str
    sujet_contexte: dict = {}

    @field_validator("sujet_contexte", mode="before")
    @classmethod
    def _contexte_tolerant(cls, valeur):
        """Le contexte d'un étudiant est naturellement du TEXTE.

        Le site envoie une chaîne, et il a raison : elle est donc acceptée et encapsulée en objet
        (`{"contexte": "…"}`) pour que le pipeline continue de recevoir un objet. Un OBJET déjà
        formé est gardé tel quel. Toute autre forme (liste, nombre…) reste REFUSÉE : on ne devine
        jamais ce que l'appelant a voulu dire.
        """
        if valeur is None:
            return {}
        if isinstance(valeur, str):
            texte = valeur.strip()
            return {"contexte": texte} if texte else {}
        return valeur


class DecisionEtudiant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    commentaire: str = ""


class QuestionLibre(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str


def _erreur(erreur: OrchestratorError) -> HTTPException:
    """Traduit une erreur métier en réponse HTTP exploitable par la plateforme."""
    statut = {("ETAPE_NON_AUTORISEE"): 409, "QUOTA_DEPASSE": 429,
              "DOSSIER_INCONNU": 404}.get(erreur.etat.value, 400)
    return HTTPException(status_code=statut, detail=erreur.as_dict())


@router.get("/health")
async def health() -> dict:
    return {"agent": "orchestrator", "version": "1.0", "status": "ok"}


@router.get("/parcours")
async def parcours(request: Request) -> dict:
    """La carte du parcours, montrable PUBLIQUEMENT : les étapes et leurs libellés.

    Aucune donnée d'étudiant, aucun nom d'agent, aucune adresse de service : seulement ce que la
    plateforme annonce d'elle-même. C'est ce que la page d'accueil affiche à un visiteur.
    """
    settings = request.app.state.settings
    return {
        "etapes": [{"numero": etape.numero, "position": rang + 1, "libelle": etape.libelle,
                    "resume": etape.resume}
                   for rang, etape in enumerate(settings.etapes)]}


@router.get("/agents")
async def agents(request: Request, forcer: bool = False) -> dict:
    """Qui sont les agents, que savent-ils faire, sont-ils en ligne ?

    L'orchestrateur ne se contente pas de connaître des adresses : il INTERROGE chaque agent
    (`/health` pour la disponibilité, `/capabilities` pour l'identité et les capacités) et
    SIGNALE tout désaccord entre ce qu'un agent déclare et ce que la carte du parcours prévoit.
    """
    settings = request.app.state.settings
    fiches = registry.registre(settings, forcer=forcer)
    return {
        "total": len(fiches),
        "en_ligne": sum(1 for fiche in fiches if fiche["en_ligne"]),
        "agents": fiches,
    }


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


@router.post("/dossiers/{etudiant}/{session}/etapes/{n}/reprendre")
async def reprendre_etape(request: Request, etudiant: str, session: str, n: int) -> dict:
    """REPRENDRE une étape DÉJÀ FRANCHIE : l'étudiant reçoit de nouvelles données, ou veut corriger.

    Une étape validée était définitive : y revenir exigeait d'intervenir dans la base. La reprise la
    rouvre et invalide ses étapes aval (voir `campaign.reprendre` pour le comportement et pourquoi).
    Aucun quota n'est consommé : rien ne part vers un agent, on rouvre seulement le parcours.
    """
    settings = request.app.state.settings
    try:
        return campaign.reprendre(settings, etudiant, session, n)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.get("/dossiers/{etudiant}/{session}/etape")
async def detail_etape(request: Request, etudiant: str, session: str, n: int = 0) -> dict:
    """Le détail d'une étape pour l'affichage : proposition, inconnues, limites, questions,
    verdict — c'est ce que le site montre à l'étudiant, sans rien réécrire."""
    settings = request.app.state.settings
    try:
        return campaign.etape_detail(settings, etudiant, session, n or None)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.post("/dossiers/{etudiant}/{session}/question")
async def question_libre(request: Request, etudiant: str, session: str,
                         body: QuestionLibre) -> dict:
    """L'étudiant pose une question quelconque : l'orchestrateur DÉSIGNE l'étape qui la porte.

    C'est le seul composant qui connaît la carte du parcours — donc le seul capable de dire à quel
    agent une question appartient. L'étudiant n'a jamais à connaître les agents.
    """
    settings = request.app.state.settings
    try:
        return campaign.question(settings, etudiant, session, body.question)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.get("/dossiers/{etudiant}/{session}/documents")
async def documents_du_dossier(request: Request, etudiant: str, session: str) -> dict:
    """Les textes retrouvés pour l'étudiant (manifeste normalisé, prêt à afficher)."""
    settings = request.app.state.settings
    try:
        return campaign.documents(settings, etudiant, session)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur


@router.get("/dossiers/{etudiant}/{session}/documents/{doc_id}/fichier")
async def fichier_du_document(request: Request, etudiant: str, session: str, doc_id: str):
    """Le texte intégral d'un document (accès ouvert uniquement), relayé tel quel."""
    from fastapi.responses import Response

    settings = request.app.state.settings
    try:
        contenu = campaign.fichier_document(settings, etudiant, session, doc_id)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur
    return Response(content=contenu, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{doc_id}.pdf"'})


@router.get("/dossiers/{etudiant}/{session}/bibliographie")
async def bibliographie_du_dossier(request: Request, etudiant: str, session: str,
                                   format: str = "bibtex"):
    """Export bibliographique relayé tel quel (BibTeX, RIS ou CSV)."""
    from fastapi.responses import Response

    settings = request.app.state.settings
    try:
        contenu = campaign.bibliographie(settings, etudiant, session, format)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur
    extensions = {"bibtex": ("application/x-bibtex", "bib"), "ris":
                  ("application/x-research-info-systems", "ris"), "csv": ("text/csv", "csv")}
    type_mime, extension = extensions.get(format, ("application/octet-stream", "txt"))
    return Response(content=contenu, media_type=type_mime,
                    headers={"Content-Disposition":
                             f'attachment; filename="bibliographie.{extension}"'})

@router.post("/dossiers/{etudiant}/{session}/interroger")
async def interroger(request: Request, etudiant: str, session: str,
                     body: QuestionLibre) -> dict:
    """L'étudiant pose une question LIBRE : l'orchestrateur désigne l'étape et SON AGENT répond.

    Différence avec `/question` (qui ne fait que désigner) : ici la réponse existe. L'agent
    compétent est appelé, il répond dans son périmètre à partir du dossier réel, et si la question
    appartient en fait à une AUTRE étape, l'orchestrateur appelle cet agent-là.

    Sans effet de bord : aucune écriture de dossier, aucun quota consommé, aucune campagne lancée.
    """
    settings = request.app.state.settings
    try:
        return interrogation.interroger(settings, etudiant, session, body.question)
    except OrchestratorError as erreur:
        raise _erreur(erreur) from erreur
