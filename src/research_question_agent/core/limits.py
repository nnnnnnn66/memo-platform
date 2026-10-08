"""Bornes de consommation (SPEC §11, §14). Cadre propre à l'agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    max_input_size: int
    max_output_tokens: int
    max_agent_turns: int
    max_verification_retries: int
    timeout: int
    max_llm_calls: int
    # --- clarification documentaire (réseau borné, optionnel) ---
    max_external_requests: int
    source_timeout: int
    max_clarification_queries: int
    max_results_per_query: int
    cache_ttl_hours: int

    @classmethod
    def from_dict(cls, d: dict) -> "Limits":
        fields = cls.__dataclass_fields__.keys()
        return cls(**{k: int(d[k]) for k in fields if k in d})
