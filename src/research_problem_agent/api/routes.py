"""Endpoints HTTP de l'Agent Problème de recherche. Aucune logique métier ici."""

from fastapi import APIRouter, HTTPException, Request

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..pipeline import input_controller, orchestrator, interrogation
from ..schemas.input import ProblemRequest, QuestionRequest
from ..storage import audit, workspace

router = APIRouter()
log = get_logger("api")

AGENT_ID = "research_problem_agent"
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
    'agent': 'research_problem_agent',
    'etape': 2,
    'nom': 'Problème de recherche',
    'role': 'Formule le problème de recherche et mène une recherche documentaire déterministe.',
    'capacites': ['probleme_recherche', 'recherche_documentaire', 'clarification'],
    'entrees_requises': ['upstream_subject'],
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

@router.post("/problem/analyze")
async def analyze(request: Request, body: ProblemRequest) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    verifier_llm = getattr(request.app.state, "verifier_llm", None) or llm
    prepared = input_controller.prepare(body)

    try:
        result = orchestrator.analyze_problem(prepared, settings, llm, verifier_llm)
    except PipelineError as exc:
        audit.log_event(settings.audit_db, session_id=prepared.session_id or "?",
                        agent_id=AGENT_ID, version=VERSION,
                        status=exc.state.value, errors=[exc.detail])
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                   "problem_output", result.output)
    if result.verifier is not None:
        workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                       "verifier_output", result.verifier)
    if result.source_set is not None:
        workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                       "sources", result.source_set.to_dict())
    audit.log_event(settings.audit_db, session_id=prepared.session_id,
                    agent_id=AGENT_ID, version=VERSION,
                    status=result.output.status.value,
                    validation_result=result.verifier_status,
                    attempts=result.attempts,
                    consumption=llm.calls,
                    external_requests=result.external_requests,
                    cache_hits=result.cache_hits,
                    providers_used=result.source_set.providers_used if result.source_set else [],
                    source_ids=result.source_ids)

    return {
        "session_id": prepared.session_id,
        "status": result.output.status.value,
        "verifier_status": result.verifier_status,
        "attempts": result.attempts,
        "verifications": result.verifications,
        "external_requests": result.external_requests,
        "cache_hits": result.cache_hits,
        "providers_used": result.source_set.providers_used if result.source_set else [],
        "providers_failed": result.source_set.providers_failed if result.source_set else [],
        "injection_annotations": result.injection_annotations,
        "output": result.output.model_dump(mode="json"),
        "verifier": result.verifier.model_dump(mode="json") if result.verifier else None,
    }


@router.get("/problem/{student_id}/{session_id}")
async def get_problem(request: Request, student_id: str, session_id: str) -> dict:
    settings = request.app.state.settings
    data = workspace.load(settings.workspace_dir, student_id, session_id, "problem_output")
    if data is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return data

@router.post("/problem/question")
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
            nom_etape="Problème", libelle_etape="Identification et formulation du problème de recherche")
    except PipelineError as exc:
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    audit.log_event(settings.audit_db, session_id=body.session_id or "?",
                    agent_id="research_problem_agent", version="1.0", status="question_answered",
                    consumption=llm.calls)
    return {"agent": "research_problem_agent", "nom": "Problème", "question": body.question, **reponse}
