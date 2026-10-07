"""Validation de schéma de la sortie de l'agent (SPEC §10)."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.output import SubjectOutput


def validate(data: dict) -> SubjectOutput:
    try:
        return SubjectOutput.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc
