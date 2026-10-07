"""Contrôleur d'entrée : prépare la session (SPEC §31). Aucune logique métier."""

from ..core.sessions import new_session_id
from ..schemas.input import SubjectRequest


def prepare(request: SubjectRequest) -> SubjectRequest:
    """Garantit la présence d'un session_id sans écraser celui fourni."""
    if not request.session_id:
        return request.model_copy(update={"session_id": new_session_id()})
    return request
