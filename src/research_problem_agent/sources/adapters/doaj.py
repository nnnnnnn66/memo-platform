"""DOAJ — Directory of Open Access Journals (gratuit, sans clé)."""

from . import clean, first

PROVIDER_ID = "doaj"
ENDPOINT = "https://doaj.org/api/search/articles"


def _doi(identifiers) -> str:
    for item in identifiers or []:
        if (item or {}).get("type") == "doi":
            return (item.get("id") or "").strip()
    return ""


def _fulltext_url(links) -> str:
    for link in links or []:
        if (link or {}).get("type") == "fulltext" and link.get("url"):
            return link["url"].strip()
    return (first(links) or {}).get("url", "").strip()


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(f"{ENDPOINT}/{query}", {"pageSize": limit})
    out = []
    for item in data.get("results", []):
        bib = item.get("bibjson") or {}
        doi = _doi(bib.get("identifier"))
        out.append({
            "source": clean((bib.get("journal") or {}).get("title") or "DOAJ", 300),
            "title": clean(bib.get("title"), 500),
            "url": _fulltext_url(bib.get("link")) or (f"https://doi.org/{doi}" if doi else ""),
            "doi": doi,
            "publication_date": str(bib.get("year") or "").strip(),
            "snippet": clean(bib.get("abstract"), 1200),
        })
    return out
