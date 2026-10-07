"""data.europa.eu — portail open data de l'Union européenne (gratuit, sans clé)."""

from . import clean, multilingual

PROVIDER_ID = "dataeuropa"
ENDPOINT = "https://data.europa.eu/api/hub/search/search"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "limit": limit})
    results = ((data.get("result") or {}).get("results")) or []
    out = []
    for item in results:
        publisher = item.get("publisher") or {}
        out.append({
            "source": clean(publisher.get("name") if isinstance(publisher, dict) else publisher,
                            300) or "data.europa.eu",
            "title": clean(multilingual(item.get("title")), 500),
            "url": (item.get("resource") or item.get("landing_page") or "").strip(),
            "doi": "",
            "publication_date": str(item.get("issued") or "")[:10],
            "snippet": clean(multilingual(item.get("description")), 1200),
        })
    return out
