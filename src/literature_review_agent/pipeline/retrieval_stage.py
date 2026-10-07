"""Étape de recherche documentaire (SPEC §9.3) — déterministe, aucun LLM.

Traduit les requêtes validées de la phase 1 en appels de fournisseurs, applique la cascade
géographique, dédoublonne et pré-classe le corpus.
"""

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..sources.corpus import Corpus, CorpusRecord, detect_geography, normalize_language
from ..sources.registry import Registry

log = get_logger("pipeline.retrieval")

# Terme ajouté à la requête lorsqu'une portée géographique est visée mais absente du texte.
SCOPE_TERMS = {
    "ivory_coast": "Côte d'Ivoire",
    "west_africa": "Afrique de l'Ouest",
    "africa": "Afrique",
}


def _with_scope(query: str, scope: str, cascade: list[str]) -> str:
    term = SCOPE_TERMS.get(scope, "")
    if term and term.lower() not in query.lower():
        return f"{query} {term}".strip()
    return query


def _record_from(provider, item: dict, scope: str) -> CorpusRecord:
    text = f"{item.get('title','')} {item.get('abstract','')} {item.get('venue','')}"
    geographic, evidence = detect_geography(text)
    return CorpusRecord(
        provider=provider.id,
        source_type=provider.source_type,
        document_type=item.get("document_type") or "other",
        title=(item.get("title") or "")[:500],
        url=(item.get("url") or "")[:1000],
        authors=[str(a) for a in (item.get("authors") or [])][:12],
        year=item.get("year"),
        venue=(item.get("venue") or "")[:300],
        doi=(item.get("doi") or "")[:200],
        volume=str(item.get("volume") or "")[:20],
        issue=str(item.get("issue") or "")[:20],
        pages=str(item.get("pages") or "")[:40],
        language=(normalize_language(item.get("language"))),
        abstract=(item.get("abstract") or "")[:4000],
        pdf_candidates=item.get("pdf_candidates") or [],
        is_oa=bool(item.get("is_oa")),
        query_scopes=[scope],
    )


def run_campaign(queries, settings, registry: Registry | None = None,
                 fetcher=None, cache=None, corpus: Corpus | None = None,
                 concept_terms: list[str] | None = None) -> Corpus:
    """Exécute les requêtes sur les fournisseurs déclarés et retourne le corpus dédoublonné."""
    registry = registry or Registry(settings.providers_file)
    corpus = corpus or Corpus()
    if fetcher is None or cache is None:
        raise PipelineError(ErrorState.INVALID_INPUT, "client de recherche ou cache manquant")

    cascade = settings.sources.get("cascade") or ["Côte d'Ivoire", "Afrique de l'Ouest",
                                                  "Afrique", "International"]
    max_providers = int(settings.sources.get("max_providers_per_query", 4))
    # Le plafond du corpus FINAL ne doit pas arrêter la collecte : on collecte dans un vivier plus
    # large (toutes les requêtes et tous les fournisseurs sont ainsi exploités), puis on retient.
    pool_limit = int(settings.sources.get("max_pool_documents", 250))
    per_query = int(settings.limits.max_results_per_query)

    for query in list(queries)[: settings.limits.max_search_queries]:
        text = (query.query or "").strip()
        if not text:
            continue
        scope = query.scope.value if hasattr(query.scope, "value") else str(query.scope)
        text = _with_scope(text, scope, cascade)
        corpus.queries.append(text)

        used = 0
        for provider in registry.select(query.kind.value if hasattr(query.kind, "value")
                                        else str(query.kind)):
            if used >= max_providers or len(corpus) >= pool_limit:
                break
            if fetcher.requests >= settings.limits.max_external_requests:
                break

            cached = cache.get(provider.id, text, per_query)
            if cached is None:
                try:
                    adapter = registry.adapter_module(provider)
                    records = adapter.search(fetcher, text, per_query)
                except PipelineError as exc:
                    corpus.mark_failed(provider.id, f"{exc.state.value}: {exc.detail}", text)
                    log.info("fournisseur %s indisponible (%s)", provider.id, exc.state.value)
                    continue
                except Exception as exc:  # noqa: BLE001 — un adaptateur ne casse jamais la campagne
                    corpus.mark_failed(provider.id, f"adaptateur: {type(exc).__name__}", text)
                    continue
                cache.set(provider.id, text, per_query, records)
                used += 1
            else:
                records = cached

            for item in records or []:
                if len(corpus) >= pool_limit:
                    break
                corpus.add(_record_from(provider, item, scope))

    terms = concept_terms or []
    if not terms:
        for query in queries:
            terms.extend(getattr(query, "concepts", []) or [])
    corpus.rank(terms, ["fr", "en"],
                scope_priority=["ivory_coast", "west_africa", "africa", "international"])
    log.info("campagne terminée : %s documents retenus (%s doublons écartés), fournisseurs=%s",
             len(corpus), corpus.duplicates_removed, ",".join(corpus.providers_used))
    return corpus
