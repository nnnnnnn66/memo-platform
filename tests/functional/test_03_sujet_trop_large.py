"""Test 3 — Sujet trop large : l'agent propose des axes de délimitation."""

from helpers import StubLLM, as_json, subject_output
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest

TXT = "la mondialisation"


def test_sujet_trop_large_propose_axes(settings):
    out = subject_output(
        TXT,
        status="needs_clarification",
        identified_ambiguities=["sujet trop large : périmètre non borné"],
        questions_for_student=["Quel aspect de la mondialisation ?", "Quel espace ?", "Quelle période ?"],
    )
    llm = StubLLM([as_json(out)])
    request = prepare(SubjectRequest(student_id="s3", subject_text=TXT))

    result = orchestrator.analyze_subject(request, settings, llm)

    assert result.output.status.value == "needs_clarification"
    assert result.output.identified_ambiguities
    assert result.output.questions_for_student
