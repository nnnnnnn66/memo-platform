"""theses.fr — thèses soutenues en France (API v1, gratuite, sans clé).

Aucun PDF n'est hébergé par theses.fr : l'agent fournit la métadonnée et le lien de la notice.
La résolution du texte intégral pour les thèses se fait ensuite via HAL (recherche par NNT).
"""

from . import clean, first

PROVIDER_ID = "theses_fr"
ENDPOINT = "https://theses.fr/api/v1/theses/recherche/"


def _authors(items) -> list[str]:
    out = []
    for item in items or []:
        name = " ".join(x for x in [(item or {}).get("prenom"), (item or {}).get("nom")] if x)
        if name:
            out.append(name)
    return out


def search(fetcher, query: str, limit: int) -> list[dict]:
    data = fetcher.fetch_json(ENDPOINT, {"q": query, "nombre": limit})
    out = []
    for item in data.get("theses", []):
        nnt = (item.get("nnt") or "").strip()
        resume = item.get("resume")
        out.append({
            "title": clean(item.get("titrePrincipal"), 500),
            "authors": _authors(item.get("auteurs"))[:12],
            "year": None,  # dateSoutenance est au format jj/mm/aaaa : calculé ci-dessous
            "publication_date_raw": item.get("dateSoutenance") or "",
            "venue": clean(item.get("etabSoutenanceN"), 300),
            "doi": (item.get("doi") or "").strip(),
            "url": (f"https://theses.fr/{nnt}" if nnt else ""),
            "language": "fr",
            "abstract": clean(resume, 4000) if isinstance(resume, str) else "",
            "document_type": "thesis",
            "is_oa": False,
            "pdf_candidates": [],
            "thesis_nnt": nnt,
            "discipline": first(item.get("discipline"), "") or "",
        })
        if out[-1]["publication_date_raw"]:
            parts = out[-1]["publication_date_raw"].split("/")
            if len(parts) == 3 and parts[2].isdigit():
                out[-1]["year"] = int(parts[2])
    return out
