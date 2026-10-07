"""Exécution générique d'une phase LLM : appel, extraction JSON, schéma, contrôles, re-tentative.

Un modèle « raisonneur » consomme son budget `max_tokens` en raisonnement : une sortie peut être
tronquée ou non conforme. Chaque phase DOIT donc avoir sa re-tentative avec consigne de concision —
sans quoi une troncature transitoire devient un échec de toute la campagne.
"""

from ..core.errors import ErrorState, PipelineError
from . import output_parser


def run_json_stage(llm, system: str, user: str, model_cls, extra_checks=None,
                   max_attempts: int = 2, extra: str = ""):
    """Retourne (objet validé, nombre de tentatives). `extra_checks(obj) -> list[str]`."""
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        message = user
        if extra:
            message += "\n\n[INSTRUCTION DE CORRECTION]\n" + extra
        try:
            raw = llm.complete(system, message)
            data = output_parser.extract_json(raw)
            obj = model_cls.model_validate(data)
        except PipelineError as exc:
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({exc.state.value}). "
                         f"Détail : {exc.detail[:400]}\nRéémets UNIQUEMENT le JSON conforme, "
                         "et sois CONCIS.")
                continue
            raise
        except Exception as exc:  # noqa: BLE001 — sortie non conforme au schéma
            if attempts < max_attempts:
                extra = (f"Ta sortie précédente était invalide ({str(exc)[:400]}). "
                         "Réémets UNIQUEMENT le JSON conforme, et sois CONCIS.")
                continue
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, str(exc)[:600]) from exc

        violations = list(extra_checks(obj) or []) if extra_checks else []
        if violations:
            if attempts < max_attempts:
                extra = ("Corrige ces points puis réémets le JSON COMPLET :\n"
                         + "\n".join(f"- {v}" for v in violations))
                continue
            raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR,
                                "phase non conforme : " + " ; ".join(violations[:8]))
        return obj, attempts
    raise PipelineError(ErrorState.OUTPUT_SCHEMA_ERROR, "échec après re-tentatives")
