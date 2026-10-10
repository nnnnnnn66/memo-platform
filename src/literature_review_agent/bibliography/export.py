"""Export bibliographique — BibTeX, RIS et CSV.

Livrable n°8 du document d'opérationnalisation de l'Agent 3 : « Bibliographie exportable en
BibTeX, RIS ou CSV si possible ».

Règle absolue : ces exports sont **déterministes et purement recopiés** des métadonnées réellement
collectées (`corpus.documents`). Un champ absent reste **vide** — jamais comblé par une supposition,
jamais inventé. Aucun LLM n'intervient ici.
"""

import csv
import io
import re
import unicodedata

# Type interne → type BibTeX. `misc` est le repli honnête : on ne déguise pas un document inconnu
# en article évalué par les pairs.
_BIBTEX_TYPES = {
    "article": "article", "book": "book", "thesis": "phdthesis",
    "report": "techreport", "preprint": "misc", "dataset": "misc", "other": "misc",
}

# Type interne → type RIS (codes officiels du format).
_RIS_TYPES = {
    "article": "JOUR", "book": "BOOK", "thesis": "THES",
    "report": "RPRT", "preprint": "UNPB", "dataset": "DATA", "other": "GEN",
}

_ACCENTS = re.compile(r"[^a-zA-Z0-9]+")


def _get(record, name, default=None):
    """Lit un champ sur un objet (modèle) ou un dictionnaire, sans jamais lever."""
    if isinstance(record, dict):
        value = record.get(name, default)
    else:
        value = getattr(record, name, default)
    return default if value is None else value


def _text(record, name) -> str:
    return str(_get(record, name, "") or "").strip()


def _authors(record) -> list[str]:
    value = _get(record, "authors", []) or []
    if isinstance(value, str):
        value = [value]
    return [str(a).strip() for a in value if str(a).strip()]


def _year(record):
    value = _get(record, "year", None)
    return value if isinstance(value, int) else None


def _type(record) -> str:
    value = _get(record, "document_type", "other")
    value = getattr(value, "value", value)
    return str(value or "other").strip().lower()


def _ascii(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    return decomposed.encode("ascii", "ignore").decode("ascii")


def _bibtex_key(record, used: set[str]) -> str:
    """Clé BibTeX unique : nom de famille du premier auteur + année + mot du titre."""
    authors = _authors(record)
    famille = ""
    if authors:
        premier = authors[0]
        famille = premier.split(",")[0] if "," in premier else premier.split(" ")[-1]
    base = _ACCENTS.sub("", _ascii(famille).lower()) or "sansauteur"
    annee = _year(record)
    titre = _ACCENTS.sub("", _ascii(_text(record, "title")).lower())
    mot = next((m for m in titre.split() if len(m) > 3), "")
    cle = f"{base}{annee or 'sansdate'}{mot}"
    candidate, index = cle, 0
    while candidate in used:
        index += 1
        candidate = f"{cle}{chr(ord('a') + index - 1)}"
    used.add(candidate)
    return candidate


def _bibtex_value(value: str) -> str:
    return value.replace("\\", " ").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def to_bibtex(records) -> str:
    """BibTeX : une entrée par document, champs présents uniquement."""
    used: set[str] = set()
    lignes: list[str] = []
    for record in records or []:
        champs = [("title", _text(record, "title"))]
        auteurs = _authors(record)
        if auteurs:
            champs.append(("author", " and ".join(auteurs)))
        if _year(record):
            champs.append(("year", str(_year(record))))
        for nom, cle in (("venue", "journal"), ("volume", "volume"), ("issue", "number"),
                         ("pages", "pages"), ("doi", "doi"), ("url", "url"),
                         ("language", "language"), ("abstract", "abstract")):
            valeur = _text(record, nom)
            if valeur:
                champs.append((cle, valeur))
        corps = ",\n".join(f"  {cle} = {{{_bibtex_value(valeur)}}}"
                           for cle, valeur in champs if valeur)
        lignes.append(f"@{_BIBTEX_TYPES.get(_type(record), 'misc')}{{{_bibtex_key(record, used)},\n{corps}\n}}")
    return "\n\n".join(lignes) + ("\n" if lignes else "")


def to_ris(records) -> str:
    """RIS : un enregistrement par document, terminé par `ER  -`."""
    lignes: list[str] = []
    for record in records or []:
        lignes.append(f"TY  - {_RIS_TYPES.get(_type(record), 'GEN')}")
        for auteur in _authors(record):
            lignes.append(f"AU  - {auteur}")
        for nom, tag in (("title", "TI"), ("venue", "JO"), ("volume", "VL"), ("issue", "IS"),
                         ("pages", "SP"), ("doi", "DO"), ("url", "UR"), ("language", "LA")):
            valeur = _text(record, nom)
            if valeur:
                lignes.append(f"{tag}  - {valeur}")
        if _year(record):
            lignes.append(f"PY  - {_year(record)}")
        resume = _text(record, "abstract")
        if resume:
            lignes.append(f"AB  - {resume}")
        lignes.append("ER  - ")
        lignes.append("")
    return "\n".join(lignes)


def to_csv(records) -> str:
    """CSV : une ligne par document, colonnes fixes (lisible dans un tableur)."""
    colonnes = ["doc_id", "title", "authors", "year", "venue", "document_type", "doi", "url",
                "volume", "issue", "pages", "language", "geographic_scope", "extraction_scope",
                "source_type", "provider"]
    tampon = io.StringIO()
    writer = csv.writer(tampon, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(colonnes)
    for record in records or []:
        portee = _get(record, "geographic_scope", "")
        lecture = _get(record, "extraction_scope", "")
        source = _get(record, "source_type", "")
        writer.writerow([
            _text(record, "doc_id"), _text(record, "title"), " ; ".join(_authors(record)),
            _year(record) or "", _text(record, "venue"), _type(record), _text(record, "doi"),
            _text(record, "url"), _text(record, "volume"), _text(record, "issue"),
            _text(record, "pages"), _text(record, "language"),
            getattr(portee, "value", portee), getattr(lecture, "value", lecture),
            getattr(source, "value", source), _text(record, "provider"),
        ])
    return tampon.getvalue()


FORMATS = {"bibtex": ("bibliographie.bib", "application/x-bibtex", to_bibtex),
           "ris": ("bibliographie.ris", "application/x-research-info-systems", to_ris),
           "csv": ("bibliographie.csv", "text/csv", to_csv)}


def export(records, fmt: str) -> tuple[str, str, str]:
    """Renvoie (nom_de_fichier, type MIME, contenu) pour le format demandé."""
    nom, mime, fonction = FORMATS.get(str(fmt or "").lower(), FORMATS["bibtex"])
    return nom, mime, fonction(records)
