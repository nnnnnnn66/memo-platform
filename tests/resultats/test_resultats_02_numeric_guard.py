"""Garde numérique (Q2) : aucun chiffre publié ne sort du moteur."""

from research_results_analysis_agent.analysis import numeric_guard


def test_nombres_extraits():
    pairs = numeric_guard.numbers_in("Effectif 42, moyenne 6,17 et 80 % de réponses.")
    valeurs = {v for v, _ in pairs}
    assert {"42", "6,17", "80"} <= valeurs


def test_valeur_calculee_autorisee():
    assert numeric_guard.is_allowed("6,17", "", {"6,17"})


def test_valeur_inventee_refusee():
    violations = numeric_guard.check_texts(
        {"analyse": "La moyenne s'établit à 9,4 sur l'échelle."}, {"6,17"})
    assert violations
    assert "9,4" in violations[0]


def test_pourcentage_derive_tolere():
    """Un pourcentage calculable depuis un effectif est légitime."""
    assert numeric_guard.is_allowed("80", "%", {"80"})


def test_annee_non_signalee():
    """Les années ne sont pas des résultats : elles ne doivent pas déclencher de faux positif."""
    violations = numeric_guard.check_texts(
        {"analyse": "Les données portent sur l'année 2024."}, {"2024"})
    assert violations == []
