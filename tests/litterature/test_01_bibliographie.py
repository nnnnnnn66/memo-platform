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


# --- données réelles : noms d'auteurs tels que les fournisseurs les renvoient -------------------
# Ces trois cas sont tirés d'une campagne réelle (sujet « télétravail / développeurs d'Abidjan ») où
# le vérificateur a refusé la bibliographie (contrôle L11). Chaque cas couvre un artefact distinct.

def test_affiliation_prise_pour_un_auteur_ecartee():
    """OpenAlex met parfois les AFFILIATIONS dans la liste des auteurs (D6, campagne réelle).

    Une organisation peut être auteur ; une ADRESSE ne l'est pas. Ces chaînes produisaient
    « Université Gamal Abdel Nasser de Conakry, F. D. S. T. E. S., … » dans la bibliographie.
    """
    from literature_review_agent.bibliography import normalize

    authors = [
        "Université Gamal Abdel Nasser de Conakry, Faculté des sciences techniques et santé.",
        "FBA Diallo",
        "Service National de Santé au Travail, Km9 - Matam Conakry, Rép. de Guinée.",
        "Alhousseine Yansané",
        "A Sow",
        "MM Barry",
    ]
    assert normalize.is_institution(authors[0])
    assert normalize.is_institution(authors[2])
    assert not normalize.is_institution("FBA Diallo")
    assert not normalize.is_institution("Alhousseine Yansané")

    ref = styles.render(_doc(authors=authors, year=2024), "apa7")
    assert ref.startswith("Diallo, F. B. A., Yansané, A., Sow, A., & Barry, M. M.")
    assert "Conakry" not in ref.split(" (")[0]


def test_nom_de_famille_en_capitales_avant_les_prenoms():
    """Convention « NOM Prénoms » des sources africaines (D14, campagne réelle).

    « ABBE Hermann » : l'ancien code prenait la fin pour le nom et éclatait le NOM en initiales
    (« Hermann, A. B. B. E. »). La convention détectée dans le document s'applique à tous ses
    auteurs : « Gbame Hervé Daniel » → « Gbame, H. D. ».
    """
    ref = styles.render(_doc(authors=["Gbame Hervé Daniel", "ABBE Hermann"], year=2022), "apa7")
    assert ref.startswith("Gbame, H. D. & Abbe, H.")


def test_nom_de_famille_en_capitales_apres_les_prenoms_et_compose():
    """« Boris Noé MANHOULI DANMOU » (D46, campagne réelle) : nom COMPOSÉ en capitales.

    L'ancien code prenait « DANMOU » seul pour le nom et éclatait « MANHOULI » en
    « M. A. N. H. O. U. L. I. ».
    """
    ref = styles.render(_doc(authors=["Boris Noé MANHOULI DANMOU", "Élisée Emmanuel KOUAM TATCHEMO",
                                      "Léa Clodiane NONGNI"], year=2024), "apa7")
    assert ref.startswith("Manhouli Danmou, B. N., Kouam Tatchemo, É. E., & Nongni, L. C.")


def test_initiales_courtes_devant_le_nom_ne_sont_pas_un_nom_de_famille():
    """« MM Barry », « FBA Diallo » : forme « initiales + nom », PAS la convention « NOM d'abord ».

    Régression : détecter la convention sur un bloc court provoquait « Fba, D. » et « Mm, B. ».
    """
    from literature_review_agent.bibliography.normalize import document_surname_first

    assert not document_surname_first(["FBA Diallo", "MM Barry"])
    ref = styles.render(_doc(authors=["FBA Diallo", "MM Barry"], year=2024), "apa7")
    assert ref.startswith("Diallo, F. B. A. & Barry, M. M.")


def test_initiales_collees_en_casse_mixte_reconnues():
    """« Conradie Wj » = nom « Conradie » + initiales « W. J. » (donnée OpenAlex réelle, D2).

    Le fournisseur abaisse parfois la seconde initiale. L'ancien code prenait alors « Wj » pour le
    nom de famille et rendait « Wj, C. ». Un bloc sans voyelle est un groupe d'initiales ; un nom
    court AVEC voyelle (« Li », « Wu ») reste un nom.
    """
    from literature_review_agent.bibliography.normalize import _is_initial

    assert _is_initial("Wj") and not _is_initial("Li") and not _is_initial("Wu")
    ref = styles.render(_doc(authors=["Conradie Wj", "Jeremias Jesaja De Klerk"], year=2019), "apa7")
    assert ref.startswith("Conradie, W. J. & De Klerk, J. J.")
