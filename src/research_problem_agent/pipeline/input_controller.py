"""Contrôleur d'entrée : prépare la session et vérifie le sujet amont (SPEC §11, §12).

Le sujet transmis par l'Agent Sujet n'est accepté comme base que s'il est `verified` :
une sortie non vérifiée ne doit pas servir de fondation (le portillon méthodologique).
"""

from ..core.errors import ErrorState, PipelineError
from ..core.sessions import new_session_id
from ..schemas.input import ProblemRequest


def prepare(request: ProblemRequest) -> ProblemRequest:
    """Garantit la présence d'un session_id sans écraser celui fourni."""
    if not request.session_id:
        return request.model_copy(update={"session_id": new_session_id()})
    return request


def check_upstream(request: ProblemRequest) -> str | None:
    """Retourne un avertissement si le sujet amont n'est pas vérifié, sinon None."""
    upstream = request.upstream_subject
    if upstream is None:
        return None
    if upstream.is_verified:
        return None
    raise PipelineError(
        ErrorState.MISSING_INFORMATION,
        "le sujet transmis par l'Agent Sujet n'est pas vérifié (validation.verified=false) : "
        "finalisez d'abord le Sujet, ou soumettez le sujet de recherche directement",
    )
