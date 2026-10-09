"""Rendu des références (APA 7 / ISO 690 / Vancouver) — DÉTERMINISTE.

Le modèle ne rédige jamais une référence : elle est construite ici à partir des seules métadonnées
vérifiées du corpus amont. Objectif : aucune référence inventée ne peut apparaître.
"""

import re

_PARTICLES = {"de", "van", "von", "der", "den", "la", "le", "du", "del", "di", "da", "bin", "al",
              "ó", "o", "mac", "mc"}

# Traits d'union typographiques (U+2010, U+2011, U+2012, U+2212) : les métadonnées les utilisent
# pour les prénoms composés (« Margaret‐Anne »). Sans normalisation, le prénom n'était pas reconnu
# comme composé → « M. » au lieu de « M.-A. » (constaté en exécution réelle).
_NAME_DASHES = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2212": "-"})


def _name_dashes(value: str) -> str:
    return (value or "").translate(_NAME_DASHES)


def _has_vowel(token: str) -> bool:
    return any(letter in "aeiouy" for letter in token.lower())


def _glued_initials(core: str) -> bool:
    """Bloc d'initiales collées : 2-3 lettres en capitales, ou sans voyelle (« Wj », abaissé par le
    fournisseur). Un nom court AVEC voyelle (« Li », « Wu ») n'est jamais des initiales."""
    return 2 <= len(core) <= 3 and core.isalpha() and (core.isupper() or not _has_vowel(core))


def _letters(core: str) -> list[str]:
    if _glued_initials(core):
        return [f"{letter.upper()}." for letter in core]
    return [f"{core[0].upper()}."] if core else []


def _initials(tokens: list[str]) -> str:
    """Initiales d'un prénom. Bloc collé (« JC », « Wj ») éclaté ; prénom composé garde son tiret
    (« Jean-Marc » → « J.-M. »)."""
    chunks: list[str] = []
    for token in tokens:
        cleaned = re.sub(r"[^A-Za-zÀ-ÿ\-]", "", _name_dashes(token)).strip(".")
        parts = [p for p in cleaned.split("-") if p]
        if not parts:
            continue
        if len(parts) > 1:
            chunks.append("-".join(" ".join(_letters(p)) for p in parts))
        else:
            chunks.append(" ".join(_letters(parts[0])))
    return " ".join(chunk for chunk in chunks if chunk)


def _is_initials(token: str) -> bool:
    """Vrai si le jeton est un bloc d'initiales de prénom (« T », « T. », « JC », « Wj »).

    Couvre la forme des fournisseurs « Nom Initiales » (« Jiang T », « Mutiganda JC »).
    Un nom court en casse mixte avec voyelle (« Li », « Wu ») n'est jamais pris pour des initiales.
    """
    core = _name_dashes(token).strip().strip(".")
    if not core or not core.isalpha():
        return False
    if len(core) == 1:
        return True
    return _glued_initials(core)


def format_author(name: str) -> str:
    """« Prénom Nom » / « Nom Initiales » → « Nom, I. » (best-effort déterministe, sans invention).

    Les fournisseurs renvoient tantôt « Prénom Nom », tantôt « Nom Initiales » (« Jiang T »,
    « Mutiganda JC »), tantôt avec un nom de famille EN CAPITALES (« Boris Noé MANHOULI DANMOU »)
    ou en tête (« ABBE Hermann »). Sans cette détection, le dernier mot était pris pour le nom et la
    bibliographie affichait « JC, M. » au lieu de « Mutiganda, J. C. ».
    """
    name = _name_dashes((name or "").strip())
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

    # Nom de famille EN CAPITALES en tête (« ABBE Hermann ») : il précède les prénoms.
    head = 0
    while head < len(tokens) and _is_caps_name(tokens[head]):
        head += 1
    if head and head < len(tokens):
        family = " ".join(tokens[:head])
        initials = _initials(tokens[head:])
        return f"{_recase(family)}, {initials}".strip().rstrip(",")

    # Nom de famille EN CAPITALES après les prénoms (« Boris Noé MANHOULI DANMOU »).
    caps = [t for t in tokens if _is_caps_name(t)]
    if caps:
        family = " ".join(caps)
        initials = _initials([t for t in tokens if t not in caps])
        return f"{_recase(family)}, {initials}".strip().rstrip(",")

    # Forme « Nom Initiales » : un bloc d'initiales EN FIN de chaîne est le prénom.
    cut = len(tokens)
    while cut > 1 and _is_initials(tokens[cut - 1]):
        cut -= 1
    if cut < len(tokens):
        family = " ".join(tokens[:cut])
        initials = _initials(tokens[cut:])
        return f"{family}, {initials}".strip().rstrip(",")

    # « van der Berg Jan » ou « Jan van der Berg » : last token = nom de famille, le reste initiales
    family_parts = [tokens[-1]]
    index = len(tokens) - 2
    while index >= 0 and tokens[index].lower() in _PARTICLES:
        family_parts.insert(0, tokens[index])
        index -= 1
    family = " ".join(family_parts)
    initials = _initials(tokens[:index + 1])
    return f"{family}, {initials}".strip().rstrip(",")


def _is_caps_name(token: str) -> bool:
    """Jeton en capitales (≥ 4 lettres : au-delà d'un bloc d'initiales) = nom de famille probable."""
    core = token.strip().strip(".,")
    return len(core) >= 4 and core.isalpha() and core.isupper()


def _recase(value: str) -> str:
    """« MANHOULI DANMOU » → « Manhouli Danmou » (l'APA n'écrit pas les noms en capitales)."""
    out = []
    for token in value.split():
        core = token.strip()
        if len(core) >= 2 and core.isupper():
            core = "-".join(p[:1].upper() + p[1:].lower() if p else p for p in core.split("-"))
        out.append(core)
    return " ".join(out)


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
