"""Validations de schéma des sorties de chaque phase."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.analysis import BatchAnalysis
from ..schemas.diagnosis import Diagnosis
from ..schemas.keywords import KeywordsOutput
from ..schemas.synthesis import SynthesisOutput


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate_keywords(data: dict) -> KeywordsOutput:
    return _validate(KeywordsOutput, data)


def validate_batch(data: dict) -> BatchAnalysis:
    return _validate(BatchAnalysis, data)


def validate_synthesis(data: dict) -> SynthesisOutput:
    return _validate(SynthesisOutput, data)


def validate_diagnosis(data: dict) -> Diagnosis:
    if isinstance(data, dict) and "diagnosis" in data:
        data = data["diagnosis"]
    return _validate(Diagnosis, data)
