"""Étape [10] : « gap check » — outil déterministe, réseau borné (SPEC §8, §9.3).

Vérifie si la lacune identifiée n'a pas déjà été comblée par une publication récente. Aucun LLM ne
déclenche de requête : les requêtes sont dérivées du gap et du sujet, exécutées sous bornes, mises
en cache, et limitées aux hôtes déclarés. Un échec réseau est DÉCLARÉ (`unavailable`), jamais
interprété comme « gap confirmé ».
"""

import re
import unicodedata

from ..core.errors import PipelineError
from ..core.logging import get_logger
from ..schemas.gap import GapCheck, GapCheckPublication, GapCheckResult

log = get_logger("pipeline.gap_check")

_STOPWORDS = {
    "dans", "pour", "avec", "cette", "cette", "leur", "leurs", "plus", "sont", "être", "avoir",
    "aucun", "aucune", "entre", "chez", "tout", "tous", "toute", "the", "and", "for", "with",
    "that", "this", "from", "are", "was", "were", "has", "have", "its", "les", "des", "une",
    "que", "qui", "sur", "par", "pas", "est", "aux", "the",
}


def _tokens_ordered(text: str) -> list[str]:
    """Tokens normalisés (sans accent), sans doublon, dans l'ORDRE d'apparition du texte."""
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[a-z]{4,}", normalized)
    seen: set[str] = set()
    out: list[str] = []
    for word in words:
        if word not in _STOPWORDS and word not in seen:
            seen.add(word)
            out.append(word)
    return out


def _tokens(text: str) -> set[str]:
    return set(_tokens_ordered(text))


def keywords_for(request, gap) -> list[str]:
    """Mots-clés saillants du croisement sujet × gap (ordre d'apparition du sujet)."""
    subject_tokens = _tokens_ordered(request.subject_text)
    gap_tokens = set(_tokens_ordered(gap.description))
    shared = [word for word in subject_tokens if word in gap_tokens] or subject_tokens
    return shared[:6]


def build_queries(request, gap, limit: int) -> list[str]:
    """Requêtes déterministes : mots-clés du croisement sujet × gap, puis sujet et gap en clair.

    Les mots-clés sont joints par « OR » : la plupart des fournisseurs (HAL, theses.fr, OpenAIRE,
    DataCite, DOAJ, Europe PMC) appliquent un ET sur les requêtes multi-termes, si bien qu'une
    phrase entière — ou même deux mots — ne renvoie RIEN. La requête en mots-clés est donc placée
    en premier ; les fournisseurs à recherche « booléenne libre » (Crossref, OpenAlex) acceptent
    aussi les deux autres formulations.
    """
    subject = " ".join((request.subject_text or "").split()[:14]).strip()
    gap_text = " ".join((gap.description or "").split()[:16]).strip()
    keywords = " OR ".join(keywords_for(request, gap)).strip()

    queries: list[str] = []
    for candidate in (keywords, subject, gap_text):
        candidate = candidate.strip()
        if candidate and candidate not in queries:
            queries.append(candidate)
    return queries[:max(1, limit)]


def _relevant(record: dict, keywords: set[str], min_hits: int = 2) -> bool:
    """Pertinence déterministe : au moins `min_hits` mots-clés du gap présents dans titre + revue.

    Un ratio sur TOUS les mots du sujet s'est révélé trop strict : il écartait des publications
    réellement proches (HAL) et ne laissait passer que les titres longs de Crossref. La référence
    est donc le jeu de mots-clés qui a servi à interroger les fournisseurs.
    """
    if not keywords:
        return False
    candidate = _tokens(f"{record.get('title', '')} {record.get('venue', '')}")
    if not candidate:
        return False
    return len(candidate & keywords) >= min(min_hits, len(keywords))


def run(request, gap, settings, registry=None, fetcher=None, cache=None) -> GapCheck:
    """Retourne un GapCheck. Ne lève jamais pour un échec réseau : il le déclare."""
    from ..sources.cache import GapCheckCache
    from ..sources.http import ApiFetcher
    from ..sources.registry import Registry

    sources_cfg = settings.sources or {}
    if not sources_cfg.get("enabled", True):
        return GapCheck(result=GapCheckResult.unavailable,
                        note="recherche réseau désactivée par configuration")

    registry = registry or Registry(settings.providers_file)
    fetcher = fetcher or ApiFetcher(sources_cfg, settings.limits, registry.allowed_hosts())
    cache = cache or GapCheckCache(settings.cache_db, settings.limits.cache_ttl_hours)

    limit = int(getattr(settings.limits, "max_gap_check_queries", 4))
    queries = build_queries(request, gap, limit)
    if not queries:
        return GapCheck(result=GapCheckResult.unavailable,
                       note="aucune requête exploitable pour vérifier le gap")

    reference = _tokens(f"{request.subject_text} {gap.description}")
    collected: list[dict] = []
    providers_used: list[str] = []
    providers_failed: list[dict] = []
    per_query = int(getattr(settings.limits, "max_results_per_query", 10))

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
                collected.extend(cached or [])
            except PipelineError as exc:
                providers_failed.append({"provider": provider.id, "query": query,
                                         "error": exc.state.value})
                log.info("gap check : fournisseur %s en échec (%s)", provider.id, exc.state.value)

    if not collected and providers_failed:
        return GapCheck(
            result=GapCheckResult.unavailable, queries=queries,
            providers_used=providers_used, providers_failed=providers_failed,
            note="aucune source interrogée avec succès : le statut du gap ne peut pas être vérifié "
                 "automatiquement (cela ne confirme ni n'infirme le gap)",
        )

    # Déduplication + sélection des publications réellement proches du sujet et du gap.
    reference = set(keywords_for(request, gap))
    seen: set[str] = set()
    publications: list[GapCheckPublication] = []
    for record in collected:
        key = (record.get("doi") or record.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if not _relevant(record, reference):
            continue
        publications.append(GapCheckPublication(
            title=str(record.get("title", ""))[:500],
            authors=[str(a) for a in (record.get("authors") or [])[:12]],
            year=record.get("year"),
            doi=str(record.get("doi", "")),
            url=str(record.get("url", "")),
            provider=str(record.get("provider", "")),
        ))

    result = GapCheckResult.already_addressed if publications else GapCheckResult.not_found
    note = (
        f"{len(publications)} publication(s) proche(s) du sujet et du gap ont été trouvées : "
        "le gap pourrait déjà être partiellement comblé — à examiner par l'étudiant."
        if publications else
        "aucune publication proche trouvée dans les sources interrogées : cela ne prouve pas "
        "l'absence de travaux, seulement leur non-détection ici."
    )
    return GapCheck(result=result, queries=queries, publications=publications,
                    providers_used=providers_used, providers_failed=providers_failed, note=note)
