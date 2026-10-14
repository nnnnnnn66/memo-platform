"""Endpoints HTTP de l'Agent Diagnostic méthodologique. Aucune logique métier ici."""

from fastapi import APIRouter, HTTPException, Request

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..pipeline import campaign, input_controller, interrogation
from ..schemas.decision import DecisionRequest
from ..schemas.input import MethodologyRequest, QuestionRequest
from ..schemas.output import MethodologyOutput
from ..storage import audit, workspace

router = APIRouter()
log = get_logger("api")

AGENT_ID = "methodology_diagnostic_agent"
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
    'agent': 'methodology_diagnostic_agent',
    'etape': 8,
    'nom': 'Orientation méthodologique',
    'role': "Diagnostique l'orientation méthodologique (approche, logique, type, stratégie, collecte, analyse) selon les règles M1-M7.",
    'capacites': ['diagnostic_methodologique', 'regles_m1_m7'],
    'entrees_requises': ['upstream_hypotheses', 'upstream_objectives', 'upstream_problem', 'upstream_problematic', 'upstream_question', 'upstream_subject'],
    'necessite_reseau': False,
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

@router.post("/methodology/analyze")
async def analyze(request: Request, body: MethodologyRequest) -> dict:
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

    workspace.save(settings.workspace_dir, prepared.student_id, session_id, "methodology_request",
                   prepared)
    workspace.save(settings.workspace_dir, prepared.student_id, session_id, "methodology_output",
                   result.output)
    if result.verifier is not None:
        workspace.save(settings.workspace_dir, prepared.student_id, session_id, "verifier_output",
                       result.verifier)

    audit.log_event(settings.audit_db, session_id=session_id, agent_id=AGENT_ID,
                    version=VERSION, status=result.output.status.value,
                    validation_result=result.verifier_status, attempts=result.attempts,
                    llm_calls=result.llm_calls, external_requests=result.external_requests,
                    cache_hits=result.cache_hits,
                    diagnostic_status=result.output.diagnostic_status.value,
                    approach=result.output.diagnosis.approche.code,
                    logic=result.output.diagnosis.logique.code,
                    reformulations=result.reformulations,
                    ambiguities=len(result.output.ambiguities))

    return {
        "session_id": session_id,
        "status": result.output.status.value,
        "diagnostic_status": result.output.diagnostic_status.value,
        "provisional": result.output.provisional,
        "verifier_status": result.verifier_status,
        "attempts": result.attempts,
        "verifications": result.verifications,
        "llm_calls": result.llm_calls,
        "external_requests": result.external_requests,
        "cache_hits": result.cache_hits,
        "reformulations": result.reformulations,
        "stages": result.stages,
        "injection_annotations": result.injection_annotations,
        "output": result.output.model_dump(mode="json"),
        "verifier": result.verifier.model_dump(mode="json") if result.verifier else None,
    }


@router.post("/methodology/{student_id}/{session_id}/decision")
async def decide(request: Request, student_id: str, session_id: str,
                 body: DecisionRequest) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    verifier_llm = getattr(request.app.state, "verifier_llm", None) or llm

    stored_request = workspace.load(settings.workspace_dir, student_id, session_id,
                                    "methodology_request")
    stored_output = workspace.load(settings.workspace_dir, student_id, session_id,
                                   "methodology_output")
    if stored_request is None or stored_output is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})

    try:
        methodology_request = MethodologyRequest.model_validate(stored_request)
        output = MethodologyOutput.model_validate(stored_output)
        result = campaign.decide(methodology_request, settings, llm, output, body,
                                 verifier_llm=verifier_llm)
    except PipelineError as exc:
        audit.log_event(settings.audit_db, session_id=session_id, agent_id=AGENT_ID,
                        version=VERSION, status=exc.state.value, errors=[exc.detail],
                        student_decision=body.decision.value)
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    workspace.save(settings.workspace_dir, student_id, session_id, "methodology_output",
                   result.output)
    audit.log_event(settings.audit_db, session_id=session_id, agent_id=AGENT_ID, version=VERSION,
                    status=result.output.status.value, validation_result=result.verifier_status,
                    student_decision=body.decision.value,
                    diagnostic_status=result.output.diagnostic_status.value)

    return {
        "session_id": session_id,
        "status": result.output.status.value,
        "diagnostic_status": result.output.diagnostic_status.value,
        "verifier_status": result.verifier_status,
        "student_decision": body.decision.value,
        "output": result.output.model_dump(mode="json"),
    }


@router.get("/methodology/{student_id}/{session_id}")
async def get_diagnostic(request: Request, student_id: str, session_id: str) -> dict:
    settings = request.app.state.settings
    data = workspace.load(settings.workspace_dir, student_id, session_id, "methodology_output")
    if data is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return data

@router.post("/methodology/question")
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
            nom_etape="Orientation méthodologique", libelle_etape="Diagnostic méthodologique")
    except PipelineError as exc:
        raise HTTPException(status_code=_STATUS_MAP.get(exc.state, 500),
                            detail={"error": exc.state.value, "detail": exc.detail}) from exc

    audit.log_event(settings.audit_db, session_id=body.session_id or "?",
                    agent_id="methodology_diagnostic_agent", version="1.0", status="question_answered",
                    llm_calls=llm.calls)
    return {"agent": "methodology_diagnostic_agent", "nom": "Orientation méthodologique", "question": body.question, **reponse}
