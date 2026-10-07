"""OSF Preprints (dont AfricArXiv) — prépublications, dont travaux africains.

Deux appels : la recherche, puis la liste des fichiers du préprint retenu (pour le PDF).
"""

from . import candidate, clean, year_of

PROVIDER_ID = "osf"
SEARCH = "https://api.osf.io/v2/preprints/"
FILES = "https://api.osf.io/v2/preprints/{id}/files/osfstorage/"


def _pdf_candidates(fetcher, preprint_id: str) -> list[dict]:
    try:
        data = fetcher.fetch_json(FILES.format(id=preprint_id), {"page[size]": 10})
    except Exception:  # noqa: BLE001 — l'absence de fichiers ne doit pas casser la recherche
        return []
    out = []
    for item in data.get("data", []):
        attributes = item.get("attributes") or {}
        name = str(attributes.get("name") or "")
        url = ((item.get("links") or {}).get("download")) or ""
        if url and (name.lower().endswith(".pdf") or "pdf" in str(attributes.get("kind") or "")):
            out.append(candidate(url, "repository"))
    return out


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(SEARCH, {"filter[title]": query, "page[size]": limit})
    items = data.get("data") or []
    if not items:
        data = fetcher.fetch_json(SEARCH, {"page[size]": limit})
        items = data.get("data") or []
    out = []
    for item in items:
        attributes = item.get("attributes") or {}
        links = item.get("links") or {}
        doi = str(attributes.get("doi") or "").strip()
        out.append({
            "title": clean(attributes.get("title"), 500),
            "authors": [str((c or {}).get("name") or "")
                        for c in ((attributes.get("contributors") or {}).get("data") or [])][:12],
            "year": year_of(attributes.get("date_published")),
            "venue": clean(str((attributes.get("provider") or {}).get("name") or "OSF"), 300),
            "doi": doi,
            "url": links.get("html") or "",
            "language": "en",
            "abstract": clean(attributes.get("description"), 4000),
            "document_type": "preprint",
            "is_oa": True,
            "pdf_candidates": _pdf_candidates(fetcher, item.get("id") or ""),
        })
    return out
