"""Test 1 — Sujet clair : l'agent produit une fiche prête pour vérification,
le vérificateur valide → statut verified posé par le vérificateur."""

from helpers import StubLLM, VERIFIER_VERIFIED, as_json, subject_output
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest

TXT = "Impact du télétravail sur la productivité des développeurs en Côte d'Ivoire"


def test_sujet_clair_valide_par_verificateur(settings):
    llm = StubLLM([as_json(subject_output(TXT))])
    vllm = StubLLM([as_json(VERIFIER_VERIFIED)])
    request = prepare(SubjectRequest(student_id="s1", subject_text=TXT))

    result = orchestrator.analyze_subject(request, settings, llm, vllm)

    assert result.output.status.value == "ready_for_verification"
    assert result.verifier_status == "verified"
    assert result.output.validation.verified is True
    assert result.output.validation.verifier_status == "verified"
