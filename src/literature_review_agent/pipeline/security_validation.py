"""Validation de sécurité des sorties de l'agent."""

from ..core.errors import ErrorState, PipelineError
from ..core.security_rules import UNTRUSTED_TAGS, contains_secret

_LEAK_MARKERS = [
    "system prompt",
    "prompt système",
    "api_key_env",
    "tu es l'agent revue",
    "ouvre un terminal",
    "exécute la commande",
]


def check_payload(payload) -> None:
    """Contrôle une sortie LLM quelconque (dict ou modèle) avant tout usage."""
    blob = payload if isinstance(payload, str) else (
        payload.model_dump_json() if hasattr(payload, "model_dump_json") else str(payload))
    if contains_secret(blob):
        raise PipelineError(ErrorState.SECURITY_VIOLATION, "secret détecté dans la sortie")
    lowered = blob.lower()
    for marker in _LEAK_MARKERS:
        if marker in lowered:
            raise PipelineError(ErrorState.SECURITY_VIOLATION,
                                "fuite potentielle d'instructions internes dans la sortie")
    for tag in UNTRUSTED_TAGS:
        if tag in blob:
            raise PipelineError(ErrorState.SECURITY_VIOLATION,
                                "la sortie recopie un balisage interne de données non fiables")
