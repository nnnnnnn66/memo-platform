"""Contrôleur d'entrée : session et liaison amont (étape 3)."""

from ..core.errors import ErrorState, PipelineError
from ..core.sessions import new_session_id


def prepare(request):
    if not request.session_id:
        return request.model_copy(update={"session_id": new_session_id()})
    return request


def check_upstream(request) -> None:
    """Une sortie amont n'est utilisable que si son propre vérificateur l'a validée."""
    for label, payload in (("sujet", request.upstream_subject),
                           ("problème", request.upstream_problem)):
        if payload is not None and not payload.is_verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                f"la sortie « {label} » transmise n'est pas vérifiée "
                "(validation.verified=false) : finalisez d'abord l'étape précédente, ou "
                "fournissez le texte correspondant directement",
            )
    if request.upstream_literature is not None and not request.upstream_literature.is_verified:
        raise PipelineError(
            ErrorState.MISSING_INFORMATION,
            "la revue de littérature transmise n'est pas vérifiée (validation.verified=false) : "
            "la problématique ne peut pas être sourcée sur des documents non validés. "
            "Finalisez l'étape 3, ou fournissez les documents directement",
        )
