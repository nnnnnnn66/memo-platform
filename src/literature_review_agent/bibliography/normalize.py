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


def _is_initial(token: str) -> bool:
    """Vrai si le jeton est un bloc d'initiales de prénom.

    Couvre « T », « T. » et les blocs collés sans points de certains fournisseurs
    (« Yurtseven HR », « Michels LM »). Un nom en casse mixte (« Li », « Wu ») n'est
    jamais pris pour des initiales.
    """
    core = token.strip().strip(".")
    if not core or not core.isalpha():
        return False
    if len(core) == 1:
        return True
    return 2 <= len(core) <= 3 and core.isupper()


def clean_title(value: str) -> str:
    """Titre débarrassé du bruit de métadonnée : guillemet double non apparié (« Teams" Client »).

    Un guillemet double en nombre impair ne peut pas encadrer une citation : c'est un artefact
    du fournisseur. On le retire plutôt que de l'afficher dans la bibliographie.
    """
    text = clean_text(value)
    for quote in ('"', "\u201c", "\u201d"):
        if text.count(quote) % 2 == 1:
            text = text.replace(quote, "")
    return re.sub(r"\s+", " ", text).strip(" ,;")


def split_name(full_name: str) -> tuple[str, str]:
    """Sépare « Prénom Nom » (usage des fournisseurs) en (Nom, Prénom).

    Gère les formes « Nom, Prénom » déjà normalisées, la forme « Nom Initiales »
    (« Jiang T », « Michels L. M. ») et les particules courantes
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

    # Forme « Nom Initiales » : un bloc d'initiales en fin de chaîne est le prénom.
    cut = len(parts)
    while cut > 1 and _is_initial(parts[cut - 1]):
        cut -= 1
    if cut < len(parts):
        return clean_text(" ".join(parts[:cut])), clean_text(" ".join(parts[cut:]))

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
    """Initiales d'un prénom : « Jean Pierre » → « J. P. » (APA) ou « JP » (Vancouver).

    Un bloc collé (« HR », « LM ») est éclaté en initiales distinctes : « H. R. ».
    """
    if not first_names:
        return ""
    parts = [p for p in re.split(r"[\s\-]+", first_names) if p]
    letters: list[str] = []
    for part in parts:
        core = part.strip().strip(".")
        if len(core) > 1 and core.isalpha() and core.isupper():
            letters.extend(core)
        elif core and core[0].isalpha():
            letters.append(core[0].upper())
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
    # APA 7 : « A & B » (deux auteurs), « A, B, & C » (trois et plus, virgule sérielle).
    if len(rendered) > 20:
        return ", ".join(rendered[:19]) + ", … " + rendered[-1]
    if len(rendered) == 2:
        return f"{rendered[0]} & {rendered[1]}"
    return ", ".join(rendered[:-1]) + ", & " + rendered[-1]
