"""Diagnostic : règles déterministes (SPEC §7, §10). Aucun LLM."""

from methodology_diagnostic_agent.analysis import methodology_rules as rules
from methodology_diagnostic_agent.pipeline import diagnosis_checks
from methodology_diagnostic_agent.schemas.methodology import CategoryCode, MethodologyDiagnosis
from methodology_diagnostic_agent.schemas.output import MethodologyOutput, MethodologyStatus


def _choice(code="", proposition="", justification="j", conditions=None):
    return CategoryCode(code=code, proposition=proposition, justification=justification,
                        conditions=conditions or [])


def _output(approche, logique, type_r, strategie, collecte, analyse, articulation="a",
            coherence="c", hypotheses_examined=None):
    diag = MethodologyDiagnosis(
        approche=approche, logique=logique, type_recherche=type_r, strategie=strategie,
        collecte=collecte, analyse=analyse, articulation=articulation,
        coherence_question=coherence)
    return MethodologyOutput(status=MethodologyStatus.ready_for_verification, diagnosis=diag,
                             hypotheses_examined=hypotheses_examined or [])


def _baseline():
    return dict(
        approche=_choice("quantitative", "Approche quantitative"),
        logique=_choice("hypothetico_deductive", "Démarche hypothético-déductive"),
        type_r=_choice("explicative", "Recherche explicative"),
        strategie=_choice("enquete", "Enquête par questionnaire", conditions=["accès au terrain"]),
        collecte=[_choice(proposition="Questionnaire structuré")],
        analyse=[_choice(proposition="Analyse statistique descriptive et corrélation")],
    )


def test_normalisation_des_codes():
    assert rules.normalize_code("Étude de cas", "strategie") == "etude_de_cas"
    assert rules.normalize_code("hypothético-déductif", "logique") == "hypothetico_deductive"
    assert rules.normalize_code("Qualitative", "approche") == "qualitative"
    assert rules.normalize_code("expérimentale", "type_recherche") == "experimentale"
    assert rules.normalize_code("n'importe quoi", "approche") == "autre"
    assert rules.is_known("quantitative", "approche")


def test_causalite_sans_dispositif():
    assert rules.causal_hits("Démontrer une causalité entre X et Y.") 
    assert not rules.causality_is_justified("enquete")
    assert rules.causality_is_justified("experimentation")


def test_analyse_incompatible_avec_l_approche():
    assert rules.analysis_incompatible("qualitative", ["régression logistique"])
    assert not rules.analysis_incompatible("quantitative", ["régression logistique"])
    assert rules.analysis_incompatible("quantitative", ["analyse thématique"])


def test_categories_identiques_signalees():
    assert rules.same_text("Approche quantitative par questionnaire", "Approche quantitative par questionnaire")
    assert not rules.same_text("Approche quantitative", "Démarche inductive")


def test_diagnostic_coherent_accepte(request_factory):
    out = _output(**_baseline())
    assert diagnosis_checks.apply(out, request_factory()) == []


def test_causalite_non_justifiee_refusee(request_factory):
    params = _baseline()
    params["articulation"] = "La stratégie permettra de démontrer une causalité entre télétravail et productivité."
    out = _output(**params)
    assert any(v.startswith("M4") for v in diagnosis_checks.apply(out, request_factory()))


def test_causalite_justifiee_par_experimentation_acceptee(request_factory):
    params = _baseline()
    params["strategie"] = _choice("experimentation", "Protocole expérimental",
                                  conditions=["groupe témoin", "affectation aléatoire"])
    params["articulation"] = "Le dispositif permet d'examiner un effet causal."
    out = _output(**params)
    assert not any(v.startswith("M4") for v in diagnosis_checks.apply(out, request_factory()))


def test_categories_confondues_refusees(request_factory):
    params = _baseline()
    params["logique"] = _choice("hypothetico_deductive", "Approche quantitative")
    params["approche"] = _choice("quantitative", "Approche quantitative")
    out = _output(**params)
    assert any(v.startswith("M3") for v in diagnosis_checks.apply(out, request_factory()))


def test_approche_analyse_incompatibles_refusees(request_factory):
    params = _baseline()
    params["approche"] = _choice("qualitative", "Approche qualitative")
    params["analyse"] = [_choice(proposition="Régression logistique")]
    out = _output(**params)
    assert any(v.startswith("M5") for v in diagnosis_checks.apply(out, request_factory()))


def test_strategie_sans_condition_refusee(request_factory):
    params = _baseline()
    params["strategie"] = _choice("enquete", "Enquête par questionnaire")  # pas de conditions
    out = _output(**params)
    assert any(v.startswith("M6") for v in diagnosis_checks.apply(out, request_factory()))


def test_hypotheses_non_traitees_signalees(request_factory):
    out = _output(**_baseline())
    req = request_factory(hypotheses=["La coordination est associée à la productivité."])
    assert any(v.startswith("M7") for v in diagnosis_checks.apply(out, req))
