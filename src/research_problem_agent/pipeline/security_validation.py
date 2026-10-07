"""Validation de sécurité de la sortie (SPEC §10.11-13, §11)."""

from ..core.errors import ErrorState, PipelineError
from ..core.security_rules import UNTRUSTED_TAGS, contains_secret
from ..schemas.output import ProblemOutput

# Marqueurs indiquant une fuite d'instructions internes ou une consigne exécutable.
_LEAK_MARKERS = [
    "system prompt",
    "prompt système",
    "api_key_env",
    "tu es l'agent problème",
    "ouvre un terminal",
    "exécute la commande",
]


def check(output: ProblemOutput) -> None:
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
    for tag in UNTRUSTED_TAGS:
        if tag in blob:
            raise PipelineError(
                ErrorState.SECURITY_VIOLATION,
                "la sortie recopie un balisage interne de données non fiables",
            )
