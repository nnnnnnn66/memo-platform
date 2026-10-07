"""Test 17 — sujet trop vague : questions ciblées, pas de passage au vérificateur."""

from probleme_helpers import StubLLM, as_json, problem_output

from research_problem_agent.pipeline import orchestrator
from research_problem_agent.schemas.input import ProblemRequest
from research_problem_agent.schemas.output import ProblemStatus


def test_sujet_vague_demande_clarification(offline):
    vague = problem_output(
        "le sport",
        status="needs_clarification",
        identified_problem={"statement": "", "situation": "", "why_problematic": ""},
        provisional_formulation="",
        remaining_questions=["Quel phénomène précis ?", "Quelle population ?"],
    )
    llm = StubLLM([as_json(vague)])
    request = ProblemRequest(student_id="etu-1", subject_text="le sport")

    result = orchestrator.analyze_problem(request, offline, llm)

    assert result.output.status == ProblemStatus.needs_clarification
    assert result.output.remaining_questions
    # Le vérificateur n'est pas appelé : rien n'est prêt à être vérifié.
    assert result.verifier is None
    assert result.verifier_status == "pending"
    assert llm.calls == 1
