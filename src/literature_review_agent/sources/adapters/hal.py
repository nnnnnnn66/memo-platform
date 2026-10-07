"""HAL — dépôts universitaires francophones, thèses incluses (gratuit, sans clé)."""

from . import candidate, clean, first, year_of

PROVIDER_ID = "hal"
ENDPOINT = "https://api.archives-ouvertes.fr/search/"
_FIELDS = ("title_s,uri_s,doiId_s,producedDate_s,abstract_s,journalTitle_s,fileMain_s,files_s,"
           "language_s,authFullName_s,docType_s,nntId_s")


def _pdfs(doc: dict) -> list[dict]:
    out = []
    main = doc.get("fileMain_s")
    if main:
        out.append(candidate(str(main), "repository"))
    for files in doc.get("files_s") or []:
        if str(files).lower().endswith(".pdf"):
            out.append(candidate(str(files), "repository"))
    return out


def _type(doc: dict) -> str:
    raw = " ".join(doc.get("docType_s") or []) if isinstance(doc.get("docType_s"), list) \
        else str(doc.get("docType_s") or "")
    raw = raw.upper()
    if "THESE" in raw or "HDR" in raw:
        return "thesis"
    if "OUVRAGE" in raw or "BOOK" in raw:
        return "book"
    if "RAPPORT" in raw or "REPORT" in raw:
        return "report"
    return "article"


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "fl": _FIELDS, "rows": limit, "wt": "json"})
    docs = ((data.get("response") or {}).get("docs")) or []
    out = []
    for doc in docs:
        out.append({
            "title": clean(first(doc.get("title_s")), 500),
            "authors": [str(a) for a in (doc.get("authFullName_s") or [])][:12],
            "year": year_of(first(doc.get("producedDate_s"))),
            "venue": clean(first(doc.get("journalTitle_s")) or "HAL", 300),
            "doi": str(first(doc.get("doiId_s"), "") or "").strip(),
            "url": str(first(doc.get("uri_s"), "") or "").strip(),
            "language": str(first(doc.get("language_s"), "") or "")[:8],
            "abstract": clean(first(doc.get("abstract_s")), 4000),
            "document_type": _type(doc),
            "is_oa": bool(doc.get("fileMain_s")),
            "pdf_candidates": _pdfs(doc),
            "thesis_nnt": str(first(doc.get("nntId_s"), "") or ""),
        })
    return out


def find_by_nnt(fetcher, nnt: str) -> dict | None:
    """Retrouve la notice HAL d'une thèse par son NNT (pour obtenir le texte intégral)."""
    if not nnt:
        return None
    try:
        data = fetcher.fetch_json(ENDPOINT, {
            "q": f'nntId_s:"{nnt}"', "fl": _FIELDS, "rows": 1, "wt": "json",
        })
    except Exception:  # noqa: BLE001
        return None
    docs = ((data.get("response") or {}).get("docs")) or []
    if not docs:
        return None
    doc = docs[0]
    return {
        "url": str(first(doc.get("uri_s"), "") or ""),
        "is_oa": bool(doc.get("fileMain_s")),
        "pdf_candidates": _pdfs(doc),
    }
