"""Validation du contrat d'entrée et des bornes de taille."""

from ..core.errors import ErrorState, PipelineError


def validate(request, limits) -> None:
    if not (request.student_id or "").strip():
        raise PipelineError(ErrorState.INVALID_INPUT, "student_id manquant")
    if not (request.subject_text or "").strip():
        raise PipelineError(ErrorState.INVALID_INPUT, "subject_text manquant")

    budget = int(getattr(limits, "max_input_size", 20000))
    for field, value in request.untrusted_texts().items():
        if value and len(str(value)) > budget:
            raise PipelineError(
                ErrorState.RESOURCE_LIMIT,
                f"champ « {field} » trop long ({len(str(value))} > {budget} caractères)",
            )
    for doc_id, text in (request.document_texts or {}).items():
        if text and len(str(text)) > int(getattr(limits, "max_document_chars", 80000)) * 4:
            raise PipelineError(
                ErrorState.RESOURCE_LIMIT,
                f"texte fourni pour {doc_id} trop volumineux",
            )
