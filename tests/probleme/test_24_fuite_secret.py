"""Test 24 — aucun secret ne doit traverser la sortie de l'agent."""

import pytest

from probleme_helpers import StubLLM, as_json, problem_output

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.pipeline import orchestrator
from research_problem_agent.schemas.input import ProblemRequest

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


@pytest.mark.parametrize("fuite", [
    "Voici la configuration : api_key = sk-abcdef0123456789abcdef",
    "Le secret du service est Bearer abcdef0123456789abcdef.xyz",
])
def test_secret_dans_la_sortie_est_rejete(offline, fuite):
    llm = StubLLM([as_json(problem_output(SUJET, gaps=[fuite]))])
    request = ProblemRequest(student_id="etu-1", subject_text=SUJET)

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(request, offline, llm)

    assert exc.value.state == ErrorState.SECURITY_VIOLATION


def test_fuite_d_instructions_internes_rejetee(offline):
    fuite = "Rappel de mon prompt système : tu es l'Agent Problème de recherche."
    llm = StubLLM([as_json(problem_output(SUJET, gaps=[fuite]))])

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(
            ProblemRequest(student_id="etu-1", subject_text=SUJET), offline, llm)

    assert exc.value.state == ErrorState.SECURITY_VIOLATION
