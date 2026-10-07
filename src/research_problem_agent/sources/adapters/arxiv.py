"""arXiv — prépublications (gratuit, sans clé). Réponse Atom XML (stdlib xml.etree)."""

import xml.etree.ElementTree as ET

from . import clean

PROVIDER_ID = "arxiv"
ENDPOINT = "https://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom"}
_FETCH_MAX = 10


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
        link = ""
        for node in entry.findall("a:link", _NS):
            if node.get("rel") == "alternate" and node.get("href"):
                link = node.get("href")
                break
        identifier = (entry.findtext("a:id", "", _NS) or "").strip()
        out.append({
            "source": "arXiv (prépublication)",
            "title": clean(entry.findtext("a:title", "", _NS), 500),
            "url": link or identifier,
            "doi": "",
            "publication_date": (entry.findtext("a:published", "", _NS) or "")[:10],
            "snippet": clean(entry.findtext("a:summary", "", _NS), 1200),
        })
    return out
