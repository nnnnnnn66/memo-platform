"""Export bibliographique (BibTeX, RIS, CSV) — livrable n°8 du document d'opérationnalisation.

Aucun réseau, aucun modèle : l'export ne fait que RECOPIER les métadonnées réellement collectées.
Ces tests verrouillent deux propriétés : la conformité de chaque format, et l'honnêteté (un champ
absent reste absent — jamais inventé, jamais déguisé).
"""

from literature_review_agent.bibliography import export
from literature_review_agent.schemas.document import DocumentRecord


def _doc(**kwargs):
    base = dict(
        doc_id="D1",
        title="Le télétravail et la productivité des salariés",
        authors=["Koffi A.", "Diomandé B."],
        year=2023,
        venue="Revue de gestion",
        doi="10.1234/abcd",
        url="https://doi.org/10.1234/abcd",
        volume="12",
        issue="3",
        pages="45-67",
        language="fr",
    )
    base.update(kwargs)
    return DocumentRecord(**base)


def test_bibtex_entete_et_champs():
    sortie = export.to_bibtex([_doc()])
    assert sortie.startswith("@article{")
    assert "title = {Le télétravail et la productivité des salariés}" in sortie
    # BibTeX exige les auteurs joints par « and »
    assert "author = {Koffi A. and Diomandé B.}" in sortie
    assert "year = {2023}" in sortie
    assert "journal = {Revue de gestion}" in sortie
    assert "doi = {10.1234/abcd}" in sortie
    assert sortie.rstrip().endswith("}")


def test_bibtex_type_inconnu_reste_misc():
    """Un type indéterminé (`other`) ne doit PAS être déguisé en article évalué par les pairs."""
    sortie = export.to_bibtex([_doc(document_type="other")])
    assert sortie.startswith("@misc{")


def test_bibtex_cles_uniques():
    """Deux documents du même auteur et de la même année doivent avoir des clés distinctes."""
    a = _doc(doc_id="D1", title="Télétravail et productivité")
    b = _doc(doc_id="D2", title="Télétravail et coordination")
    sortie = export.to_bibtex([a, b])
    cles = [ligne.split("{")[1].rstrip(",") for ligne in sortie.splitlines() if ligne.startswith("@")]
    assert len(cles) == 2
    assert cles[0] != cles[1]


def test_champs_absents_non_inventes():
    """Un document sans DOI ni année ne doit contenir NI doi NI year."""
    sortie = export.to_bibtex([_doc(doi="", url="", year=None, volume="", issue="", pages="",
                                    language="")])
    assert "doi" not in sortie
    assert "year" not in sortie
    assert "volume" not in sortie


def test_ris_conforme():
    sortie = export.to_ris([_doc()])
    assert sortie.startswith("TY  - JOUR")
    assert "AU  - Koffi A." in sortie
    assert "AU  - Diomandé B." in sortie
    assert "PY  - 2023" in sortie
    assert "DO  - 10.1234/abcd" in sortie
    assert "ER  - " in sortie


def test_ris_type_inconnu_reste_generique():
    assert export.to_ris([_doc(document_type="other")]).startswith("TY  - GEN")


def test_csv_entete_et_ligne():
    sortie = export.to_csv([_doc()])
    lignes = sortie.strip().splitlines()
    assert lignes[0].startswith("doc_id;title;authors")
    assert "Le télétravail et la productivité des salariés" in lignes[1]
    assert "Koffi A. ; Diomandé B." in lignes[1]
    assert "10.1234/abcd" in lignes[1]


def test_export_choisit_le_format():
    for fmt, extension in (("bibtex", ".bib"), ("ris", ".ris"), ("csv", ".csv")):
        nom, mime, contenu = export.export([_doc()], fmt)
        assert nom.endswith(extension) and mime and contenu
    # Format inconnu : repli BibTeX, jamais d'erreur pour l'utilisateur
    nom, _, _ = export.export([_doc()], "odt")
    assert nom.endswith(".bib")


def test_corpus_vide_ne_produit_pas_d_erreur():
    assert export.export([], "bibtex")[2] == ""
    assert export.to_ris([]) == ""
    assert export.to_csv([]).startswith("doc_id")


def test_dictionnaire_accepte_autant_que_modele():
    """L'export doit fonctionner sur un enregistrement brut (dict) comme sur le modèle."""
    sortie = export.to_bibtex([{"doc_id": "D9", "title": "Titre dict", "authors": ["Nom P."],
                                "year": 2020, "document_type": "book"}])
    assert "@book{" in sortie and "Titre dict" in sortie
