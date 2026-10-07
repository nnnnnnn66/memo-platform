"""PubMed — E-utilities de la NLM (gratuit, sans clé).

Deux appels (esearch puis esummary) : c'est le seul fournisseur qui consomme 2 requêtes.
Il est donc placé après les autres dans l'ordre de préférence (registry.FAMILY_ORDER).
"""

from . import clean

PROVIDER_ID = "pubmed"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def search(fetcher, query: str, limit: int) -> list[dict]:
    found = fetcher.fetch_json(ESEARCH, {
        "db": "pubmed", "term": query, "retmode": "json", "retmax": limit,
    })
    ids = ((found.get("esearchresult") or {}).get("idlist")) or []
    if not ids:
        return []
    summary = fetcher.fetch_json(ESUMMARY, {
        "db": "pubmed", "id": ",".join(ids[:limit]), "retmode": "json",
    })
    result = summary.get("result") or {}
    out = []
    for pmid in ids[:limit]:
        item = result.get(pmid) or {}
        doi = ""
        for identifier in item.get("articleids") or []:
            if (identifier or {}).get("idtype") == "doi":
                doi = (identifier.get("value") or "").strip()
                break
        out.append({
            "source": clean(item.get("fulljournalname") or item.get("source") or "PubMed", 300),
            "title": clean(item.get("title"), 500),
            "url": (f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"),
            "doi": doi,
            "publication_date": str(item.get("pubdate") or "").strip(),
            "snippet": "",
        })
    return out
