"""Validations de schéma des sorties de chaque phase LLM."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.stages import AnalysisOutput, InstrumentsOutput, ProtocolOutput, WritingOutput


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate_analysis(data: dict) -> AnalysisOutput:
    return _validate(AnalysisOutput, data)


def validate_protocol(data: dict) -> ProtocolOutput:
    return _validate(ProtocolOutput, data)


def validate_instruments(data: dict) -> InstrumentsOutput:
    return _validate(InstrumentsOutput, data)


def validate_writing(data: dict) -> WritingOutput:
    return _validate(WritingOutput, data)
