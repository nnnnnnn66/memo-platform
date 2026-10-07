"""Test 25 — une sortie LLM invalide est rejetée, jamais utilisée en l'état."""

import pytest

from probleme_helpers import StubLLM, as_json, problem_output

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.pipeline import orchestrator
from research_problem_agent.schemas.input import ProblemRequest

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


@pytest.mark.parametrize("sortie", [
    "Ceci n'est pas du JSON du tout.",
    "{'status': 'ready_for_verification'}",           # guillemets simples : JSON invalide
    '{"status": "ensemble", "cle_inconnue": 1}',      # clé hors schéma + statut invalide
])
def test_sortie_invalide_rejetee_apres_re_essai(offline, sortie):
    llm = StubLLM([sortie, sortie])  # deux tentatives, toutes deux invalides
    request = ProblemRequest(student_id="etu-1", subject_text=SUJET)

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(request, offline, llm)

    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR
    assert llm.calls == 2


def test_sortie_invalide_puis_valide_est_acceptee(offline):
    from probleme_helpers import VERIFIER_VERIFIED

    llm = StubLLM(["pas de json", as_json(problem_output(SUJET)), as_json(VERIFIER_VERIFIED)])
    result = orchestrator.analyze_problem(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), offline, llm)

    assert result.attempts == 2
    assert result.output.identified_problem.statement


def test_champ_hors_schema_rejete(offline):
    sortie = problem_output(SUJET)
    sortie["question_de_recherche"] = "Le télétravail réduit-il la productivité ?"
    llm = StubLLM([as_json(sortie), as_json(sortie)])

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(
            ProblemRequest(student_id="etu-1", subject_text=SUJET), offline, llm)

    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR
