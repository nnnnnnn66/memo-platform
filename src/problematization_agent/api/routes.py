"""Endpoints HTTP de l'Agent Problématique. Aucune logique métier ici."""

from fastapi import APIRouter, HTTPException, Request

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..pipeline import campaign, input_controller
from ..schemas.input import ProblemRequest
from ..storage import audit, workspace

router = APIRouter()
log = get_logger("api")

AGENT_ID = "problematization_agent"
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


@router.post("/problematique/analyze")
async def analyze(request: Request, body: ProblemRequest) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    verifier_llm = getattr(request.app.state, "verifier_llm", None) or llm
    prepared = input_controller.prepare(body)
    session_id = prepared.session_id or ""

    def persist(name: str, payload) -> None:
        workspace.save(settings.workspace_dir, prepared.student_id, session_id, name, payload)

    try:
        result = campaign.run(prepared, settings, llm, verifier_llm, persist=persist)
    except PipelineError as exc:
        audit.log_event(settings.audit_db, session_id=session_id or "?",
                        agent_id=AGENT_ID, version=VERSION, status=exc.state.value,
                        errors=[exc.detail])
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    workspace.save(settings.workspace_dir, prepared.student_id, session_id,
                   "problematique_output", result.output)
    if result.verifier is not None:
        workspace.save(settings.workspace_dir, prepared.student_id, session_id,
                       "verifier_output", result.verifier)

    audit.log_event(settings.audit_db, session_id=session_id, agent_id=AGENT_ID,
                    version=VERSION, status=result.output.status.value,
                    validation_result=result.verifier_status, attempts=result.attempts,
                    llm_calls=result.llm_calls, external_requests=result.external_requests,
                    cache_hits=result.cache_hits,
                    documents_total=result.output.evidence.documents_total,
                    documents_read=result.documents_read,
                    statements_removed=result.statements_removed,
                    source_ids=result.source_ids,
                    gap_type=result.output.gap.type.value,
                    gap_check=result.output.gap.gap_check.result.value)

    return {
        "session_id": session_id,
        "status": result.output.status.value,
        "verifier_status": result.verifier_status,
        "attempts": result.attempts,
        "verifications": result.verifications,
        "llm_calls": result.llm_calls,
        "external_requests": result.external_requests,
        "cache_hits": result.cache_hits,
        "documents_total": result.output.evidence.documents_total,
        "documents_read": result.documents_read,
        "statements_removed": result.statements_removed,
        "gap": result.output.gap.type.value,
        "gap_check": result.output.gap.gap_check.result.value,
        "stages": result.stages,
        "injection_annotations": result.injection_annotations,
        "output": result.output.model_dump(mode="json"),
        "verifier": result.verifier.model_dump(mode="json") if result.verifier else None,
    }


@router.get("/problematique/{student_id}/{session_id}")
async def get_note(request: Request, student_id: str, session_id: str) -> dict:
    settings = request.app.state.settings
    data = workspace.load(settings.workspace_dir, student_id, session_id, "problematique_output")
    if data is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return data
