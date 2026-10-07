"""OpenAIRE Graph — recherche financée publiquement (gratuit, sans clé)."""

from . import clean, first

PROVIDER_ID = "openaire"
ENDPOINT = "https://api.openaire.eu/graph/v1/researchProducts"


def _doi(node: dict) -> str:
    for pid in node.get("pids") or []:
        if (pid or {}).get("scheme") == "doi" and pid.get("value"):
            return str(pid["value"]).strip()
    for value in node.get("originalIds") or []:
        text = str(value)
        if text.startswith("10.") and "/" in text:
            return text.strip()
    return ""


def _url(node: dict, doi: str) -> str:
    for instance in node.get("instances") or []:
        for url in (instance or {}).get("urls") or []:
            if url:
                return str(url).strip()
    return f"https://doi.org/{doi}" if doi else ""


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"search": query, "pageSize": limit})
    out = []
    for node in data.get("results", []):
        doi = _doi(node)
        descriptions = node.get("descriptions") or []
        out.append({
            "source": clean((node.get("container") or {}).get("name")
                            or node.get("publisher") or "OpenAIRE", 300),
            "title": clean(node.get("mainTitle"), 500),
            "url": _url(node, doi),
            "doi": doi,
            "publication_date": str(node.get("publicationDate") or "").strip()[:10],
            "snippet": clean(first(descriptions, ""), 1200),
        })
    return out
