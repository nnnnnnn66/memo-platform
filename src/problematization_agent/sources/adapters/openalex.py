"""OpenAlex — publications (gratuit, sans clé). Utilisé pour vérifier si un gap est déjà comblé."""

from . import clean, first, year_of

PROVIDER_ID = "openalex"
ENDPOINT = "https://api.openalex.org/works"


def search(fetcher, query: str, limit: int) -> list[dict]:
    params = {"search": query, "per-page": limit, "sort": "relevance_score:desc"}
    email = (fetcher.cfg or {}).get("polite_email")
    if email:
        params["mailto"] = email
    data = fetcher.fetch_json(ENDPOINT, params)
    out = []
    for work in data.get("results", []):
        doi = (work.get("doi") or "").replace("https://doi.org/", "").strip()
        location = work.get("primary_location") or {}
        journal = (location.get("source") or {}) or {}
        out.append({
            "title": clean(work.get("display_name"), 500),
            "authors": [a.get("author", {}).get("display_name", "")
                        for a in (work.get("authorships") or [])[:12]
                        if a.get("author", {}).get("display_name")],
            "year": year_of(work.get("publication_date")),
            "venue": clean(journal.get("display_name"), 300),
            "doi": doi,
            "url": (work.get("doi") or work.get("id") or "").strip(),
            "language": (work.get("language") or "")[:8],
            "provider": PROVIDER_ID,
        })
    return out
