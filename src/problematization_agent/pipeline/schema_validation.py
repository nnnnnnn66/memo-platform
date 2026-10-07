"""Validations de schéma des sorties de chaque phase."""

from pydantic import ValidationError

from ..core.errors import ErrorState, PipelineError
from ..schemas.stages import (
    AlignmentOutput,
    ConfrontationOutput,
    GapOutput,
    JustificationOutput,
    ProblemMappingOutput,
    QuestionObjectivesOutput,
)


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)) from exc


def validate_problem_mapping(data: dict) -> ProblemMappingOutput:
    return _validate(ProblemMappingOutput, data)


def validate_confrontation(data: dict) -> ConfrontationOutput:
    return _validate(ConfrontationOutput, data)


def validate_gap(data: dict) -> GapOutput:
    return _validate(GapOutput, data)


def validate_justification(data: dict) -> JustificationOutput:
    return _validate(JustificationOutput, data)


def validate_question_objectives(data: dict) -> QuestionObjectivesOutput:
    return _validate(QuestionObjectivesOutput, data)


def validate_alignment(data: dict) -> AlignmentOutput:
    return _validate(AlignmentOutput, data)
