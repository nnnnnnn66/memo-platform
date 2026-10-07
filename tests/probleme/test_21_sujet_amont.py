"""Test 21 — liaison avec l'Agent Sujet : un sujet amont NON vérifié est refusé."""

import pytest

from probleme_helpers import StubLLM, VERIFIER_VERIFIED, as_json, problem_output

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.pipeline import orchestrator
from research_problem_agent.schemas.input import ProblemRequest, UpstreamSubject

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"

UPSTREAM = {
    "agent": "subject_agent",
    "version": "1.0",
    "status": "verified",
    "subject": {"original": SUJET, "reformulated": SUJET},
    "research_context": {"domain": "gestion", "object_of_study": "productivité",
                         "population": "développeurs", "geographical_scope": "Abidjan",
                         "temporal_scope": "2020-2024", "phenomenon": "télétravail"},
    "key_concepts": ["télétravail", "productivité"],
    "validation": {"verified": False, "verifier_status": "pending"},
}


def test_sujet_amont_non_verifie_refuse(offline):
    llm = StubLLM([as_json(problem_output(SUJET))])
    request = ProblemRequest(student_id="etu-1", subject_text=SUJET,
                             upstream_subject=UpstreamSubject.model_validate(UPSTREAM))

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(request, offline, llm)

    assert exc.value.state == ErrorState.MISSING_INFORMATION
    assert llm.calls == 0  # rien n'est envoyé au modèle


def test_sujet_amont_verifie_utilise(offline):
    verified = dict(UPSTREAM)
    verified["validation"] = {"verified": True, "verifier_status": "verified"}
    llm = StubLLM([as_json(problem_output(SUJET)), as_json(VERIFIER_VERIFIED)])
    request = ProblemRequest(student_id="etu-1", subject_text=SUJET,
                             upstream_subject=UpstreamSubject.model_validate(verified))

    result = orchestrator.analyze_problem(request, offline, llm)

    assert result.output.validation.verified is True
    assert "sujet_amont_verifie_non_fiable" in llm.sent[0]["user"]
    assert "Abidjan" in llm.sent[0]["user"]
