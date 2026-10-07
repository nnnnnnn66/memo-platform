"""DOAJ — revues en accès ouvert (gratuit, sans clé)."""

import urllib.parse

from . import candidate, clean, first, year_of

PROVIDER_ID = "doaj"
ENDPOINT = "https://doaj.org/api/search/articles"


def _doi(identifiers) -> str:
    for item in identifiers or []:
        if (item or {}).get("type") == "doi":
            return (item.get("id") or "").strip()
    return ""


def _pdfs(links) -> list[dict]:
    out = []
    for link in links or []:
        url = (link or {}).get("url") or ""
        content_type = str((link or {}).get("content_type") or "")
        if url and ("pdf" in content_type or url.lower().endswith(".pdf")):
            out.append(candidate(url, "publisher"))
    return out


def search(fetcher, query: str, limit: int) -> list[dict]:
    # DOAJ attend la requête dans le CHEMIN : elle doit être encodée (accents, espaces, « / »).
    encoded = urllib.parse.quote(query, safe="")
    data = fetcher.fetch_json(f"{ENDPOINT}/{encoded}", {"pageSize": limit})
    out = []
    for item in data.get("results", []):
        bib = item.get("bibjson") or {}
        doi = _doi(bib.get("identifier"))
        journal = bib.get("journal") or {}
        authors = [a.get("name", "") for a in (bib.get("author") or []) if a.get("name")]
        out.append({
            "title": clean(bib.get("title"), 500),
            "provider": PROVIDER_ID,
            "authors": authors[:12],
            "year": year_of(bib.get("year")),
            "venue": clean(journal.get("title") or "DOAJ", 300),
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else
                    (first([l.get("url") for l in (bib.get("link") or [])], "") or "")),
            "language": (first(bib.get("language"), "") or "")[:8],
            "abstract": clean(bib.get("abstract"), 4000),
            "document_type": "article",
            "is_oa": True,  # DOAJ indexe exclusivement des revues en accès ouvert
            "pdf_candidates": _pdfs(bib.get("link")),
        })
    return out
