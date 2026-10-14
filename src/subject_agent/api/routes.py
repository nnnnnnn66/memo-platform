"""Endpoints HTTP de l'Agent Sujet. Aucune logique métier ici."""

from fastapi import APIRouter, HTTPException, Request

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..pipeline import input_controller, orchestrator, interrogation
from ..schemas.input import QuestionRequest, SubjectRequest
from ..storage import audit, workspace

router = APIRouter()
log = get_logger("api")

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
    'agent': 'subject_agent',
    'etape': 1,
    'nom': 'Sujet',
    'role': 'Cadre le sujet de mémoire et détecte les informations manquantes (QUOI/QUI/OÙ/QUAND).',
    'capacites': ['sujet', 'cadrage', 'clarification'],
    'entrees_requises': [],
    'necessite_reseau': False,
    'portillon_humain': True,
    'version': '1.0',
}


@router.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "subject_agent", "version": "1.0"}



@router.get("/capabilities")
async def capabilities() -> dict:
    """Ce que cet agent SAIT FAIRE, et ce dont il a besoin pour travailler.

    Répond aux quatre questions que l'orchestrateur doit pouvoir poser :
    WHO ARE YOU (`agent`) — WHAT CAN YOU DO (`capacites`) — WHAT DO YOU NEED (`entrees_requises`)
    — ARE YOU ONLINE (`/health`). Déclaration en DONNÉES : l'orchestrateur la LIT, il ne la devine pas.
    """
    return _CAPACITES

@router.post("/subject/analyze")
async def analyze(request: Request, body: SubjectRequest) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    verifier_llm = getattr(request.app.state, "verifier_llm", None) or llm
    prepared = input_controller.prepare(body)

    try:
        result = orchestrator.analyze_subject(prepared, settings, llm, verifier_llm)
    except PipelineError as exc:
        audit.log_event(settings.audit_db, session_id=prepared.session_id or "?",
                        agent_id="subject_agent", version="1.0",
                        status=exc.state.value, errors=[exc.detail])
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    # Persistance du résultat validé + audit
    workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                   "subject_output", result.output)
    if result.verifier is not None:
        workspace.save(settings.workspace_dir, prepared.student_id, prepared.session_id,
                       "verifier_output", result.verifier)
    audit.log_event(settings.audit_db, session_id=prepared.session_id,
                    agent_id="subject_agent", version="1.0",
                    status=result.output.status.value,
                    validation_result=result.verifier_status,
                    attempts=result.attempts,
                    consumption=llm.calls)

    return {
        "session_id": prepared.session_id,
        "status": result.output.status.value,
        "verifier_status": result.verifier_status,
        "attempts": result.attempts,
        "injection_annotations": result.injection_annotations,
        "output": result.output.model_dump(mode="json"),
        "verifier": result.verifier.model_dump(mode="json") if result.verifier else None,
    }


@router.get("/subject/{student_id}/{session_id}")
async def get_subject(request: Request, student_id: str, session_id: str) -> dict:
    settings = request.app.state.settings
    data = workspace.load(settings.workspace_dir, student_id, session_id, "subject_output")
    if data is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return data


@router.post("/subject/question")
async def question(request: Request, body: QuestionRequest) -> dict:
    """Répondre à une question de l'étudiant DANS le périmètre de cet agent.

    Demandé par le porteur : l'agent choisi répond à toutes les requêtes ; si la question sort de
    son périmètre, l'agent le DIT et nomme l'étape compétente — c'est ce signalement qui permet à
    l'orchestrateur de faire répondre le bon agent, au lieu de laisser inventer.
    Aucune écriture de dossier : répondre ne consomme pas une analyse.
    """
    settings = request.app.state.settings
    llm = request.app.state.llm
    try:
        reponse = interrogation.repondre(
            llm, body.question, contexte=body.contexte,
            nom_etape="Sujet", libelle_etape="Cadrage du sujet de mémoire")
    except PipelineError as exc:
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    audit.log_event(settings.audit_db, session_id=body.session_id or "?",
                    agent_id="subject_agent", version="1.0", status="question_answered",
                    consumption=llm.calls)
    return {"agent": "subject_agent", "etape": 1, "nom": "Sujet",
            "question": body.question, **reponse}
