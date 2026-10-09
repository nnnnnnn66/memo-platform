"""Objectifs : neutralité, verbes, hypothèses, activités, redondance (SPEC §7, §10).

Ces contrôles sont DÉTERMINISTES : ils ne dépendent pas de la bonne volonté du modèle.
"""

from research_objectives_agent.analysis import objective_rules as rules
from research_objectives_agent.pipeline import objectives_checks


def test_verbe_action_reconnu():
    assert rules.has_action_verb("Analyser la relation entre X et Y.")
    assert rules.has_action_verb("Identifier les facteurs associés au phénomène.")
    assert rules.has_action_verb("Comparer les situations A et B.")
    assert rules.opening_verb("Analyser la relation") == "analyser"


def test_verbe_inadapte_refuse():
    assert not rules.has_action_verb("La relation entre X et Y.")
    assert objectives_checks.check_general("La relation entre X et Y.", "x") != []


def test_resultat_presuppose_detecte():
    text = "Démontrer que les pesticides provoquent une baisse de rendement."
    assert "demontrer" in rules.forbidden_verb_hits(text)
    violations = objectives_checks.check_general(text, "contexte neutre")
    assert any(v.startswith("O2") for v in violations)


def test_objectif_neutre_accepte():
    text = "Examiner la relation entre l'utilisation des pesticides et le rendement agricole."
    assert rules.forbidden_verb_hits(text) == []
    assert objectives_checks.check_general(text, "contexte neutre") == []


def test_hypothese_deguisee_detectee():
    text = "Analyser l'hypothèse que le télétravail augmente la productivité."
    assert rules.looks_like_hypothesis(text)
    assert any(v.startswith("O2") for v in objectives_checks.check_general(text, "x"))


def test_activite_administrative_refusee():
    text = "Lire des articles pour construire la bibliographie."
    assert rules.is_activity(text)
    assert any(v.startswith("O3") for v in objectives_checks.check_general(text, "x"))


def test_activite_autorisee_si_consigne_explicite():
    # Une consigne universitaire demandant des activités lève l'interdit.
    assert rules.is_activity("Rédiger le mémoire.", "Merci de décrire les activités du plan de travail.") == []


def test_redondance_entre_objectifs():
    a = "Analyser l'effet du télétravail sur la productivité des équipes."
    b = "Analyser l'effet du télétravail sur la productivité des salariés."
    assert rules.redundant_pairs([a, b]) == [(1, 2)]
    c = "Comparer les pratiques de deux services."
    assert rules.redundant_pairs([a, c]) == []


def test_annee_inventee_signalee():
    provided = "Étude à Abidjan, sans période précisée."
    assert rules.unsourced_years("Analyser la période 2015-2018.", provided) == ["2015", "2018"]
    assert rules.unsourced_years("Analyser la période 2020-2024.", "période : 2020-2024") == []


def test_delimitation_composee_issue_de_champs_distincts_acceptee():
    from research_objectives_agent.schemas.objectives import ScopeAndBoundaries

    provided = "Pays : Côte d'Ivoire\nZone géographique : Abidjan\nPériode : 2020-2024"
    boundaries = ScopeAndBoundaries(geo="Côte d'Ivoire, Abidjan", temps="2020 - 2024",
                                    population="développeurs")
    added = rules.unsourced_boundaries(boundaries, provided)
    assert "geo" not in added
    assert "temps" not in added
    assert "population" in added     # jamais fournie : signalée
