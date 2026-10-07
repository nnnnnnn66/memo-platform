"""Test 27 — hallucination de source : impossible par construction."""

import pytest

from probleme_helpers import StubLLM, as_json, phase1_output, problem_output, source_set_with

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.pipeline import orchestrator, sources_stage
from research_problem_agent.schemas.input import ProblemRequest

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def _source_set():
    return source_set_with([{
        "provider": "openalex",
        "source": "Revue X",
        "title": "Télétravail et productivité",
        "url": "https://doi.org/10.1234/reel",
        "doi": "10.1234/reel",
        "publication_date": "2021-05-01",
        "source_type": "scientific",
        "snippet": "extrait réel",
    }])


def _output_avec_fausse_source():
    output = problem_output(SUJET)
    output["sources"] = [{
        "source_id": "S42", "source": "Journal inventé", "title": "Étude imaginaire",
        "url": "https://doi.org/10.5555/invente", "doi": "10.5555/invente",
        "publication_date": "2023-01-01", "access_date": "2026-10-07",
        "information_used": "statistique inventée", "source_type": "scientific",
        "confidence": 0.9, "verification_status": "verified",
    }]
    output["justifying_elements"] = [{
        "element": "Une étude montre 40 % de baisse", "source_id": "S42",
        "provenance": "inferred", "nature": "fact",
    }]
    return output


def test_pipeline_refuse_une_source_inventee(settings, monkeypatch):
    monkeypatch.setattr(sources_stage, "retrieve", lambda *a, **k: _source_set())
    fausse = _output_avec_fausse_source()
    llm = StubLLM([as_json(phase1_output()), as_json(fausse), as_json(fausse)])

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(
            ProblemRequest(student_id="etu-1", subject_text=SUJET), settings, llm)

    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR


def test_citation_correcte_acceptee(settings, monkeypatch):
    from probleme_helpers import VERIFIER_VERIFIED

    monkeypatch.setattr(sources_stage, "retrieve", lambda *a, **k: _source_set())
    correct = problem_output(SUJET)
    correct["sources"] = [{
        "source_id": "S1", "source": "Revue X", "title": "Télétravail et productivité",
        "url": "https://doi.org/10.1234/reel", "doi": "10.1234/reel",
        "publication_date": "2021-05-01", "access_date": "2026-10-07",
        "information_used": "effet mesuré sur la productivité", "source_type": "scientific",
        "confidence": 0.7, "verification_status": "verified",
    }]
    correct["justifying_elements"] = [{
        "element": "L'étude mesure un effet négatif", "source_id": "S1",
        "provenance": "external", "nature": "interpretation",
    }]
    llm = StubLLM([as_json(phase1_output()), as_json(correct), as_json(VERIFIER_VERIFIED)])

    result = orchestrator.analyze_problem(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), settings, llm)

    assert result.source_ids == ["S1"]
    assert result.output.sources[0].source_id == "S1"
    assert result.output.validation.verified is True
