"""Validation du contrat d'entrée (SPEC §5, §6)."""

from ..core.errors import ErrorState, PipelineError


def validate(request, limits) -> None:
    if not request.student_id or not request.student_id.strip():
        raise PipelineError(ErrorState.INVALID_INPUT, "student_id manquant")
    if not request.subject_text or not request.subject_text.strip():
        raise PipelineError(ErrorState.MISSING_INFORMATION, "subject_text vide")

    for name, value in request.untrusted_texts().items():
        if len(value) > limits.max_input_size:
            raise PipelineError(
                ErrorState.RESOURCE_LIMIT,
                f"{name} dépasse MAX_INPUT_SIZE ({limits.max_input_size})",
            )
    if len(request.student_documents) > 10:
        raise PipelineError(ErrorState.RESOURCE_LIMIT, "trop de documents fournis (max 10)")
    if len(request.known_references) > 100:
        raise PipelineError(ErrorState.RESOURCE_LIMIT, "trop de références fournies (max 100)")
