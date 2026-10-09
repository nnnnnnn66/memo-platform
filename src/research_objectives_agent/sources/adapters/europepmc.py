"""Europe PMC — littérature biomédicale avec statut d'accès et lien texte intégral."""

from . import candidate, clean, year_of

PROVIDER_ID = "europepmc"
ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _pdfs(item: dict) -> list[dict]:
    out = []
    url_list = ((item.get("fullTextUrlList") or {}).get("fullTextUrl")) or []
    for entry in url_list:
        url = (entry or {}).get("url") or ""
        style = str((entry or {}).get("documentStyle") or "")
        availability = str((entry or {}).get("availabilityCode") or "")
        if url and (style == "pdf" or url.lower().endswith(".pdf")) and availability in ("OA", "F"):
            out.append(candidate(url, "repository", str(item.get("license") or "")))
    return out


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {
        "query": query, "format": "json", "pageSize": limit, "resultType": "core",
    })
    results = ((data.get("resultList") or {}).get("result")) or []
    out = []
    for item in results:
        doi = (item.get("doi") or "").strip()
        pmid = str(item.get("pmid") or "").strip()
        journal = ((item.get("journalInfo") or {}).get("journal") or {}).get("title")
        authors = [a.strip() for a in str(item.get("authorString") or "").rstrip(".").split(",")
                   if a.strip()]
        out.append({
            "title": clean(item.get("title"), 500),
            "provider": PROVIDER_ID,
            "authors": authors[:12],
            "year": year_of(item.get("pubYear") or item.get("firstPublicationDate")),
            "venue": clean(journal or item.get("journalTitle") or "Europe PMC", 300),
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else
                    (f"https://europepmc.org/article/MED/{pmid}" if pmid else "")),
            "language": (item.get("language") or "")[:8],
            "abstract": clean(item.get("abstractText"), 4000),
            "document_type": "article",
            "is_oa": str(item.get("isOpenAccess") or "").upper() in ("Y", "YES", "TRUE"),
            "pdf_candidates": _pdfs(item),
        })
    return out
