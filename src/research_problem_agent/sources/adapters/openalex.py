"""OpenAlex — métadonnées de publications scientifoptimisées (gratuit, sans clé)."""

from . import clean

PROVIDER_ID = "openalex"
ENDPOINT = "https://api.openalex.org/works"


def _abstract(work: dict) -> str:
    """Reconstruit le résumé depuis l'index inversé d'OpenAlex."""
    index = work.get("abstract_inverted_index")
    if not isinstance(index, dict):
        return ""
    positions: dict[int, str] = {}
    for word, slots in index.items():
        for slot in slots or []:
            positions[int(slot)] = word
    if not positions:
        return ""
    return " ".join(positions[i] for i in sorted(positions))


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"search": query, "per-page": limit})
    out = []
    for work in data.get("results", []):
        location = work.get("primary_location") or {}
        journal = (location.get("source") or {}) or {}
        out.append({
            "source": journal.get("display_name") or "OpenAlex",
            "title": clean(work.get("display_name"), 500),
            "url": (work.get("doi") or work.get("id") or "").strip(),
            "doi": (work.get("doi") or "").replace("https://doi.org/", "").strip(),
            "publication_date": (work.get("publication_date") or "").strip(),
            "snippet": clean(_abstract(work), 1200),
        })
    return out
