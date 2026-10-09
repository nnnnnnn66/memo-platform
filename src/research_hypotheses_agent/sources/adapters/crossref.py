"""Crossref — registre officiel des DOI (gratuit, sans clé). Repli du gap check (429 OpenAlex)."""

from . import clean, first, year_of

PROVIDER_ID = "crossref"
ENDPOINT = "https://api.crossref.org/works"


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
            "language": (item.get("language") or "")[:8],
            "provider": PROVIDER_ID,
        })
    return out
