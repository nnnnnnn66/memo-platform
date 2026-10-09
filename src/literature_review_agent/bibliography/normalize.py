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


# Traits d'union « typographiques » rencontrés dans les métadonnées (U+2010 trait d'union, U+2011
# insécable, U+2012, U+2013 tiret demi-cadratin). Un prénom composé réel « Margaret‐Anne » (avec
# U+2010) n'était pas reconnu comme composé → rendu « M. » au lieu de « M.-A. » (constaté en
# exécution réelle). On ne touche PAS aux titres : un tiret demi-cadratin y sépare des segments.
_NAME_DASHES = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2212": "-"})


def name_dashes(value: str) -> str:
    """Normalise les traits d'union typographiques d'un NOM (jamais d'un titre)."""
    return (value or "").translate(_NAME_DASHES)


_PARTICLES = {"de", "du", "des", "van", "von", "der", "den", "la", "le", "el", "al", "da", "di",
              "bin", "ben", "st", "st.", "mac", "mc"}


def _has_vowel(token: str) -> bool:
    return any(letter in "aeiouy" for letter in token.lower())


def _is_initial(token: str) -> bool:
    """Vrai si le jeton est un bloc d'initiales de prénom.

    Couvre « T », « T. », les blocs collés en capitales (« Yurtseven HR », « Michels LM ») et les
    blocs collés **en casse mixte sans voyelle** : le fournisseur abaisse parfois la seconde
    initiale (« Conradie Wj » = « Conradie, W. J. » plus loin dans les métadonnées). Un nom court
    contenant une voyelle (« Li », « Wu ») reste un nom — jamais des initiales.
    """
    core = token.strip().strip(".")
    if not core or not core.isalpha():
        return False
    if len(core) == 1:
        return True
    return 2 <= len(core) <= 3 and (core.isupper() or not _has_vowel(core))


def _is_caps_token(token: str) -> bool:
    """Jeton entièrement en capitales (« ABBE », « MANHOULI ») : nom de famille probable.

    Convention francophone très répandue dans les sources africaines : les NOMS sont écrits en
    capitales et placés AVANT les prénoms (« ABBE Hermann ») ou après (« Boris Noé MANHOULI DANMOU »).
    """
    core = token.strip().strip(".,")
    return len(core) >= 2 and core.isalpha() and core.isupper()


def _is_caps_surname_token(token: str) -> bool:
    """Capitales longues (≥ 4 lettres) : jamais des initiales, donc un NOM (« MANHOULI »)."""
    core = token.strip().strip(".,")
    return len(core) >= 4 and core.isalpha() and core.isupper()


def _recase_surname(value: str) -> str:
    """« MANHOULI DANMOU » → « Manhouli Danmou » (l'APA n'écrit pas les noms en capitales)."""
    out = []
    for token in value.split():
        core = token.strip()
        if len(core) >= 2 and core.isupper():
            core = "-".join(part[:1].upper() + part[1:].lower() if part else part
                            for part in core.split("-"))
        out.append(core)
    return " ".join(out)


_INSTITUTION_MARKERS = (
    "université", "universite", "university", "faculté", "faculte", "faculty", "institut",
    "institute", "école ", "ecole ", "school", "collège", "college", "département", "departement",
    "department", "laboratoire", "laboratory", "hôpital", "hopital", "hospital", "ministère",
    "ministere", "ministry", "république", "republique", "republic", "société", "societe",
    "company", "association", "agence nationale", "agency", "organisation", "organization",
    "fondation", "foundation", "banque", "bank", "umr ", "cnrs", "inserm", "service national",
    "ltd", "gmbh", "corp.",
)


def is_institution(value: str) -> bool:
    """Vrai si la chaîne est une AFFILIATION prise à tort pour un auteur (artefact de fournisseur).

    OpenAlex place parfois les affiliations DANS la liste des auteurs : « Université Gamal Abdel
    Nasser de Conakry, Faculté des sciences techniques et santé. ». Une organisation peut être
    auteur (APA), mais une ADRESSE ne l'est pas — ces chaînes polluaient la bibliographie et le
    vérificateur les comptait comme noms mal formés (contrôle L11).
    """
    text = clean_text(value)
    if not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in _INSTITUTION_MARKERS):
        return True
    # Forme d'une adresse postale : plusieurs segments séparés par des virgules, ponctuation finale.
    return text.endswith(".") and "," in text and len(text.split()) >= 5


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


def split_name(full_name: str, surname_first: bool = False) -> tuple[str, str]:
    """Sépare un nom d'auteur en (Nom, Prénom).

    Gère les formes rencontrées dans les données réelles :
      - « Nom, Prénom » déjà normalisée ;
      - « Nom Initiales » (« Jiang T », « Michels L. M. ») ;
      - « Prénom Nom » (usage courant des fournisseurs) et les particules
        (« van der Berg », « de La Fontaine », « El Amrani ») ;
      - **convention « NOM Prénoms »** des sources africaines/francophones, où le nom de famille
        est en CAPITALES, en tête (« ABBE Hermann ») ou après les prénoms
        (« Boris Noé MANHOULI DANMOU »). `surname_first` signale cette convention quand un autre
        auteur du même document la montre (même source = même convention).
    """
    name = name_dashes(clean_text(full_name))
    if not name:
        return "", ""
    if "," in name:
        last, _, first = name.partition(",")
        return clean_text(_recase_surname(last)), clean_text(first)
    parts = [p for p in name.split() if p]
    if len(parts) == 1:
        return _recase_surname(parts[0]), ""

    # 1. Nom de famille EN CAPITALES en tête de chaîne (« ABBE Hermann », « MANHOULI Boris »).
    head = 0
    while head < len(parts) and _is_caps_token(parts[head]) and not _is_initial(parts[head]):
        head += 1
    if head and head < len(parts) and (surname_first or head == 1):
        return clean_text(_recase_surname(" ".join(parts[:head]))), clean_text(" ".join(parts[head:]))
    if surname_first and not head:
        # Convention du document (NOM d'abord) : le premier jeton est le nom de famille.
        return clean_text(_recase_surname(parts[0])), clean_text(" ".join(parts[1:]))

    # 2. Capitales longues ailleurs (« Boris Noé MANHOULI DANMOU ») : elles forment le nom.
    caps = [p for p in parts if _is_caps_surname_token(p)]
    if caps:
        given = [p for p in parts if p not in caps]
        return clean_text(_recase_surname(" ".join(caps))), clean_text(" ".join(given))

    # 3. Forme « Nom Initiales » : un bloc d'initiales en fin de chaîne est le prénom.
    cut = len(parts)
    while cut > 1 and _is_initial(parts[cut - 1]):
        cut -= 1
    if cut < len(parts):
        return clean_text(" ".join(parts[:cut])), clean_text(" ".join(parts[cut:]))

    # 4. On remonte depuis la fin : la dernière particule est le nom, auquel s'ajoutent les
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
    return clean_text(_recase_surname(last)), clean_text(first)


def initials(first_names: str, style: str = "apa") -> str:
    """Initiales d'un prénom : « Jean Pierre » → « J. P. » (APA) ou « JP » (Vancouver).

    Un bloc collé (« HR », « LM ») est éclaté en initiales distinctes : « H. R. ».
    """
    first_names = name_dashes(first_names or "")
    if not first_names.strip():
        return ""
    # Un prénom composé garde son tiret (« Kai-Kristian » → « K.-K. ») ; les prénoms successifs et
    # les initiales d'un même bloc sont séparés par une espace (« Jean Pierre » → « J. P. »,
    # « Yurtseven HR » → « H. R. »).

    def letters_of(core: str) -> list[str]:
        if 2 <= len(core) <= 3 and (core.isupper() or not _has_vowel(core)):
            # Bloc d'initiales collées (« HR », « LM », « Wj ») : éclaté lettre par lettre
            # (en capitales : le fournisseur abaisse parfois la seconde, « Wj »).
            return list(core.upper())
        if core and core[0].isalpha():
            # Un jeton plus long (« MANHOULI », « Boris ») est un NOM, jamais des initiales :
            # l'éclater produisait « B. N. M. A. N. H. O. U. L. I. » (constaté en exécution réelle).
            return [core[0].upper()]
        return []

    chunks: list[str] = []
    flat: list[str] = []
    for token in re.split(r"\s+", first_names.strip()):
        if not token:
            continue
        parts = [p.strip().strip(".") for p in token.split("-")]
        parts = [p for p in parts if p]
        if not parts:
            continue
        per_part = [letters_of(p) for p in parts]
        flat.extend(letter for group in per_part for letter in group)
        if len(parts) > 1:
            chunks.append("-".join(" ".join(f"{letter}." for letter in group) for group in per_part))
        else:
            chunks.append(" ".join(f"{letter}." for letter in per_part[0]))
    if style == "vancouver":
        return "".join(flat)
    return " ".join(chunk for chunk in chunks if chunk)


def document_surname_first(authors: list[str]) -> bool:
    """Le document suit-il la convention « NOM Prénoms » ?

    Indice pris DANS le document lui-même : un auteur dont le premier jeton est un NOM en
    capitales — capitales LONGUES, ≥ 4 lettres (« ABBE Hermann »). Un bloc de 1 à 3 capitales est un
    groupe d'initiales et NE compte pas : « MM Barry » ou « FBA Diallo » sont des formes
    « initiales + nom » très courantes, pas la convention « NOM d'abord ».
    """
    for author in authors or []:
        parts = [p for p in clean_text(author).split() if p]
        if len(parts) >= 2 and _is_caps_surname_token(parts[0]) and not _is_caps_token(parts[1]):
            return True
    return False


def author_apa(full_name: str, surname_first: bool = False) -> str:
    last, first = split_name(full_name, surname_first)
    if not last:
        return ""
    return f"{last}, {initials(first)}".strip().rstrip(",") if first else last


def author_iso(full_name: str, surname_first: bool = False) -> str:
    last, first = split_name(full_name, surname_first)
    if not last:
        return ""
    return f"{last.upper()}, {first}".strip().rstrip(",") if first else last.upper()


def author_vancouver(full_name: str, surname_first: bool = False) -> str:
    last, first = split_name(full_name, surname_first)
    if not last:
        return ""
    return f"{last} {initials(first, 'vancouver')}".strip()


def join_authors(authors: list[str], style: str, surname_first: bool | None = None) -> str:
    """Assemble la liste d'auteurs selon les conventions du style demandé.

    Les AFFILIATIONS prises pour des auteurs (artefact de fournisseur) sont écartées : une adresse
    n'est pas un auteur.
    """
    people = [a for a in (authors or []) if a and not is_institution(a)]
    if surname_first is None:
        surname_first = document_surname_first(people)
    rendered = []
    for author in people:
        if style == "iso690":
            rendered.append(author_iso(author, surname_first))
        elif style == "vancouver":
            rendered.append(author_vancouver(author, surname_first))
        else:
            rendered.append(author_apa(author, surname_first))
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
