"""Test 15 — un problème identifiable et distinct du sujet passe la vérification."""

from probleme_helpers import StubLLM, VERIFIER_VERIFIED, as_json, problem_output

from research_problem_agent.pipeline import orchestrator
from research_problem_agent.schemas.input import ProblemRequest
from research_problem_agent.schemas.output import ProblemStatus

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def test_probleme_identifie_et_valide(offline):
    llm = StubLLM([as_json(problem_output(SUJET)), as_json(VERIFIER_VERIFIED)])
    request = ProblemRequest(student_id="etu-1", subject_text=SUJET,
                             subject_context="Entreprise de services numériques")

    result = orchestrator.analyze_problem(request, offline, llm)

    assert result.output.status == ProblemStatus.ready_for_verification
    assert result.output.identified_problem.statement
    assert result.output.provisional_formulation
    assert result.source_ids == []
    assert result.verifier is not None
    assert result.verifier.verdict.value == "verified"
    assert result.output.validation.verified is True
    assert result.output.validation.verifier_status == "verified"
    assert result.verifier_status == "verified"
