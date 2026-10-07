"""Validation de sécurité de la sortie (SPEC §22, §25, §27)."""

from ..core.errors import ErrorState, PipelineError
from ..core.security_rules import contains_secret
from ..schemas.output import SubjectOutput

# Marqueurs indiquant une fuite d'instructions internes.
_LEAK_MARKERS = [
    "system prompt",
    "prompt système",
    "<sujet_non_fiable>",
    "api_key_env",
]


def check(output: SubjectOutput) -> None:
    blob = output.model_dump_json()
    if contains_secret(blob):
        raise PipelineError(ErrorState.SECURITY_VIOLATION, "secret détecté dans la sortie")
    lowered = blob.lower()
    for marker in _LEAK_MARKERS:
        if marker in lowered:
            raise PipelineError(
                ErrorState.SECURITY_VIOLATION,
                "fuite potentielle d'instructions internes dans la sortie",
            )
