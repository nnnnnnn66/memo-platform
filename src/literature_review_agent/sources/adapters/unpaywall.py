"""Unpaywall — enrichissement « accès ouvert » : localisations légales du texte intégral.

Ce n'est pas un moteur de recherche : c'est un service d'enrichissement appelé par DOI.
Gratuit, sans clé (un e-mail de courtoisie est requis par l'API).
"""

from . import candidate

PROVIDER_ID = "unpaywall"
ENDPOINT = "https://api.unpaywall.org/v2/{doi}"


def lookup(fetcher, doi: str) -> dict:
    """Retourne {is_oa, oa_status, license, pdf_candidates[], landing_urls[]}."""
    doi = (doi or "").strip()
    if not doi:
        return {"is_oa": False, "oa_status": "", "license": "", "pdf_candidates": [],
                "landing_urls": []}
    email = (fetcher.cfg or {}).get("polite_email") or "contact@example.org"
    try:
        data = fetcher.fetch_json(ENDPOINT.format(doi=doi), {"email": email})
    except Exception as exc:  # noqa: BLE001 — l'enrichissement ne doit jamais casser le flux
        fetcher.errors.append(f"unpaywall {doi}: {type(exc).__name__}")
        return {"is_oa": False, "oa_status": "", "license": "", "pdf_candidates": [],
                "landing_urls": []}

    pdfs: list[dict] = []
    landings: list[str] = []
    for location in data.get("oa_locations") or []:
        location = location or {}
        license_ = str(location.get("license") or "")
        host_type = str(location.get("host_type") or "")
        host_kind = "repository" if host_type == "repository" else "publisher"
        url_pdf = location.get("url_for_pdf")
        if url_pdf:
            pdfs.append(candidate(url_pdf, host_kind, license_))
        url_page = location.get("url") or location.get("url_for_landing_page") or ""
        if url_page:
            landings.append(str(url_page))
            if str(url_page).lower().endswith(".pdf"):
                pdfs.append(candidate(str(url_page), host_kind, license_))
    best = data.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        pdfs.insert(0, candidate(best["url_for_pdf"],
                                 "repository" if str(best.get("host_type")) == "repository"
                                 else "publisher", str(best.get("license") or "")))

    # Dédoublonnage des candidats par URL
    seen: set[str] = set()
    unique = []
    for item in pdfs:
        if item["url"] and item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return {
        "is_oa": bool(data.get("is_oa")),
        "oa_status": str(data.get("oa_status") or ""),
        "license": str(best.get("license") or ""),
        "pdf_candidates": unique,
        "landing_urls": landings,
    }
