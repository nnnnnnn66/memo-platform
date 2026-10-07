"""Europe PMC — littérature biomédicale, résumés inclus (gratuit, sans clé)."""

from . import clean

PROVIDER_ID = "europepmc"
ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {
        "query": query, "format": "json", "pageSize": limit, "resultType": "core",
    })
    results = ((data.get("resultList") or {}).get("result")) or []
    out = []
    for item in results:
        doi = (item.get("doi") or "").strip()
        pmid = str(item.get("pmid") or "").strip()
        url = (f"https://doi.org/{doi}" if doi else
               (f"https://europepmc.org/article/MED/{pmid}" if pmid else ""))
        out.append({
            "source": clean(item.get("journalInfo", {}).get("journal", {}).get("title")
                            or item.get("journalTitle") or "Europe PMC", 300),
            "title": clean(item.get("title"), 500),
            "url": url,
            "doi": doi,
            "publication_date": str(item.get("pubYear") or "").strip(),
            "snippet": clean(item.get("abstractText"), 1200),
        })
    return out
