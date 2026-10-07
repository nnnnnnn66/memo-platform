"""data.gouv.fr — données publiques françaises (gratuit, sans clé)."""

from . import clean

PROVIDER_ID = "datagouv"
ENDPOINT = "https://www.data.gouv.fr/api/1/datasets/"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "page_size": limit})
    out = []
    for item in data.get("data", []):
        organization = (item.get("organization") or {}).get("name") or "data.gouv.fr"
        out.append({
            "source": clean(organization, 300),
            "title": clean(item.get("title"), 500),
            "url": (item.get("page") or "").strip(),
            "doi": "",
            "publication_date": str(item.get("created_at") or "")[:10],
            "snippet": clean(item.get("description"), 1200),
        })
    return out
