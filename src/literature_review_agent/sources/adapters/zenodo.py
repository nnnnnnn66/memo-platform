"""Zenodo — dépôt pluridisciplinaire (gratuit, sans clé)."""

from . import candidate, clean, first, year_of

PROVIDER_ID = "zenodo"
ENDPOINT = "https://zenodo.org/api/records"

_TYPE_MAP = {"publication": "article", "article": "article", "thesis": "thesis",
             "dataset": "dataset", "report": "report", "book": "book", "preprint": "preprint"}


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "size": limit})
    hits = ((data.get("hits") or {}).get("hits")) or []
    out = []
    for item in hits:
        meta = item.get("metadata") or {}
        doi = (item.get("doi") or meta.get("doi") or "").strip()
        resource_type = str(((meta.get("resource_type") or {}).get("type")) or "")
        pdfs = []
        for file in item.get("files") or []:
            url = ((file or {}).get("links") or {}).get("self") or ""
            if url:
                pdfs.append(candidate(url, "repository", str(meta.get("license") or "")))
        out.append({
            "title": clean(meta.get("title"), 500),
            "authors": [str((c or {}).get("name") or "") for c in (meta.get("creators") or [])][:12],
            "year": year_of(meta.get("publication_date")),
            "venue": clean(meta.get("publisher") or "Zenodo", 300),
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi
                    else ((item.get("links") or {}).get("self_html") or "")),
            "language": str(meta.get("language") or "")[:8],
            "abstract": clean(meta.get("description"), 4000),
            "document_type": _TYPE_MAP.get(resource_type, "other"),
            "is_oa": bool(pdfs) or str(meta.get("access_right") or "") == "open",
            "pdf_candidates": pdfs,
        })
    return out
