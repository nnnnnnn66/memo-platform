"""HAL — dépôt universitaire francophone (gratuit, sans clé)."""

from . import clean, first

PROVIDER_ID = "hal"
ENDPOINT = "https://api.archives-ouvertes.fr/search/"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {
        "q": query,
        "fl": "title_s,uri_s,doiId_s,producedDate_s,abstract_s,journalTitle_s",
        "rows": limit,
        "wt": "json",
    })
    docs = ((data.get("response") or {}).get("docs")) or []
    out = []
    for doc in docs:
        doi = str(first(doc.get("doiId_s"), "") or "").strip()
        out.append({
            "source": clean(first(doc.get("journalTitle_s"), "HAL"), 300),
            "title": clean(first(doc.get("title_s")), 500),
            "url": str(first(doc.get("uri_s"), "") or "").strip(),
            "doi": doi,
            "publication_date": str(first(doc.get("producedDate_s"), "") or "").strip(),
            "snippet": clean(first(doc.get("abstract_s")), 1200),
        })
    return out
