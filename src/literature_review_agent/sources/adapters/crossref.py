"""Crossref — registre officiel des DOI (articles, thèses, rapports ; gratuit, sans clé)."""

from . import candidate, clean, first, year_of

PROVIDER_ID = "crossref"
ENDPOINT = "https://api.crossref.org/works"

_TYPE_MAP = {
    "journal-article": "article", "proceedings-article": "article", "book-chapter": "book",
    "book": "book", "monograph": "book", "dissertation": "thesis", "report": "report",
    "posted-content": "preprint", "dataset": "dataset", "reference-entry": "article",
}


def _pdf_candidates(item: dict) -> list[dict]:
    out = []
    for link in item.get("link") or []:
        url = (link or {}).get("URL") or ""
        content_type = str((link or {}).get("content-type") or "")
        if url and ("pdf" in content_type or url.lower().endswith(".pdf")):
            out.append(candidate(url, "publisher"))
    return out


def _is_oa(item: dict) -> bool:
    licenses = item.get("license") or []
    for lic in licenses:
        if (lic or {}).get("URL"):
            return True
    return False


def search(fetcher, query: str, limit: int) -> list[dict]:
    params = {"query": query, "rows": limit}
    email = (fetcher.cfg or {}).get("polite_email")
    if email:
        params["mailto"] = email
    data = fetcher.fetch_json(ENDPOINT, params)
    out = []
    for item in (data.get("message") or {}).get("items", []):
        doi = (item.get("DOI") or "").strip()
        parts = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
        year = year_of(parts[0]) if parts else None
        authors = []
        for author in item.get("author") or []:
            name = " ".join(x for x in [author.get("given"), author.get("family")] if x)
            if name:
                authors.append(name)
        out.append({
            "title": clean(first(item.get("title")), 500),
            "authors": authors[:12],
            "year": year,
            "venue": clean(first(item.get("container-title")) or first(item.get("publisher")) or "", 300),
            "doi": doi,
            "url": (item.get("URL") or (f"https://doi.org/{doi}" if doi else "")).strip(),
            "volume": str(item.get("volume") or ""),
            "issue": str(item.get("issue") or ""),
            "pages": str(item.get("page") or ""),
            "language": (item.get("language") or "")[:8],
            "abstract": clean(item.get("abstract"), 4000),
            "document_type": _TYPE_MAP.get(item.get("type"), "other"),
            "is_oa": _is_oa(item),
            "pdf_candidates": _pdf_candidates(item),
        })
    return out


def lookup_by_doi(fetcher, doi: str) -> dict | None:
    """Métadonnées complètes d'un DOI connu (utilisé pour les références fournies par l'étudiant)."""
    try:
        data = fetcher.fetch_json(f"{ENDPOINT}/{doi}")
    except Exception:  # noqa: BLE001
        return None
    item = data.get("message") or {}
    return item or None
