"""MOTEUR DÉTERMINISTE : les chiffres viennent du code (vérifiés à la main)."""

from resultats_helpers import CSV

from research_results_analysis_agent.analysis import data_engine


def _by_libelle(results, fragment):
    for resultat in results:
        if fragment in resultat["libelle"]:
            return resultat
    return None


def test_profil_du_jeu():
    profil = data_engine.profile(CSV)
    assert profil["lignes"] == 6
    assert profil["colonnes"] == 4
    natures = {v["nom"]: v["nature"] for v in profil["variables"]}
    assert natures["jours_teletravail"] == "numerique"
    assert natures["ville"] == "categorielle"
    manquants = {v["nom"]: v["manquants"] for v in profil["variables"]}
    assert manquants["jours_teletravail"] == 1


def test_effectif_moyenne_mediane_etendue():
    results = data_engine.compute(CSV)
    assert _by_libelle(results, "nombre de lignes")["valeur"] == "6"
    productivite = [r for r in results if r["variable"] == "productivite"]
    valeurs = {r["methode"]: r["valeur"] for r in productivite}
    # 7 + 5 + 6 + 8 + 5 + 6 = 37 ; 37 / 6 = 6,166…
    assert valeurs["moyenne"].startswith("6,1")   # 37 / 6 = 6,166…
    assert valeurs["mediane"] == "6"          # valeurs triées : 5 5 6 6 7 8 → (6+6)/2
    assert valeurs["minimum"] == "5"
    assert valeurs["maximum"] == "8"
    assert valeurs["etendue"] == "3"


def test_frequences_par_modalite():
    results = data_engine.compute(CSV)
    frequences = [r for r in results if r["methode"] == "frequence"]
    assert frequences
    pourcentages = {r["groupe"]: r["valeur"] for r in frequences if r["variable"] == "ville"}
    # 4 Abidjan sur 6 réponses = 66,67 %
    assert pourcentages.get("Abidjan", "").startswith("66")


def test_croisement_moyenne_par_groupe():
    results = data_engine.compute(CSV)
    croisements = [r for r in results if r["methode"] == "moyenne_par_groupe"]
    assert croisements
    abidjan = [r for r in croisements if r["groupe"] == "Abidjan"]
    assert abidjan
    assert abidjan[0]["effectif"] == 4


def test_colonne_identifiant_non_calculee():
    """Une colonne d'identification ne reçoit pas de moyenne (bruit inutile)."""
    results = data_engine.compute(CSV)
    assert not [r for r in results if r["variable"] == "id"]


def test_valeurs_manquantes_declarees():
    results = data_engine.compute(CSV)
    manquants = _by_libelle(results, "valeurs manquantes")
    assert manquants is not None
    assert manquants["valeur"] == "1"


def test_separateur_point_virgule_et_virgule_decimale():
    texte = "ville;note\nAbidjan;7,5\nBouake;6,5\n"
    results = data_engine.compute(texte)
    moyenne = [r for r in results if r["methode"] == "moyenne"][0]
    assert moyenne["valeur"] == "7"


def test_entree_vide_ou_non_tabulaire():
    assert data_engine.compute("") == []
    assert data_engine.compute("   ") == []


def test_documents_corpus():
    class Doc:
        periode = "2021"
        type = "rapport"

    results = data_engine.compute_documents([Doc(), Doc()])
    assert _by_libelle(results, "nombre de documents")["valeur"] == "2"


def test_liste_blanche_contient_les_valeurs_calculees_et_les_petits_entiers():
    results = data_engine.compute(CSV)
    allowed = data_engine.numeric_whitelist(results, ["Le questionnaire a recueilli 6 réponses."])
    assert "6,17" in allowed or any(v.startswith("6,17") for v in allowed)
    assert "6" in allowed
    assert "3" in allowed          # petit entier toléré (dénombrement d'objets)
