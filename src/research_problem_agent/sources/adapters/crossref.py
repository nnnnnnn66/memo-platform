"""Crossref — registre officiel des DOI (gratuit, sans clé)."""

from . import clean, first

PROVIDER_ID = "crossref"
ENDPOINT = "https://api.crossref.org/works"


def _date(item: dict) -> str:
    parts = ((item.get("issued") or {}).get("date-parts") or [[]])[0]
    if not parts or not parts[0]:
        return ""
    if len(parts) >= 3 and parts[1] and parts[2]:
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    if len(parts) >= 2 and parts[1]:
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}"
    return f"{int(parts[0]):04d}"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"query": query, "rows": limit})
    out = []
    for item in (data.get("message") or {}).get("items", []):
        doi = (item.get("DOI") or "").strip()
        out.append({
            "source": clean(first(item.get("container-title"), first(item.get("publisher"), "Crossref")), 300),
            "title": clean(first(item.get("title")), 500),
            "url": (item.get("URL") or (f"https://doi.org/{doi}" if doi else "")).strip(),
            "doi": doi,
            "publication_date": _date(item),
            "snippet": clean(item.get("abstract"), 1200),
        })
    return out
