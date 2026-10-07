"""arXiv — prépublications (Atom XML, stdlib xml.etree)."""

import xml.etree.ElementTree as ET

from . import candidate, clean, year_of

PROVIDER_ID = "arxiv"
ENDPOINT = "https://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom"}
_FETCH_MAX = 25


def search(fetcher, query: str, limit: int) -> list[dict]:
    limit = max(1, min(int(limit), _FETCH_MAX))
    text = fetcher.fetch(ENDPOINT, {
        "search_query": f"all:{query}", "max_results": limit, "start": 0,
    })
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    out = []
    for entry in root.findall("a:entry", _NS):
        identifier = (entry.findtext("a:id", "", _NS) or "").strip()
        landing = identifier
        pdf_url = ""
        for node in entry.findall("a:link", _NS):
            if node.get("rel") == "alternate" and node.get("href"):
                landing = node.get("href")
            if node.get("title") == "pdf" and node.get("href"):
                pdf_url = node.get("href")
        authors = [a.findtext("a:name", "", _NS) for a in entry.findall("a:author", _NS)]
        out.append({
            "title": clean(entry.findtext("a:title", "", _NS), 500),
            "authors": [a for a in authors if a][:12],
            "year": year_of((entry.findtext("a:published", "", _NS) or "")[:4]),
            "venue": "arXiv (prépublication)",
            "doi": (entry.findtext("{http://arxiv.org/schemas/atom}doi", "", _NS) or "").strip(),
            "url": landing,
            "language": "en",
            "abstract": clean(entry.findtext("a:summary", "", _NS), 4000),
            "document_type": "preprint",
            "is_oa": True,
            "pdf_candidates": [candidate(pdf_url, "repository")] if pdf_url else [],
        })
    return out
