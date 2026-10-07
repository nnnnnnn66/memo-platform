"""Bornes de consommation de l'Agent Problème (SPEC §10.9). Cadre propre à l'agent."""

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
    max_search_queries: int
    source_timeout: int
    max_source_snippet: int
    cache_ttl_hours: int

    @classmethod
    def from_dict(cls, d: dict) -> "Limits":
        fields = cls.__dataclass_fields__.keys()
        return cls(**{k: int(d[k]) for k in fields if k in d})
