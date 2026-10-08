"""Neutralité et forme de la question : contrôles DÉTERMINISTES (SPEC §10.C, §10.D)."""

from research_question_agent.analysis import question_rules as qr
from research_question_agent.pipeline import formulation_checks


def test_question_neutre_acceptee():
    q = "Dans quelle mesure le télétravail influence-t-il la productivité des développeurs ?"
    assert formulation_checks.check_question_text(q, "contexte sans prémisse") == []
    assert not qr.is_double_question(q)
    assert not qr.is_too_broad(q)


def test_presuppose_non_etabli_detecte():
    q = "Pourquoi cette politique est-elle inefficace ?"
    violations = formulation_checks.check_question_text(q, "contexte neutre sans jugement")
    assert any(v.startswith("F2") for v in violations)
    assert "inefficace" in qr.detect_premises(q)


def test_presuppose_etabli_par_les_entrees_accepte():
    q = "Pourquoi cette politique est-elle inefficace ?"
    # L'inefficacité est explicitement établie dans le contexte fourni par l'étudiant.
    context = "Le rapport officiel établit que la politique est inefficace depuis 2019."
    violations = formulation_checks.check_question_text(q, context)
    assert not any(v.startswith("F2") for v in violations)


def test_question_double_detectee():
    q = "Pourquoi le télétravail progresse-t-il et comment affecte-t-il la productivité ?"
    assert qr.is_double_question(q)
    assert any(v.startswith("F3") for v in formulation_checks.check_question_text(q, "x"))


def test_dans_quelle_mesure_n_est_pas_double():
    assert not qr.is_double_question("Dans quelle mesure X influence-t-il Y ?")


def test_question_trop_large_detectee():
    assert qr.is_too_broad("Quel est l'impact ?")
    assert any(v.startswith("F4")
               for v in formulation_checks.check_question_text("Quel est l'impact ?", "x"))


def test_delimitation_sans_source_signalee():
    scope = qr.__dict__  # placeholder pour prouver l'API via unsourced_boundaries
    from research_question_agent.schemas.question import ScopeAndBoundaries
    boundaries = ScopeAndBoundaries(geo="Abidjan", temps="", population="")
    added = qr.unsourced_boundaries(boundaries, "sujet sans mention géographique")
    assert "geo" in added


def test_delimitation_presente_dans_les_entrees_acceptee():
    from research_question_agent.schemas.question import ScopeAndBoundaries
    boundaries = ScopeAndBoundaries(geo="Abidjan", temps="2020-2024", population="")
    added = qr.unsourced_boundaries(boundaries, "étude menée à Abidjan entre 2020-2024")
    assert added == {}
