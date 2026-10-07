"""DataCite — DOI de données et de dépôts (gratuit, sans clé)."""

from . import clean, first

PROVIDER_ID = "datacite"
ENDPOINT = "https://api.datacite.org/dois"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(f"{ENDPOINT}", {"query": query, "page[size]": limit})
    out = []
    for item in data.get("data", []):
        attrs = item.get("attributes") or {}
        doi = (attrs.get("doi") or "").strip()
        description = first(attrs.get("descriptions"), {}) or {}
        out.append({
            "source": clean(attrs.get("publisher") or "DataCite", 300),
            "title": clean(first(attrs.get("titles"), {}).get("title"), 500),
            "url": (attrs.get("url") or (f"https://doi.org/{doi}" if doi else "")).strip(),
            "doi": doi,
            "publication_date": str(attrs.get("publicationYear") or "").strip(),
            "snippet": clean(description.get("description"), 1200),
        })
    return out
