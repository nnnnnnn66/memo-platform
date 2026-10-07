"""Normalisation bibliographique déterministe (aucun LLM).

Transforme les métadonnées vérifiées d'un document en composants exploitables par les styles :
liste d'auteurs au format « Nom, Prénom », année, titre, support, volume, numéro, pages, DOI, URL.

Rien n'est inventé : un champ absent reste absent, et le rendu l'omet proprement.
"""

import re
import unicodedata


def clean_text(value: str) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,;")


_PARTICLES = {"de", "du", "des", "van", "von", "der", "den", "la", "le", "el", "al", "da", "di",
              "bin", "ben", "st", "st.", "mac", "mc"}


def split_name(full_name: str) -> tuple[str, str]:
    """Sépare « Prénom Nom » (usage des fournisseurs) en (Nom, Prénom).

    Gère les formes « Nom, Prénom » déjà normalisées et les particules courantes
    (« van der Berg », « de La Fontaine », « El Amrani »).
    """
    name = clean_text(full_name)
    if not name:
        return "", ""
    if "," in name:
        last, _, first = name.partition(",")
        return clean_text(last), clean_text(first)
    parts = [p for p in name.split() if p]
    if len(parts) == 1:
        return parts[0], ""

    # On remonte depuis la fin : la dernière particule est le nom, auquel s'ajoutent les
    # particules (ou mots en minuscules) qui le précèdent.
    index = len(parts) - 1
    while index > 0:
        previous = parts[index - 1]
        if previous.lower() in _PARTICLES or (previous and previous[0].islower()):
            index -= 1
            continue
        break
    last = " ".join(parts[index:])
    first = " ".join(parts[:index])
    return clean_text(last), clean_text(first)


def initials(first_names: str, style: str = "apa") -> str:
    """Initiales d'un prénom : « Jean Pierre » → « J. P. » (APA) ou « JP » (Vancouver)."""
    if not first_names:
        return ""
    parts = [p for p in re.split(r"[\s\-]+", first_names) if p]
    letters = [p[0].upper() for p in parts if p and p[0].isalpha()]
    if style == "vancouver":
        return "".join(letters)
    return " ".join(f"{letter}." for letter in letters)


def author_apa(full_name: str) -> str:
    last, first = split_name(full_name)
    if not last:
        return ""
    return f"{last}, {initials(first)}".strip().rstrip(",") if first else last


def author_iso(full_name: str) -> str:
    last, first = split_name(full_name)
    if not last:
        return ""
    return f"{last.upper()}, {first}".strip().rstrip(",") if first else last.upper()


def author_vancouver(full_name: str) -> str:
    last, first = split_name(full_name)
    if not last:
        return ""
    return f"{last} {initials(first, 'vancouver')}".strip()


def join_authors(authors: list[str], style: str) -> str:
    """Assemble la liste d'auteurs selon les conventions du style demandé."""
    rendered = []
    for author in authors or []:
        if style == "iso690":
            rendered.append(author_iso(author))
        elif style == "vancouver":
            rendered.append(author_vancouver(author))
        else:
            rendered.append(author_apa(author))
    rendered = [r for r in rendered if r]
    if not rendered:
        return ""
    if style == "vancouver":
        return ", ".join(rendered)
    if len(rendered) == 1:
        return rendered[0]
    if style == "iso690":
        # ISO 690 : « NOM, Prénom ; NOM, Prénom » (au-delà de 3, on abrège)
        if len(rendered) > 3:
            return " ; ".join(rendered[:3]) + " et al."
        return " ; ".join(rendered)
    # APA 7 : « A ; B et C » avec esperluette avant le dernier
    if len(rendered) > 20:
        return ", ".join(rendered[:19]) + ", … " + rendered[-1]
    return ", ".join(rendered[:-1]) + " et " + rendered[-1] if len(rendered) > 1 else rendered[0]
