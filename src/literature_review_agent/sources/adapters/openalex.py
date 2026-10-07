"""OpenAlex — publications, chapitres et thèses (gratuit).

Le quota gratuit d'OpenAlex est **partagé par toute l'adresse IP** : depuis ce serveur il répond
parfois `429`. Une **clé OpenAlex gratuite** lève cette limite (quota propre, 10× le budget
anonyme). La clé est un SECRET : elle n'est jamais écrite ici, ni dans la configuration, ni dans
les journaux ; elle est lue dans l'environnement sous `OPENALEX_API_KEY` (à placer dans
`~/.hermes/.env`) et transmise en en-tête `Authorization` — jamais dans l'URL. Sans clé,
l'adaptateur fonctionne exactement comme avant (requête anonyme).
"""

import os

from . import candidate, clean, first, year_of

PROVIDER_ID = "openalex"
ENDPOINT = "https://api.openalex.org/works"
ENV_VAR = "OPENALEX_API_KEY"


def api_key() -> str:
    """Clé OpenAlex fournie par l'environnement (vide si non configurée). Jamais journalisée."""
    return (os.environ.get(ENV_VAR) or "").strip()

_TYPE_MAP = {
    "article": "article", "review": "article", "book-chapter": "book", "book": "book",
    "dissertation": "thesis", "report": "report", "dataset": "dataset", "preprint": "preprint",
}


def _abstract(work: dict) -> str:
    index = work.get("abstract_inverted_index")
    if not isinstance(index, dict):
        return ""
    positions: dict[int, str] = {}
    for word, slots in index.items():
        for slot in slots or []:
            positions[int(slot)] = word
    return " ".join(positions[i] for i in sorted(positions)) if positions else ""


def search(fetcher, query: str, limit: int) -> list[dict]:
    params = {"search": query, "per-page": limit}
    email = (fetcher.cfg or {}).get("polite_email")
    if email:
        params["mailto"] = email
    headers: dict = {}
    key = api_key()
    if key:
        # En-tête, pas paramètre d'URL : la clé ne doit jamais apparaître dans une URL journalisée.
        headers["Authorization"] = f"Bearer {key}"
    data = fetcher.fetch_json(ENDPOINT, params, headers=headers)
    out = []
    for work in data.get("results", []):
        location = work.get("primary_location") or {}
        journal = (location.get("source") or {}) or {}
        best = work.get("best_oa_location") or {}
        open_access = work.get("open_access") or {}
        doi = (work.get("doi") or "").replace("https://doi.org/", "").strip()
        pdfs = []
        for url in (best.get("pdf_url"), location.get("pdf_url")):
            if url:
                pdfs.append(candidate(url, "repository" if "repository" in str(best.get("host_type")) else "publisher",
                                      str(best.get("license") or "")))
        out.append({
            "title": clean(work.get("display_name"), 500),
            "authors": [a.get("author", {}).get("display_name", "")
                        for a in (work.get("authorships") or [])[:12]
                        if a.get("author", {}).get("display_name")],
            "year": year_of(work.get("publication_date")),
            "venue": clean(journal.get("display_name"), 300),
            "doi": doi,
            "url": (work.get("doi") or work.get("id") or "").strip(),
            "volume": str((work.get("biblio") or {}).get("volume") or ""),
            "issue": str((work.get("biblio") or {}).get("issue") or ""),
            "pages": "-".join(str(x) for x in [
                (work.get("biblio") or {}).get("first_page"), (work.get("biblio") or {}).get("last_page")
            ] if x),
            "language": (work.get("language") or "")[:8],
            "abstract": clean(_abstract(work), 4000),
            "document_type": _TYPE_MAP.get(work.get("type"), "other"),
            "is_oa": bool(open_access.get("is_oa")),
            "pdf_candidates": [p for p in pdfs if p["url"]],
        })
    return out
