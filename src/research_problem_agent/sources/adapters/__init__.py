"""Adaptateurs de fournisseurs : normalisation requête → métadonnées.

Chaque module expose `PROVIDER_ID` et `search(fetcher, query, limit) -> list[dict]`.
Aucun LLM, aucune clé d'API, aucun coût. Le dict retourné contient au minimum :
`source`, `title`, `url` (et si disponible `doi`, `publication_date`, `snippet`).
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
    """Premier élément d'une liste (les API renvoient souvent des listes à un élément)."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else default
    return value if value is not None else default


def multilingual(value, default="") -> str:
    """Titre/description multilingue : préfère en/fr, sinon première valeur disponible."""
    if isinstance(value, dict):
        for lang in ("en", "fr", "eng"):
            if value.get(lang):
                return str(value[lang])
        for candidate in value.values():
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return default
    return str(value) if value else default
