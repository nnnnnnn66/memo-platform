"""Validation de schéma des sorties de l'agent (SPEC §16)."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.output import ProblemOutput
from ..schemas.search_intent import Phase1Output


def validate_phase1(data: dict) -> Phase1Output:
    try:
        return Phase1Output.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate(data: dict) -> ProblemOutput:
    try:
        return ProblemOutput.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc
