"""Bornes de consommation configurables (SPEC §30)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    max_input_size: int
    max_output_tokens: int
    max_tool_calls: int
    max_agent_turns: int
    max_verification_retries: int
    timeout: int
    max_external_requests: int
    max_search_results: int
    # --- recherche documentaire RÉELLE (couche « sources ») ---
    # L'agent ne se contente plus de questionner : il va chercher l'information et la livre,
    # avec ses sources. Bornes strictes (budget réseau, délai, cache) : voir sources/http.py.
    source_timeout: int = 20
    max_research_queries: int = 3
    max_results_per_query: int = 8
    cache_ttl_hours: int = 336

    @classmethod
    def from_dict(cls, d: dict) -> "Limits":
        fields = cls.__dataclass_fields__.keys()
        return cls(**{k: int(d[k]) for k in fields if k in d})
