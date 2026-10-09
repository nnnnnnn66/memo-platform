"""États d'erreur contrôlés (SPEC §15). Propres à cet agent."""

from enum import Enum


class ErrorState(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    OUTPUT_SCHEMA_ERROR = "OUTPUT_SCHEMA_ERROR"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    TOOL_ERROR = "TOOL_ERROR"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class PipelineError(Exception):
    """Erreur contrôlée du pipeline. Ne contient jamais de secret."""

    def __init__(self, state: ErrorState, detail: str = "") -> None:
        self.state = state
        self.detail = detail
        super().__init__(f"{state.value}: {detail}")
