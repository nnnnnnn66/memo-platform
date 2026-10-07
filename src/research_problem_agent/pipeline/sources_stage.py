"""Phase déterministe de récupération des sources (SPEC §9.3).

Aucun LLM ici : le modèle propose des intentions de recherche, ce module décide quels
fournisseurs déclarés sont interrogés, sous bornes strictes (requêtes, taille, cache).
"""

from ..core.errors import PipelineError
from ..core.logging import get_logger
from ..sources.cache import SourceCache
from ..sources.http import Fetcher
from ..sources.registry import Registry
from ..sources.source_set import SourceSet

log = get_logger("sources.stage")

# Bornes de sélection (surchargeables par config, sans toucher au pipeline).
DEFAULT_MAX_PROVIDERS_PER_INTENT = 3
DEFAULT_MAX_SOURCES_TOTAL = 15


def _cfg(settings, key: str, default: int) -> int:
    try:
        return int(settings.sources.get(key, default))
    except (TypeError, ValueError):
        return default


def retrieve(intents, settings, registry: Registry | None = None,
             fetcher: Fetcher | None = None, cache: SourceCache | None = None) -> SourceSet:
    """Exécute les intentions de recherche et retourne l'ensemble des sources réellement
    récupérées. Une défaillance de fournisseur est enregistrée, jamais compensée par une
    invention (SPEC §15)."""
    source_set = SourceSet()
    if not settings.sources.get("enabled", True):
        return source_set

    registry = registry or Registry(settings.providers_file)
    fetcher = fetcher or Fetcher(settings.sources, settings.limits, registry.allowed_hosts())
    cache = cache or SourceCache(settings.cache_db, settings.limits.cache_ttl_hours)

    max_providers = _cfg(settings, "max_providers_per_intent", DEFAULT_MAX_PROVIDERS_PER_INTENT)
    max_total = _cfg(settings, "max_sources_total", DEFAULT_MAX_SOURCES_TOTAL)
    per_query = int(settings.limits.max_search_results)

    executed = 0
    for intent in list(intents)[: settings.limits.max_search_queries]:
        query = (intent.query or "").strip()
        if not query:
            continue
        source_set.queries.append(query)

        used_for_intent = 0
        for provider in registry.select(intent.kind.value):
            if len(source_set) >= max_total or used_for_intent >= max_providers:
                break
            if executed >= settings.limits.max_tool_calls:
                break
            if fetcher.requests >= settings.limits.max_external_requests:
                break

            cached = cache.get(provider.id, query, per_query)
            if cached is None:
                try:
                    adapter = registry.adapter_module(provider)
                    records = adapter.search(fetcher, query, per_query)
                except PipelineError as exc:
                    source_set.mark_failed(provider.id, f"{exc.state.value}: {exc.detail}")
                    log.info("fournisseur %s indisponible : %s", provider.id, exc.state.value)
                    continue
                except Exception as exc:  # noqa: BLE001 — un adaptateur ne doit jamais casser le flux
                    source_set.mark_failed(provider.id, f"adaptateur: {type(exc).__name__}")
                    continue
                cache.set(provider.id, query, per_query, records)
                executed += 1
            else:
                records = cached

            used_for_intent += 1
            for record in records or []:
                if len(source_set) >= max_total:
                    break
                source_set.add(provider.id, record, provider.source_type,
                               settings.limits.max_source_snippet)

    log.info("recherche terminée : %s sources, %s requêtes réseau, fournisseurs=%s",
             len(source_set), fetcher.requests, ",".join(source_set.providers_used))
    return source_set
