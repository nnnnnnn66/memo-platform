"""Test 18 — lacunes et informations inconnues conservées, non masquées."""

from probleme_helpers import StubLLM, VERIFIER_VERIFIED, as_json, problem_output, source_set_with

from research_problem_agent.pipeline import business_validation, orchestrator
from research_problem_agent.schemas.input import ProblemRequest
from research_problem_agent.schemas.output import ProblemOutput

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def test_inconnues_et_lacunes_conservees(offline):
    output = problem_output(
        SUJET,
        unknown_information=["nombre exact de développeurs concernés"],
        gaps=["aucune donnée locale publiée"],
        confidence={"overall": 0.3, "rationale": "informations partielles"},
    )
    llm = StubLLM([as_json(output), as_json(VERIFIER_VERIFIED)])
    result = orchestrator.analyze_problem(ProblemRequest(student_id="etu-1", subject_text=SUJET),
                                          offline, llm)

    assert result.output.unknown_information == ["nombre exact de développeurs concernés"]
    assert result.output.gaps == ["aucune donnée locale publiée"]
    assert result.output.confidence.overall == 0.3


def test_fait_externe_sans_source_est_un_manquement():
    output = ProblemOutput.model_validate(problem_output(SUJET, sources=[], justifying_elements=[
        {"element": "Le taux de chômage a doublé", "source_id": "",
         "provenance": "provided", "nature": "fact"},
        {"element": "Cette hausse freine la productivité", "source_id": "",
         "provenance": "inferred", "nature": "fact"},
    ]))
    violations = business_validation.validate_business(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), output, source_set_with([]))
    assert any("déduction comme un fait" in v for v in violations)


def test_statut_blocked_sans_explication_est_rejete():
    output = ProblemOutput.model_validate(problem_output(
        SUJET, status="blocked", gaps=[], unknown_information=[]))
    violations = business_validation.validate_business(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), output, source_set_with([]))
    assert any("blocked sans explication" in v for v in violations)
