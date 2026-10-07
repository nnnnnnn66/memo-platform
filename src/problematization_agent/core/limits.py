"""Bornes de consommation (SPEC §8, §10). Cadre propre à l'agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    max_input_size: int
    max_output_tokens: int
    max_agent_turns: int
    max_verification_retries: int
    timeout: int
    max_llm_calls: int
    # --- lecture du corpus amont ---
    max_documents_read: int
    max_context_chars: int
    max_document_chars: int
    # --- ancrage verbatim ---
    min_quote_chars: int
    max_quote_chars: int
    max_statements_per_stage: int
    # --- gap check (réseau borné) ---
    max_external_requests: int
    source_timeout: int
    max_gap_check_queries: int
    max_results_per_query: int
    cache_ttl_hours: int

    @classmethod
    def from_dict(cls, d: dict) -> "Limits":
        fields = cls.__dataclass_fields__.keys()
        return cls(**{k: int(d[k]) for k in fields if k in d})
