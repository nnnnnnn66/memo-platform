"""Zenodo — dépôt pluridisciplinaire (gratuit, sans clé)."""

from . import clean

PROVIDER_ID = "zenodo"
ENDPOINT = "https://zenodo.org/api/records"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "size": limit})
    hits = ((data.get("hits") or {}).get("hits")) or []
    out = []
    for item in hits:
        meta = item.get("metadata") or {}
        doi = (item.get("doi") or meta.get("doi") or "").strip()
        html = (item.get("links") or {}).get("self_html") or ""
        out.append({
            "source": clean(meta.get("publisher") or "Zenodo", 300),
            "title": clean(meta.get("title"), 500),
            "url": (f"https://doi.org/{doi}" if doi else html).strip(),
            "doi": doi,
            "publication_date": str(meta.get("publication_date") or "").strip(),
            "snippet": clean(meta.get("description"), 1200),
        })
    return out
