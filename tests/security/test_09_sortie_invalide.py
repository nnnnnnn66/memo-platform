"""Test 9 — Sortie invalide : le validateur rejette (OUTPUT_SCHEMA_ERROR)."""

import pytest

from helpers import StubLLM, subject_output
from subject_agent.core.errors import ErrorState, PipelineError
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest


def test_sortie_non_json_rejetee(settings):
    llm = StubLLM(["ceci n'est pas du JSON", "toujours pas"])
    request = prepare(SubjectRequest(student_id="x", subject_text="un sujet"))

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_subject(request, settings, llm)
    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR


def test_champ_hors_schema_rejete(settings):
    import json
    bad = subject_output("un sujet")
    bad["champ_interdit"] = "valeur"  # extra=forbid
    llm = StubLLM([json.dumps(bad), json.dumps(bad)])
    request = prepare(SubjectRequest(student_id="x", subject_text="un sujet"))

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_subject(request, settings, llm)
    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR
