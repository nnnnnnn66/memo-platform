"""Rendu déterministe des références bibliographiques : APA 7, ISO 690, Vancouver.

Le modèle ne rédige JAMAIS une référence : tout est construit à partir des métadonnées vérifiées
du document (nom des auteurs, année, titre, support, DOI/URL). Un champ manquant est omis — jamais
inventé.
"""

from .normalize import clean_text, clean_title, join_authors

STYLES = ("apa7", "iso690", "vancouver")


def _venue(venue: str) -> str:
    return clean_text(venue)


def _volume_issue_pages(record) -> str:
    volume = clean_text(getattr(record, "volume", "") or "")
    issue = clean_text(getattr(record, "issue", "") or "")
    pages = clean_text(getattr(record, "pages", "") or "")
    parts = ""
    if volume:
        parts = volume
        if issue:
            parts += f"({issue})"
    if pages:
        parts = f"{parts}, {pages}" if parts else pages
    return parts


def _doi_url(record, include_doi: bool = True) -> str:
    doi = clean_text(getattr(record, "doi", "") or "")
    url = clean_text(getattr(record, "url", "") or "")
    if include_doi and doi:
        return f"https://doi.org/{doi}"
    return url


def apa7(record) -> str:
    authors = join_authors(getattr(record, "authors", []) or [], "apa7")
    year = getattr(record, "year", None)
    title = clean_title(getattr(record, "title", "") or "")
    venue = _venue(getattr(record, "venue", "") or "")
    vip = _volume_issue_pages(record)
    link = _doi_url(record)
    doc_type = getattr(record, "document_type", "article")
    if hasattr(doc_type, "value"):
        doc_type = doc_type.value

    segments = []
    segments.append(f"{authors}. " if authors else "")
    segments.append(f"({year}). " if year else "(s. d.). ")
    segments.append(f"{title}. " if title else "")
    if doc_type == "thesis":
        segments.append(f"Thèse. {venue}. " if venue else "Thèse. ")
    elif doc_type in ("report", "dataset"):
        label = "Rapport" if doc_type == "report" else "Jeu de données"
        segments.append(f"{label}. {venue}. " if venue else f"{label}. ")
    elif doc_type == "book":
        segments.append(f"{venue}. " if venue else "")
    else:
        if venue:
            segments.append(f"{venue}")
            segments.append(f", {vip}" if vip else "")
            segments.append(". ")
    if link:
        segments.append(link)
    return "".join(segments).strip().replace("..", ".")


def iso690(record) -> str:
    authors = join_authors(getattr(record, "authors", []) or [], "iso690")
    title = clean_title(getattr(record, "title", "") or "")
    venue = _venue(getattr(record, "venue", "") or "")
    year = getattr(record, "year", None)
    vip = _volume_issue_pages(record)
    url = _doi_url(record)
    doc_type = getattr(record, "document_type", "article")
    if hasattr(doc_type, "value"):
        doc_type = doc_type.value

    head = f"{authors}. " if authors else ""
    label = {"thesis": "Thèse", "book": "Ouvrage", "report": "Rapport",
             "dataset": "Jeu de données", "preprint": "Prépublication"}.get(doc_type, "Article")
    body = f"{title}. " if title else ""
    body += f"{label}. " if label != "Article" else ""
    if venue:
        body += f"{venue}. " if label == "Article" else f"{venue}. "
    detail = []
    if year:
        detail.append(str(year))
    if vip:
        detail.append(vip)
    if detail:
        body += ", ".join(detail) + ". "
    if url:
        body += f"Disponible sur : {url}"
    return (head + body).strip().replace("..", ".")


def vancouver(record) -> str:
    authors = join_authors(getattr(record, "authors", []) or [], "vancouver")
    title = clean_title(getattr(record, "title", "") or "")
    venue = _venue(getattr(record, "venue", "") or "")
    year = getattr(record, "year", None)
    vip = _volume_issue_pages(record)
    url = _doi_url(record)

    out = f"{authors}. " if authors else ""
    out += f"{title}. " if title else ""
    if venue:
        out += f"{venue}. "
    if year:
        out += f"{year}"
        if vip:
            out += f";{vip}"
        out += ". "
    if url:
        out += url
    return out.strip().replace("..", ".")


_RENDERERS = {"apa7": apa7, "iso690": iso690, "vancouver": vancouver}


def render(record, style: str = "apa7") -> str:
    """Rend la référence d'un document dans le style demandé (défaut : APA 7)."""
    renderer = _RENDERERS.get((style or "apa7").lower(), apa7)
    return renderer(record)
