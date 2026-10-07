"""Rendu des références (APA 7 / ISO 690 / Vancouver) — DÉTERMINISTE.

Le modèle ne rédige jamais une référence : elle est construite ici à partir des seules métadonnées
vérifiées du corpus amont. Objectif : aucune référence inventée ne peut apparaître.
"""

import re

_PARTICLES = {"de", "van", "von", "der", "den", "la", "le", "du", "del", "di", "da", "bin", "al"}


def _initials(tokens: list[str]) -> str:
    out = []
    for token in tokens:
        cleaned = re.sub(r"[^A-Za-zÀ-ÿ]", "", token)
        if cleaned:
            out.append(f"{cleaned[0].upper()}.")
    return " ".join(out)


def format_author(name: str) -> str:
    """« Prénom Nom » → « Nom, P. » (best-effort déterministe ; jamais d'invention)."""
    name = (name or "").strip()
    if not name:
        return ""
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        family, rest = parts[0], parts[1] if len(parts) > 1 else ""
        initials = _initials(rest.split())
        return f"{family}, {initials}".strip().rstrip(",")
    tokens = name.split()
    if len(tokens) == 1:
        return tokens[0]
    # « van der Berg Jan » ou « Jan van der Berg » : last token = nom de famille, le reste initiales
    family_parts = [tokens[-1]]
    index = len(tokens) - 2
    while index >= 0 and tokens[index].lower() in _PARTICLES:
        family_parts.insert(0, tokens[index])
        index -= 1
    family = " ".join(family_parts)
    initials = _initials(tokens[:index + 1])
    return f"{family}, {initials}".strip().rstrip(",")


def authors_apa(authors: list[str]) -> str:
    formatted = [format_author(a) for a in authors if a]
    formatted = [f for f in formatted if f]
    if not formatted:
        return ""
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def authors_plain(authors: list[str]) -> str:
    formatted = [format_author(a) for a in authors if a]
    formatted = [f for f in formatted if f]
    if not formatted:
        return ""
    return "; ".join(formatted)


def render(document, style: str = "apa7") -> str:
    """Référence déterministe d'un document du corpus amont."""
    title = (document.title or "").strip()
    venue = (document.venue or "").strip()
    year = document.year or "s.d."
    doi = (document.doi or "").strip()
    url = (document.url or "").strip()
    link = f"https://doi.org/{doi}" if doi and not doi.startswith("http") else (doi or url)

    if style == "iso690":
        head = authors_plain(document.authors) or "(sans auteur)"
        parts = [f"{head}. {title}."]
        if venue:
            parts.append(f"{venue},")
        parts.append(f"{year}.")
        if link:
            parts.append(link)
        return " ".join(parts).strip()

    if style == "vancouver":
        head = authors_plain(document.authors) or "(sans auteur)"
        parts = [f"{head}. {title}."]
        if venue:
            parts.append(f"{venue}.")
        parts.append(f"{year}.")
        if link:
            parts.append(link)
        return " ".join(parts).strip()

    # APA 7 (défaut)
    head = authors_apa(document.authors) or "(sans auteur)"
    entry = f"{head} ({year}). {title}."
    if venue:
        entry += f" {venue}."
    if link:
        entry += f" {link}"
    return entry.strip()
