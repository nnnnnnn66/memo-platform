"""Validations de schéma des sorties de chaque phase LLM."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.stages import ComprehensionOutput, FormulationOutput, IntentionOutput


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate_comprehension(data: dict) -> ComprehensionOutput:
    return _validate(ComprehensionOutput, data)


def validate_intention(data: dict) -> IntentionOutput:
    return _validate(IntentionOutput, data)


def validate_formulation(data: dict) -> FormulationOutput:
    return _validate(FormulationOutput, data)
