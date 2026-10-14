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
    max_search_queries: int
    max_results_per_query: int
    max_documents: int
    min_documents_useful: int
    max_external_requests: int
    source_timeout: int
    max_abstract_chars: int
    documents_per_scoring_batch: int
    max_scoring_batches: int
    cache_ttl_hours: int
    unpaywall_max_lookups: int
    max_downloads: int
    max_download_mb: int
    max_session_download_mb: int
    download_timeout: int
    max_pdf_pages: int
    max_text_chars_per_doc: int
    max_excerpts_per_doc: int
    excerpt_window_chars: int
    max_quote_chars: int
    max_thesis_resolvers: int
    # Nombre de lots de notation notés SIMULTANÉMENT (les lots sont indépendants : méthode,
    # résultats et citations ne dépendent que du document lui-même). 1 = ancien comportement
    # strictement séquentiel. La qualité ne dépend pas du parallélisme : chaque lot reçoit
    # exactement le même contenu et passe par les mêmes validations.
    scoring_parallelism: int = 4

    @classmethod
    def from_dict(cls, d: dict) -> "Limits":
        fields = cls.__dataclass_fields__.keys()
        return cls(**{k: int(d[k]) for k in fields if k in d})
