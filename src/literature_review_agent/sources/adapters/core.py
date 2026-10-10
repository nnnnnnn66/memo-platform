"""CORE — agrégateur de textes intégraux en accès ouvert (gratuit, CLÉ D'API REQUISE).

CORE expose des **textes intégraux** (et non seulement des notices), ce qui en fait une source
précieuse pour l'étape « trouver et récupérer les textes intégraux » du document
d'opérationnalisation de l'Agent 3.

**Clé requise** : contrairement à OpenAlex ou Semantic Scholar, l'API v3 de CORE refuse toute
requête sans clé. L'inscription est **gratuite** (https://core.ac.uk/services/api). La clé est un
SECRET : elle n'est jamais écrite ici ni dans la configuration ; elle est lue dans l'environnement
sous `CORE_API_KEY` et transmise en en-tête `Authorization`, jamais dans l'URL.

Tant que la clé est absente, l'adaptateur ne fabrique AUCUN résultat (il renvoie une liste vide) et
le fournisseur est **désactivé** dans `providers.yaml` : il n'est donc jamais compté comme « source
interrogée ». Le jour où la clé est posée, il suffit de passer `enabled: true` — configuration, pas
code.
"""

import os

from . import candidate, clean, year_of

PROVIDER_ID = "core"
ENDPOINT = "https://api.core.ac.uk/v3/search/works"
ENV_VAR = "CORE_API_KEY"

_TYPE_MAP = {
    "journal article": "article", "article": "article", "review": "article",
    "book": "book", "book chapter": "book", "thesis": "thesis", "dissertation": "thesis",
    "report": "report", "dataset": "dataset", "research": "article",
}


def api_key() -> str:
    """Clé CORE fournie par l'environnement (vide si non configurée). Jamais journalisée."""
    return (os.environ.get(ENV_VAR) or "").strip()


def _document_type(value) -> str:
    return _TYPE_MAP.get(str(value or "").strip().lower(), "other")


def search(fetcher, query: str, limit: int) -> list[dict]:
    key = api_key()
    if not key:
        # Sans clé, l'API CORE refuse la requête : on ne prétend rien avoir interrogé.
        return []
    headers = {"Authorization": f"Bearer {key}"}
    params = {"q": query, "limit": max(1, min(100, limit))}
    data = fetcher.fetch_json(ENDPOINT, params, headers=headers)
    out = []
    for work in data.get("results") or []:
        if not isinstance(work, dict):
            continue
        authors = []
        for author in work.get("authors") or []:
            name = author.get("name") if isinstance(author, dict) else author
            if name:
                authors.append(str(name))
        doi = str(work.get("doi") or "").replace("https://doi.org/", "").strip()
        language = work.get("language") or {}
        code = language.get("code") if isinstance(language, dict) else str(language or "")
        pdfs = []
        for url in (work.get("downloadUrl"), work.get("fullTextLink")):
            if url:
                pdfs.append(candidate(str(url), "repository"))
        out.append({
            "title": clean(work.get("title"), 500),
            "authors": authors[:12],
            "year": year_of(work.get("yearPublished") or work.get("createdDate")),
            "venue": clean(work.get("publisher") or work.get("dataProvider") or "", 300),
            "doi": doi,
            "url": str(work.get("downloadUrl") or work.get("fullTextLink")
                       or (f"https://doi.org/{doi}" if doi else "")).strip(),
            "volume": "",
            "issue": "",
            "pages": "",
            "language": str(code or "")[:8],
            "abstract": clean(work.get("abstract"), 4000),
            "document_type": _document_type(work.get("documentType")),
            "is_oa": bool(pdfs),
            "pdf_candidates": [p for p in pdfs if p["url"]],
        })
    return out
