"""data.gouv.fr — données publiques françaises (gratuit, sans clé)."""

from . import clean, year_of

PROVIDER_ID = "datagouv"
ENDPOINT = "https://www.data.gouv.fr/api/1/datasets/"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "page_size": limit})
    out = []
    for item in data.get("data", []):
        organization = (item.get("organization") or {}).get("name") or "data.gouv.fr"
        out.append({
            "title": clean(item.get("title"), 500),
            "authors": [str(organization)],
            "year": year_of(item.get("created_at")),
            "venue": clean(organization, 300),
            "doi": "",
            "url": (item.get("page") or "").strip(),
            "language": "fr",
            "abstract": clean(item.get("description"), 4000),
            "document_type": "dataset",
            "is_oa": True,
            "pdf_candidates": [],
        })
    return out
