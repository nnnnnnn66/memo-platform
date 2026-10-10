"""Contrôleur d'entrée : session et liaison amont (SPEC §6)."""

from ..core.errors import ErrorState, PipelineError
from ..core.sessions import new_session_id


def prepare(request):
    if not request.session_id:
        return request.model_copy(update={"session_id": new_session_id()})
    return request


def check_upstream(request) -> None:
    """Une sortie amont n'est utilisable que si SON vérificateur l'a validée.

    La clé dépend de l'émetteur (`validation` pour les étapes 1 à 4, `verification_result` pour les
    étapes 5 à 9) : `is_verified` accepte les deux (leçon de la chaîne 1 → 9).
    """
    for label, payload in (("sujet", request.upstream_subject),
                           ("problème", request.upstream_problem),
                           ("revue de littérature", request.upstream_literature),
                           ("problématique", request.upstream_problematic),
                           ("question de recherche", request.upstream_question),
                           ("objectifs de recherche", request.upstream_objectives),
                           ("hypothèses de recherche", request.upstream_hypotheses),
                           ("diagnostic méthodologique", request.upstream_methodology_diagnostic),
                           ("méthodologie", request.upstream_methodology)):
        if payload is not None and not payload.is_verified:
            raise PipelineError(
                ErrorState.MISSING_INFORMATION,
                f"la sortie « {label} » transmise n'est pas vérifiée : finalisez d'abord l'étape "
                "précédente, ou fournissez le texte correspondant directement")
