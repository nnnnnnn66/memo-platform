"""Validation du contrat d'entrée et des bornes de taille."""

from ..core.errors import ErrorState, PipelineError


def validate(request, limits) -> None:
    if not (request.student_id or "").strip():
        raise PipelineError(ErrorState.INVALID_INPUT, "student_id manquant")

    budget = int(getattr(limits, "max_input_size", 40000))
    for field, value in request.untrusted_texts().items():
        if value and len(str(value)) > budget:
            raise PipelineError(
                ErrorState.RESOURCE_LIMIT,
                f"champ « {field} » trop long ({len(str(value))} > {budget} caractères)",
            )
