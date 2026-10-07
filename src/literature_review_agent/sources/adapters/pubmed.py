"""PubMed — E-utilities de la NLM (deux appels : esearch puis esummary)."""

from . import candidate, clean, year_of

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
    }, cost=1)
    result = summary.get("result") or {}
    out = []
    for pmid in ids[:limit]:
        item = result.get(pmid) or {}
        doi = ""
        pmcid = ""
        for identifier in item.get("articleids") or []:
            kind = (identifier or {}).get("idtype")
            if kind == "doi":
                doi = (identifier.get("value") or "").strip()
            elif kind == "pmc":
                pmcid = (identifier.get("value") or "").strip()
        pdfs = []
        if pmcid:
            pdfs.append(candidate(f"https://europepmc.org/api/fulltextRepo?pprId={pmcid}&type=FILE",
                                  "repository"))
        out.append({
            "title": clean(item.get("title"), 500),
            "authors": [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")][:12],
            "year": year_of(item.get("pubdate")),
            "venue": clean(item.get("fulljournalname") or item.get("source") or "PubMed", 300),
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"),
            "language": (item.get("lang", [""]) or [""])[0][:8],
            "abstract": "",
            "document_type": "article",
            "is_oa": bool(pmcid),
            "pdf_candidates": pdfs,
        })
    return out
