"""Validation de schéma des sorties de chaque étage LLM."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.stages import PlanOutput, SynthesisOutput, WritingOutput


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate_synthesis(data: dict) -> SynthesisOutput:
    return _validate(SynthesisOutput, data)


def validate_plan(data: dict) -> PlanOutput:
    return _validate(PlanOutput, data)


def validate_writing(data: dict) -> WritingOutput:
    return _validate(WritingOutput, data)
