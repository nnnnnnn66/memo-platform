"""Validations de schéma des sorties de chaque phase LLM."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.stages import AnalysisOutput, GeneralOutput, SpecificOutput


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate_analysis(data: dict) -> AnalysisOutput:
    return _validate(AnalysisOutput, data)


def validate_general(data: dict) -> GeneralOutput:
    return _validate(GeneralOutput, data)


def validate_specific(data: dict) -> SpecificOutput:
    return _validate(SpecificOutput, data)
