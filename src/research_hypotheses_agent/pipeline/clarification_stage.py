"""Étape [10] — clarification documentaire (déterministe, OPTIONNELLE, réseau borné).

Sert à lever une ambiguïté terminologique dans un objectif (« ce concept recouvre-t-il bien ceci dans
la littérature ? »). Elle ne produit PAS d'état des savoirs et n'est jamais déclenchée par le modèle.
Désactivée par défaut (`clarification.enabled: false`). Aucune source n'entre dans les objectifs :
les résultats ne sont qu'une PREUVE (`source_evidence`), jamais une citation imposée.
"""

import re
import unicodedata

from ..core.errors import PipelineError
from ..core.logging import get_logger
from ..schemas.hypotheses import SourceEvidence

log = get_logger("pipeline.clarification")


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return {w for w in re.findall(r"[a-z]{4,}", normalized)}


def _queries(terms: list[str], limit: int) -> list[str]:
    """Requêtes en mots-clés joints par OR (la plupart des fournisseurs appliquent un ET)."""
    words: list[str] = []
    for term in terms:
        for word in re.findall(r"[A-Za-zÀ-ÿ]{4,}", term or ""):
            key = unicodedata.normalize("NFKD", word.lower()).encode("ascii", "ignore").decode()
            if key and key not in words:
                words.append(key)
    if not words:
        return []
    return [" OR ".join(words[:6])][:max(1, limit)]


def run(terms, settings, registry=None, fetcher=None, cache=None, limit: int = 3):
    """Retourne (source_evidence, stats, note). Ne lève jamais pour un échec réseau : il le déclare."""
    stats = {"network_requests": 0, "cache_hits": 0}
    if not terms:
        return [], stats, "aucun concept ambigu à vérifier"

    if not (settings.clarification or {}).get("enabled", False):
        return [], stats, "clarification documentaire désactivée par configuration"

    from ..sources.cache import GapCheckCache
    from ..sources.http import ApiFetcher
    from ..sources.registry import Registry

    registry = registry or Registry(settings.providers_file)
    fetcher = fetcher or ApiFetcher(settings.sources or {}, settings.limits,
                                    registry.allowed_hosts())
    cache = cache or GapCheckCache(settings.cache_db, settings.limits.cache_ttl_hours)

    queries = _queries(terms, int(getattr(settings.limits, "max_clarification_queries", 3)))
    if not queries:
        return [], stats, "aucune requête exploitable pour clarifier"

    reference = set()
    for term in terms:
        reference |= _tokens(term)

    per_query = int(getattr(settings.limits, "max_results_per_query", 10))
    evidence: list[SourceEvidence] = []
    providers_used: list[str] = []
    providers_failed: list[str] = []
    seen: set[str] = set()

    for provider in registry.enabled():
        search = registry.adapter_module(provider).search
        for query in queries:
            try:
                cached = cache.get(provider.id, query, per_query)
                if cached is None:
                    cached = search(fetcher, query, per_query)
                    cache.set(provider.id, query, per_query, cached)
                if provider.id not in providers_used:
                    providers_used.append(provider.id)
            except PipelineError as exc:
                providers_failed.append(provider.id)
                log.info("clarification : fournisseur %s en échec (%s)", provider.id, exc.state.value)
                continue
            for record in cached or []:
                if reference and not (reference & _tokens(str(record.get("title", "")))):
                    continue
                key = (record.get("doi") or record.get("title") or "").strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                evidence.append(SourceEvidence(
                    query=query, provider=provider.id,
                    source_id=key, title=str(record.get("title", ""))[:400],
                    url=str(record.get("url", "")), used=False))

    stats["network_requests"] = getattr(fetcher, "requests", 0)
    stats["cache_hits"] = getattr(cache, "hits", 0)

    if not evidence and providers_failed:
        return [], stats, (
            "clarification incomplète : aucun fournisseur n'a répondu ("
            + ", ".join(sorted(set(providers_failed)))
            + ") — le concept n'a pas pu être vérifié")

    note = (f"{len(evidence)} référence(s) trouvée(s) pour clarifier le concept"
            if evidence else "aucune référence trouvée pour ce concept dans les sources interrogées")
    return evidence, stats, note
