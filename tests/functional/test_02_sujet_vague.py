"""Test 2 — Sujet vague : l'agent doit demander des précisions (needs_clarification)."""

from helpers import StubLLM, as_json, subject_output
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest

TXT = "le sport"


def test_sujet_vague_demande_precisions(settings):
    out = subject_output(
        TXT,
        status="needs_clarification",
        questions_for_student=["Quel sport précisément ?", "Quelle population ?", "Quel espace ?"],
    )
    llm = StubLLM([as_json(out)])
    request = prepare(SubjectRequest(student_id="s2", subject_text=TXT))

    result = orchestrator.analyze_subject(request, settings, llm)

    assert result.output.status.value == "needs_clarification"
    assert result.output.questions_for_student
    assert result.verifier is None  # pas de vérification tant que ce n'est pas prêt
