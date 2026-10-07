"""Test 19 — anti-fusion : l'agent ne produit ni problématique ni question de recherche."""

import pytest

from probleme_helpers import StubLLM, as_json, problem_output, source_set_with

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.pipeline import business_validation, orchestrator
from research_problem_agent.schemas.input import ProblemRequest
from research_problem_agent.schemas.output import ProblemOutput

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


@pytest.mark.parametrize("texte", [
    "La problématique de ce travail porte sur l'organisation du travail.",
    "La question de recherche est : le télétravail réduit-il la productivité ?",
    "Hypothèse : le télétravail réduit la productivité.",
])
def test_marqueurs_interdits_rejetes(texte):
    output = ProblemOutput.model_validate(
        problem_output(SUJET, provisional_formulation=texte))
    violations = business_validation.validate_business(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), output, source_set_with([]))
    assert any("fusion interdite" in v for v in violations)


def test_pipeline_refuse_une_sortie_fusionnee(offline):
    """Deux tentatives interdites → échec contrôlé, jamais transmis à l'étudiant."""
    fusionne = problem_output(SUJET, provisional_formulation="La problématique retenue est claire.")
    llm = StubLLM([as_json(fusionne), as_json(fusionne)])

    with pytest.raises(PipelineError) as exc:
        orchestrator.analyze_problem(
            ProblemRequest(student_id="etu-1", subject_text=SUJET), offline, llm)

    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR
    assert "2" in str(llm.calls) or llm.calls == 2
