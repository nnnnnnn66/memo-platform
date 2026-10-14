"""DataCite — DOI de données, de thèses et de dépôts (gratuit, sans clé)."""

from . import candidate, clean, first, year_of

PROVIDER_ID = "datacite"
ENDPOINT = "https://api.datacite.org/dois"

_TYPE_MAP = {"dataset": "dataset", "text": "article", "dissertation": "thesis",
             "book": "book", "report": "report", "preprint": "preprint"}


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"query": query, "page[size]": limit})
    out = []
    for item in data.get("data", []):
        attrs = item.get("attributes") or {}
        doi = (attrs.get("doi") or "").strip()
        types = (attrs.get("types") or {}).get("resourceTypeGeneral") or ""
        rights = first(attrs.get("rightsList"), {}) or {}
        url = (attrs.get("url") or (f"https://doi.org/{doi}" if doi else "")).strip()
        pdfs = []
        if url.lower().endswith(".pdf"):
            pdfs.append(candidate(url, "repository", str(rights.get("rights") or "")))
        out.append({
            "title": clean(first(attrs.get("titles"), {}).get("title"), 500),
            "provider": PROVIDER_ID,
            "authors": [str((c or {}).get("name") or "") for c in (attrs.get("creators") or [])][:12],
            "year": year_of(attrs.get("publicationYear")),
            "venue": clean(attrs.get("publisher") or "DataCite", 300),
            "doi": doi,
            "url": url,
            "language": str(attrs.get("language") or "")[:8],
            "abstract": clean((first(attrs.get("descriptions"), {}) or {}).get("description"), 4000),
            "document_type": _TYPE_MAP.get(str(types).lower(), "other"),
            "is_oa": bool(rights.get("rights")),
            "pdf_candidates": pdfs,
        })
    return out
