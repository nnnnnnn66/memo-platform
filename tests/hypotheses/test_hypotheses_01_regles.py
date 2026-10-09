"""Hypothèses : règles déterministes (SPEC §7, §10). Aucun LLM."""

from research_hypotheses_agent.analysis import hypothesis_rules as rules
from research_hypotheses_agent.pipeline import hypotheses_checks
from research_hypotheses_agent.schemas.hypotheses import DecisionCode, Hypothesis
from research_hypotheses_agent.schemas.output import HypothesisStatus, HypothesesOutput


def _output(decision, hypotheses=()):
    return HypothesesOutput(status=HypothesisStatus.ready_for_verification,
                            hypotheses_decision=decision,
                            research_hypotheses=list(hypotheses))


def test_question_n_est_pas_une_hypothese():
    assert rules.looks_like_question("Le télétravail influence-t-il la productivité ?")
    assert rules.looks_like_question("Comment le télétravail agit-il ?")
    assert not rules.looks_like_question("Le télétravail est associé à la productivité.")


def test_objectif_n_est_pas_une_hypothese():
    assert rules.looks_like_objective("Analyser la relation entre X et Y.")
    assert rules.looks_like_objective("Identifier les facteurs associés.")
    assert not rules.looks_like_objective("Le télétravail est associé à la productivité.")


def test_fait_presuppose_detecte():
    text = "Il est démontré que le télétravail augmente la productivité."
    assert rules.presupposed_fact_hits(text)


def test_causalite_non_etablie_detectee():
    text = "Le télétravail provoque une baisse de productivité."
    assert "provoque" in rules.causal_hits(text)
    assert not rules.causal_is_justified("provoque", "contexte neutre")
    assert rules.causal_is_justified("provoque", "l'étude a montré que le télétravail provoque X")


def test_examinable():
    assert rules.has_relation_marker("La coordination est associée à la productivité.")
    assert rules.is_examinable("La coordination est associée à la productivité.")
    assert rules.is_examinable("Proposition quelconque.", ["un indicateur à collecter"])
    assert not rules.is_examinable("Le télétravail existe.", [])


def test_redondance_des_hypotheses():
    a = "La coordination des équipes est associée à la productivité des salariés."
    b = "La coordination des équipes est associée à la productivité des salariés."
    assert rules.duplicate_hypotheses([a, b]) == [(1, 2)]
    c = "L'intensité du télétravail varie selon les métiers."
    assert rules.duplicate_hypotheses([a, c]) == []


def test_decision_incoherente_signalee(request_factory):
    # Décision « pas d'hypothèses » mais des hypothèses présentes.
    out = _output(DecisionCode.not_required,
                  [Hypothesis(id="H1", formulation="X est associé à Y.",
                              justification="j")])
    violations = hypotheses_checks.apply(out, request_factory())
    assert any(v.startswith("H1") for v in violations)


def test_hypothese_a_presuppose_refusee(request_factory):
    out = _output(DecisionCode.recommended, [
        Hypothesis(id="H1", formulation="Il est démontré que le télétravail réduit la productivité.",
                   justification="j", required_data=["x"])])
    violations = hypotheses_checks.apply(out, request_factory())
    assert any(v.startswith("H3") for v in violations)


def test_causalite_non_justifiee_refusee(request_factory):
    out = _output(DecisionCode.recommended, [
        Hypothesis(id="H1", formulation="Le télétravail provoque une baisse de productivité.",
                   justification="j", required_data=["x"])])
    violations = hypotheses_checks.apply(out, request_factory())
    assert any(v.startswith("H4") for v in violations)


def test_hypothese_neutre_acceptee(request_factory):
    out = _output(DecisionCode.recommended, [
        Hypothesis(id="H1",
                   formulation="La coordination des équipes est associée à la productivité.",
                   justification="La problématique le suggère.", required_data=["indicateur"])])
    assert hypotheses_checks.apply(out, request_factory()) == []
