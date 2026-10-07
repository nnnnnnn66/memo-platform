"""Extraction du JSON depuis la sortie LLM. Échoue si aucun JSON exploitable (SPEC §10.12)."""

import json
import re

from ..core.errors import ErrorState, PipelineError

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "sortie LLM vide")

    match = _FENCE.search(text)
    scope = match.group(1) if match else text

    start = scope.find("{")
    end = scope.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "aucun objet JSON trouvé")
    candidate = scope[start:end + 1]

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        hint = ""
        if not text.rstrip().endswith("}"):
            hint = (" — indice : la réponse ne se termine pas par « } », elle est probablement "
                    "TRONQUÉE. Sois plus concis (champs courts, listes limitées).")
        raise PipelineError(
            ErrorState.OUTPUT_SCHEMA_ERROR,
            f"JSON invalide : {exc} (longueur reçue : {len(text)} caractères){hint}",
        ) from exc
    if not isinstance(data, dict):
        raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "la racine JSON n'est pas un objet")
    return data
