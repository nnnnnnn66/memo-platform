"""data.europa.eu — portail open data de l'Union européenne (gratuit, sans clé)."""

from . import candidate, clean, multilingual, year_of

PROVIDER_ID = "dataeuropa"
ENDPOINT = "https://data.europa.eu/api/hub/search/search"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "limit": limit})
    results = ((data.get("result") or {}).get("results")) or []
    out = []
    for item in results:
        publisher = item.get("publisher") or {}
        name = publisher.get("name") if isinstance(publisher, dict) else publisher
        url = (item.get("resource") or item.get("landing_page") or "").strip()
        out.append({
            "title": clean(multilingual(item.get("title")), 500),
            "authors": [clean(name, 200)] if name else [],
            "year": year_of(item.get("issued")),
            "venue": clean(name or "data.europa.eu", 300),
            "doi": "",
            "url": url,
            "language": "en",
            "abstract": clean(multilingual(item.get("description")), 4000),
            "document_type": "dataset",
            "is_oa": True,
            "pdf_candidates": [candidate(url, "repository")] if url.lower().endswith(".pdf") else [],
        })
    return out
