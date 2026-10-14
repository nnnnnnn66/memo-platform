"""Endpoints HTTP de l'Agent Revue de littérature. Aucune logique métier ici."""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from ..bibliography import export
from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..pipeline import campaign, input_controller, interrogation
from ..schemas.input import CampaignRequest, QuestionRequest
from ..storage import audit, workspace

router = APIRouter()
log = get_logger("api")

AGENT_ID = "literature_review_agent"
VERSION = "1.0"

_STATUS_MAP = {
    ErrorState.INVALID_INPUT: 422,
    ErrorState.MISSING_INFORMATION: 422,
    ErrorState.RESOURCE_LIMIT: 413,
    ErrorState.SECURITY_VIOLATION: 400,
    ErrorState.TIMEOUT: 504,
    ErrorState.OUTPUT_SCHEMA_ERROR: 502,
    ErrorState.TOOL_ERROR: 502,
    ErrorState.VERIFICATION_FAILED: 502,
}


_CAPACITES = {
    'agent': 'literature_review_agent',
    'etape': 3,
    'nom': 'Revue de littérature',
    'role': 'Interroge les fournisseurs scientifiques, télécharge et LIT les textes intégraux, sélectionne le corpus, ancre les citations et produit la bibliographie.',
    'capacites': ['revue_litterature', 'recherche_documentaire', 'telechargement_pdf', 'lecture_pdf', 'bibliographie', 'matrice_comparative', 'synthese_critique'],
    'entrees_requises': ['upstream_problem', 'upstream_subject'],
    'necessite_reseau': True,
    'portillon_humain': True,
    'version': '1.0',
}


@router.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": AGENT_ID, "version": VERSION}



@router.get("/capabilities")
async def capabilities() -> dict:
    """Ce que cet agent SAIT FAIRE, et ce dont il a besoin pour travailler.

    Répond aux quatre questions que l'orchestrateur doit pouvoir poser :
    WHO ARE YOU (`agent`) — WHAT CAN YOU DO (`capacites`) — WHAT DO YOU NEED (`entrees_requises`)
    — ARE YOU ONLINE (`/health`). Déclaration en DONNÉES : l'orchestrateur la LIT, il ne la devine pas.
    """
    return _CAPACITES

@router.post("/literature/review")
async def review(request: Request, body: CampaignRequest) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    verifier_llm = getattr(request.app.state, "verifier_llm", None) or llm
    prepared = input_controller.prepare(body)

    def persist(name: str, payload) -> None:
        workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                       name, payload)

    try:
        result = campaign.run(prepared, settings, llm, verifier_llm, persist=persist)
    except PipelineError as exc:
        audit.log_event(settings.audit_db, session_id=prepared.session_id or "?",
                        agent_id=AGENT_ID, version=VERSION, status=exc.state.value,
                        errors=[exc.detail])
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                   "review_output", result.output)
    if result.verifier is not None:
        workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                       "verifier_output", result.verifier)
    audit.log_event(settings.audit_db, session_id=prepared.session_id, agent_id=AGENT_ID,
                    version=VERSION, status=result.output.status.value,
                    validation_result=result.verifier_status, attempts=result.attempts,
                    llm_calls=result.llm_calls, external_requests=result.external_requests,
                    cache_hits=result.cache_hits,
                    providers_used=result.output.corpus.providers_used,
                    documents_count=result.output.corpus.documents_count,
                    downloaded_count=result.downloaded_count, source_ids=result.source_ids)

    return {
        "session_id": prepared.session_id,
        "status": result.output.status.value,
        "verifier_status": result.verifier_status,
        "attempts": result.attempts,
        "verifications": result.verifications,
        "llm_calls": result.llm_calls,
        "external_requests": result.external_requests,
        "cache_hits": result.cache_hits,
        "documents_count": result.output.corpus.documents_count,
        "downloaded_count": result.downloaded_count,
        "dropped_claims": result.dropped_claims,
        "stages": result.stages,
        "injection_annotations": result.injection_annotations,
        "output": result.output.model_dump(mode="json"),
        "verifier": result.verifier.model_dump(mode="json") if result.verifier else None,
    }


@router.get("/literature/{student_id}/{session_id}")
async def get_review(request: Request, student_id: str, session_id: str) -> dict:
    settings = request.app.state.settings
    data = workspace.load(settings.workspace_dir, student_id, session_id, "review_output")
    if data is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return data


@router.get("/literature/{student_id}/{session_id}/bibliographie")
async def download_bibliography(request: Request, student_id: str, session_id: str,
                                format: str = "bibtex") -> Response:
    """Bibliographie exportable (BibTeX, RIS, CSV).

    Livrable du document d'opérationnalisation : l'étudiant doit pouvoir réutiliser les références.
    L'export est une RECOPIE déterministe des métadonnées réellement collectées : aucun champ
    inventé, aucun appel réseau, aucun modèle.
    """
    settings = request.app.state.settings
    data = workspace.load(settings.workspace_dir, student_id, session_id, "review_output")
    if data is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    documents = ((data.get("corpus") or {}).get("documents") or [])
    nom, mime, contenu = export.export(documents, format)
    return Response(content=contenu, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})


@router.get("/literature/{student_id}/{session_id}/documents")
async def list_documents(request: Request, student_id: str, session_id: str) -> dict:
    """Manifeste des documents téléchargés, avec leurs liens de téléchargement locaux."""
    settings = request.app.state.settings
    directory = workspace.documents_dir(settings.workspace_dir, student_id, session_id)
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("entries", []):
        entry["download_url"] = (
            f"/literature/{student_id}/{session_id}/documents/{entry['doc_id']}/file"
        )
    return manifest


@router.get("/literature/{student_id}/{session_id}/documents/{doc_id}/file")
async def download_document(request: Request, student_id: str, session_id: str, doc_id: str):
    """Renvoie le PDF téléchargé pour l'étudiant (accès ouvert uniquement)."""
    import json

    settings = request.app.state.settings
    directory = workspace.documents_dir(settings.workspace_dir, student_id, session_id)
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("entries", []):
        if entry.get("doc_id") == doc_id:
            path = directory / str(entry.get("file_name"))
            if not path.exists():
                raise HTTPException(status_code=404, detail={"error": "FILE_MISSING"})
            return FileResponse(path, media_type="application/pdf",
                                filename=str(entry.get("file_name")))
    raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})

@router.post("/literature/question")
async def question(request: Request, body: QuestionRequest) -> dict:
    """Répondre à une question de l'étudiant DANS le périmètre de cet agent.

    Demande du porteur : l'agent choisi répond à toutes les requêtes ; s'il ne sait pas, il le DIT et
    nomme l'étape compétente — c'est ce signalement qui permet à l'orchestrateur de faire répondre le
    bon agent, au lieu de laisser inventer. Répondre n'écrit rien dans le dossier et ne consomme pas
    une analyse.
    """
    settings = request.app.state.settings
    llm = request.app.state.llm
    try:
        reponse = interrogation.repondre(
            llm, body.question, contexte=body.contexte,
            nom_etape="Revue de littérature", libelle_etape="Revue de littérature et diagnostic")
    except PipelineError as exc:
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    audit.log_event(settings.audit_db, session_id=body.session_id or "?",
                    agent_id="literature_review_agent", version="1.0", status="question_answered",
                    llm_calls=llm.calls)
    return {"agent": "literature_review_agent", "nom": "Revue de littérature", "question": body.question, **reponse}
