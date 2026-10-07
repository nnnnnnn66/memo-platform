"""Test 4 — Informations manquantes : l'agent identifie les informations nécessaires."""

from helpers import StubLLM, as_json, subject_output
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest

TXT = "la satisfaction des clients"


def test_infos_manquantes_identifiees(settings):
    out = subject_output(
        TXT,
        status="needs_clarification",
        missing_information=["population", "période", "espace", "type d'organisation"],
        questions_for_student=["Quels clients ?", "Sur quelle période ?", "Dans quel pays ?"],
    )
    llm = StubLLM([as_json(out)])
    request = prepare(SubjectRequest(student_id="s4", subject_text=TXT))

    result = orchestrator.analyze_subject(request, settings, llm)

    assert "population" in result.output.missing_information
    assert result.output.questions_for_student
