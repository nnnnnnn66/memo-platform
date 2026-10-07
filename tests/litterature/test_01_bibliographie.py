"""Rendu bibliographique déterministe : APA 7, ISO 690, Vancouver."""

from literature_review_agent.bibliography import styles
from literature_review_agent.schemas.document import DocumentRecord


def _doc(**overrides) -> DocumentRecord:
    payload = {
        "doc_id": "D1",
        "authors": ["Marie Dupont", "Jean de La Fontaine", "Awa Traoré"],
        "title": "Télétravail et productivité",
        "year": 2022,
        "venue": "Revue du travail",
        "doi": "10.1234/abcd",
        "url": "https://doi.org/10.1234/abcd",
        "volume": "8",
        "issue": "2",
        "pages": "10-30",
        "document_type": "article",
    }
    payload.update(overrides)
    return DocumentRecord(**payload)


def test_apa7_article_complet():
    ref = styles.render(_doc(), "apa7")
    assert "Dupont, M." in ref
    assert "La Fontaine, J. d." in ref or "La Fontaine" in ref
    assert "(2022)." in ref
    assert "Revue du travail" in ref
    assert "8(2), 10-30" in ref
    assert "https://doi.org/10.1234/abcd" in ref


def test_iso690_article():
    ref = styles.render(_doc(), "iso690")
    assert ref.startswith("DUPONT") or "DUPONT" in ref
    assert "2022" in ref
    assert "Disponible sur : https://doi.org/10.1234/abcd" in ref


def test_vancouver_article():
    ref = styles.render(_doc(), "vancouver")
    assert "Dupont M" in ref
    assert "2022;8(2), 10-30" in ref or "2022;8(2)" in ref


def test_these_et_rapport_sont_etiquetes():
    these = styles.render(_doc(document_type="thesis", venue="Université de Rennes"), "apa7")
    assert "Thèse" in these
    rapport = styles.render(_doc(document_type="report", venue="Banque mondiale"), "apa7")
    assert "Rapport" in rapport


def test_champs_absents_omis_sans_invention():
    ref = styles.render(_doc(year=None, venue="", volume="", issue="", pages="", doi="",
                             url=""), "apa7")
    assert "Dupont" in ref
    assert "(s. d.)." in ref
    assert "None" not in ref
    assert "  " not in ref


def test_aucun_auteur_connu():
    ref = styles.render(_doc(authors=[]), "apa7")
    assert "(2022)." in ref
    assert ref.strip().startswith("(2022).")


def test_particules_de_nom_preservees():
    ref = styles.render(_doc(authors=["Jan van der Berg"]), "apa7")
    assert "van der Berg" in ref


def test_style_inconnu_retombe_sur_apa():
    assert styles.render(_doc(), "inconnu") == styles.render(_doc(), "apa7")


def test_apa7_esperluette_avant_le_dernier_auteur():
    ref = styles.render(_doc(authors=["Marie Dupont", "Awa Traoré"]), "apa7")
    assert "Dupont, M. & Traoré, A." in ref


def test_nom_suivi_d_initiales_remis_dans_le_bon_ordre():
    """Fournisseurs : « Jiang T » (nom puis initiale) ne doit pas devenir « T, J. »."""
    from literature_review_agent.bibliography.normalize import author_apa, split_name

    assert split_name("Jiang T") == ("Jiang", "T")
    assert author_apa("Jiang T") == "Jiang, T."
    assert author_apa("Michels L. M.") == "Michels, L. M."
    assert author_apa("Abdulrahman M. Qahtani") == "Qahtani, A. M."
    assert author_apa("Graziotin, D.") == "Graziotin, D."
    # Bloc d'initiales collées sans points, renvoyé par certains fournisseurs.
    assert author_apa("Yurtseven HR") == "Yurtseven, H. R."
    assert author_apa("Li") == "Li"          # un nom court en casse mixte reste un nom
    ref = styles.render(_doc(authors=["Jiang T"]), "apa7")
    assert ref.startswith("Jiang, T.")


def test_apa7_virgule_serielle_avant_l_esperluette_a_partir_de_trois_auteurs():
    deux = styles.render(_doc(authors=["Marie Dupont", "Awa Traoré"]), "apa7")
    assert "Dupont, M. & Traoré, A." in deux
    trois = styles.render(_doc(authors=["Marie Dupont", "Awa Traoré", "Kim Lee"]), "apa7")
    assert "Dupont, M., Traoré, A., & Lee, K." in trois


def test_guillemet_double_non_apparie_retire_du_titre():
    ref = styles.render(_doc(title='Enhancing Teams" Client Awareness'), "apa7")
    assert '"' not in ref
    assert "Teams Client Awareness" in ref


def test_guillemets_apparies_conserves():
    ref = styles.render(_doc(title='The "New" Normal of Work'), "apa7")
    assert '"New"' in ref
