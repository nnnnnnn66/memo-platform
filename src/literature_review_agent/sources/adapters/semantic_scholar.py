"""Semantic Scholar — moteur scientifique (gratuit, sans clé).

Complète OpenAlex et Crossref : découverte de travaux liés et couverture plus large. L'API publique
est **gratuite sans clé** ; elle est limitée en débit (quelques requêtes par seconde), d'où la
reprise sur `429` déjà assurée par le `fetcher`. Une clé **facultative** (`SEMANTIC_SCHOLAR_API_KEY`,
gratuite sur demande) élève ce quota : elle est lue dans l'environnement et transmise en EN-TÊTE
`x-api-key`, jamais dans l'URL.

Règle du projet : aucune URL de PDF n'est construite à la main — celle-ci vient de l'API
(`openAccessPdf`), et le téléchargement reste soumis aux règles d'accès de `fulltext.py`.
"""

import os

from . import candidate, clean, year_of

PROVIDER_ID = "semanticscholar"
ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
ENV_VAR = "SEMANTIC_SCHOLAR_API_KEY"
FIELDS = "title,authors,year,venue,externalIds,abstract,openAccessPdf,publicationTypes,url"

_TYPE_MAP = {
    "journalarticle": "article", "review": "article", "conference": "article",
    "book": "book", "booksection": "book", "thesis": "thesis", "report": "report",
    "dataset": "dataset", "clinicaltrial": "article", "study": "article",
}


def api_key() -> str:
    """Clé facultative fournie par l'environnement (vide si non configurée). Jamais journalisée."""
    return (os.environ.get(ENV_VAR) or "").strip()


def _document_type(types) -> str:
    for kind in types or []:
        key = str(kind).replace("_", "").replace("-", "").lower()
        if key in _TYPE_MAP:
            return _TYPE_MAP[key]
    return "other"


def search(fetcher, query: str, limit: int) -> list[dict]:
    params = {"query": query, "limit": max(1, min(100, limit)), "fields": FIELDS}
    headers: dict = {}
    key = api_key()
    if key:
        headers["x-api-key"] = key
    data = fetcher.fetch_json(ENDPOINT, params, headers=headers)
    out = []
    for paper in data.get("data") or []:
        if not isinstance(paper, dict):
            continue
        ids = paper.get("externalIds") or {}
        doi = str(ids.get("DOI") or "").strip()
        oa = paper.get("openAccessPdf") or {}
        pdf_url = str(oa.get("url") or "").strip()
        out.append({
            "title": clean(paper.get("title"), 500),
            "authors": [a.get("name", "") for a in (paper.get("authors") or [])[:12]
                        if isinstance(a, dict) and a.get("name")],
            "year": year_of(paper.get("year")),
            "venue": clean(paper.get("venue"), 300),
            "doi": doi,
            "url": str(paper.get("url") or (f"https://doi.org/{doi}" if doi else "")).strip(),
            "volume": "",
            "issue": "",
            "pages": "",
            "language": "",
            "abstract": clean(paper.get("abstract"), 4000),
            "document_type": _document_type(paper.get("publicationTypes")),
            "is_oa": bool(pdf_url),
            "pdf_candidates": [candidate(pdf_url, "repository")] if pdf_url else [],
        })
    return out
