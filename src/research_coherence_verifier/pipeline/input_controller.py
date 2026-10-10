"""Contrôleur d'entrée : session et recevabilité du dossier (SPEC §5, §14).

Différence essentielle avec les autres agents : une étape NON VÉRIFIÉE n'est pas un refus — c'est un
CONSTAT (X1). Seul un dossier ENTIÈREMENT non vérifié est arrêté : l'audit n'aurait aucun fondement.
"""

from ..core.errors import ErrorState, PipelineError
from ..core.sessions import new_session_id


def prepare(request):
    if not request.session_id:
        return request.model_copy(update={"session_id": new_session_id()})
    return request


def check_upstream(request) -> None:
    payloads = [p for p in request.payloads().values() if p is not None]
    if not payloads:
        raise PipelineError(ErrorState.MISSING_INFORMATION,
                            "aucune sortie amont transmise : il n'y a rien à auditer")
    if not any(p.is_verified for p in payloads):
        raise PipelineError(
            ErrorState.MISSING_INFORMATION,
            "aucune étape du dossier n'est vérifiée : l'audit porterait uniquement sur des brouillons. "
            "Finalisez au moins une étape (vérificateur puis décision) avant de demander un contrôle "
            "de cohérence.")
