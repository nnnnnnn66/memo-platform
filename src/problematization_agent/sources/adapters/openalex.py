"""OpenAlex — publications (gratuit). Adaptateur du gap check.

OpenAlex est le plus large index généraliste, mais son quota gratuit est **partagé par toute
l'adresse IP** : depuis ce serveur il répond `429` (budget épuisé, réinitialisation à minuit UTC).

Une **clé OpenAlex gratuite** lève cette limite : elle a son propre quota (10× le budget sans clé).
La clé est un SECRET : elle n'est jamais écrite ici, ni dans la configuration, ni dans les journaux.
Elle est lue dans l'environnement, sous `OPENALEX_API_KEY` (à placer dans `~/.hermes/.env`).
Sans clé, l'adaptateur fonctionne exactement comme avant (requête anonyme).
"""

import os

from . import clean, first, year_of

PROVIDER_ID = "openalex"
ENDPOINT = "https://api.openalex.org/works"
ENV_VAR = "OPENALEX_API_KEY"


def api_key() -> str:
    """Clé OpenAlex fournie par l'environnement (vide si non configurée). Jamais journalisée."""
    return (os.environ.get(ENV_VAR) or "").strip()


def search(fetcher, query: str, limit: int) -> list[dict]:
    params = {"search": query, "per-page": limit, "sort": "relevance_score:desc"}
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
        doi = (work.get("doi") or "").replace("https://doi.org/", "").strip()
        location = work.get("primary_location") or {}
        journal = (location.get("source") or {}) or {}
        out.append({
            "title": clean(work.get("display_name"), 500),
            "authors": [a.get("author", {}).get("display_name", "")
                        for a in (work.get("authorships") or [])[:12]
                        if a.get("author", {}).get("display_name")],
            "year": year_of(work.get("publication_date")),
            "venue": clean(journal.get("display_name"), 300),
            "doi": doi,
            "url": (work.get("doi") or work.get("id") or "").strip(),
            "language": (work.get("language") or "")[:8],
            "provider": PROVIDER_ID,
        })
    return out
