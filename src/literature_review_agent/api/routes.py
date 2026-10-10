"""Endpoints HTTP de l'Agent Revue de littérature. Aucune logique métier ici."""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from ..bibliography import export
from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..pipeline import campaign, input_controller
from ..schemas.input import CampaignRequest
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


@router.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": AGENT_ID, "version": VERSION}


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
