"""Adaptateurs du gap check : normalisation requête → publications candidates.

Chaque module expose `PROVIDER_ID` et `search(fetcher, query, limit) -> list[dict]`.
Le dict normalisé contient : title, authors[], year, venue, doi, url, language, provider.
Aucun LLM, aucune clé, aucun coût.
"""

import html
import re

_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def clean(text, limit: int = 1200) -> str:
    """Nettoie un texte de source : tags HTML/JATS retirés, espaces normalisés, borné."""
    if not text:
        return ""
    out = html.unescape(_TAGS.sub(" ", str(text)))
    out = _SPACES.sub(" ", out).strip()
    return out[:limit]


def first(value, default=None):
    if isinstance(value, (list, tuple)):
        return value[0] if value else default
    return value if value is not None else default


def year_of(value) -> int | None:
    """Extrait une année d'une chaîne ou d'un entier, sinon None."""
    if value is None:
        return None
    match = re.search(r"(1[5-9]\d{2}|20\d{2}|21\d{2})", str(value))
    return int(match.group(1)) if match else None


def candidate(url: str, host_kind: str = "repository", license: str = "") -> dict:
    """Candidate de texte intégral : uniquement des URL fournies par l'API du fournisseur."""
    return {"url": (url or "").strip(), "host_kind": host_kind, "license": license or ""}
