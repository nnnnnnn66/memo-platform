"""OpenAIRE Graph — recherche financée publiquement, dépôts institutionnels."""

from . import candidate, clean, first, year_of

PROVIDER_ID = "openaire"
ENDPOINT = "https://api.openaire.eu/graph/v1/researchProducts"

_TYPE_MAP = {"publication": "article", "dataset": "dataset", "software": "other",
             "other": "other", "doctoralThesis": "thesis"}


def _doi(node: dict) -> str:
    for pid in node.get("pids") or []:
        if (pid or {}).get("scheme") == "doi" and pid.get("value"):
            return str(pid["value"]).strip()
    for value in node.get("originalIds") or []:
        text = str(value)
        if text.startswith("10.") and "/" in text:
            return text.strip()
    return ""


def _pdfs(node: dict) -> list[dict]:
    out = []
    for instance in node.get("instances") or []:
        for url in (instance or {}).get("urls") or []:
            text = str(url)
            if text.lower().endswith(".pdf"):
                out.append(candidate(text, "repository", str((instance or {}).get("license") or "")))
    if not out:
        for instance in node.get("instances") or []:
            urls = (instance or {}).get("urls") or []
            if urls:
                out.append(candidate(str(urls[0]), "repository"))
    return out


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"search": query, "pageSize": limit})
    out = []
    for node in data.get("results", []):
        doi = _doi(node)
        container = node.get("container") or {}
        descriptions = node.get("descriptions") or []
        access = str((node.get("bestAccessRight") or {}).get("label") or "")
        out.append({
            "title": clean(node.get("mainTitle"), 500),
            "provider": PROVIDER_ID,
            "authors": [str((a or {}).get("fullName") or "") for a in (node.get("authors") or [])][:12],
            "year": year_of(node.get("publicationDate")),
            "venue": clean(container.get("name") or node.get("publisher") or "OpenAIRE", 300),
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else
                    (f"https://explore.openaire.eu/search/publication?pid={node.get('id')}"
                     if node.get("id") else "")),
            "language": str((node.get("language") or {}).get("code") or "")[:8],
            "abstract": clean(first(descriptions, ""), 4000),
            "document_type": _TYPE_MAP.get(str(node.get("type") or ""), "article"),
            "is_oa": access.upper() in ("OPEN", "OPEN SOURCE", "OA"),
            "pdf_candidates": _pdfs(node),
        })
    return out
