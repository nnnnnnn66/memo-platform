"""Test 20 — fidélité : le sujet reçu est recopié exactement, jamais réécrit."""

from probleme_helpers import StubLLM, VERIFIER_VERIFIED, as_json, problem_output, source_set_with

from research_problem_agent.pipeline import business_validation, orchestrator
from research_problem_agent.schemas.input import ProblemRequest
from research_problem_agent.schemas.output import ProblemOutput

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def test_sujet_modifie_est_rejete():
    output = ProblemOutput.model_validate(problem_output("le télétravail et la productivité"))
    violations = business_validation.validate_business(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), output, source_set_with([]))
    assert any("R1" in v for v in violations)


def test_sujet_recopie_exactement_est_conforme(offline):
    llm = StubLLM([as_json(problem_output(SUJET)), as_json(VERIFIER_VERIFIED)])
    result = orchestrator.analyze_problem(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), offline, llm)
    assert result.output.subject_reference.original == SUJET
    assert result.output.validation.verified is True


def test_le_verificateur_recoit_toutes_les_donnees_de_l_etudiant(offline):
    """Sans le contexte complet, le vérificateur prendrait des faits fournis pour des inventions."""
    llm = StubLLM([as_json(problem_output(SUJET)), as_json(VERIFIER_VERIFIED)])
    orchestrator.analyze_problem(
        ProblemRequest(student_id="etu-1", subject_text=SUJET,
                       subject_context="Entreprise de 120 salariés",
                       observations="Le directeur observe une baisse",
                       discipline="Sciences de gestion"),
        offline, llm)

    message_verificateur = llm.sent[1]["user"]
    assert "<donnees_etudiant_non_fiables>" in message_verificateur
    assert "Entreprise de 120 salariés" in message_verificateur
    assert "Le directeur observe une baisse" in message_verificateur
    assert "Sciences de gestion" in message_verificateur
