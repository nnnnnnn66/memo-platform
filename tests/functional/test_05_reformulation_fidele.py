"""Test 5 — Reformulation : le vérificateur demande une correction, l'agent corrige,
puis le vérificateur valide (boucle corrective bornée)."""

from helpers import StubLLM, VERIFIER_VERIFIED, as_json, subject_output
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.schemas.input import SubjectRequest

TXT = "Effet de la formation continue sur la performance des PME"

CORRECTION = {
    "agent": "subject_verifier", "version": "1.0", "verdict": "corrections_requested",
    "controls": [{"code": "C1", "resultat": "echec", "detail": "reformulation non fidèle"}],
    "corrections": ["Reformule sans introduire de notion absente du sujet initial"],
    "flags": [],
}


def test_boucle_corrective_converge(settings):
    first = subject_output(TXT, subject={"original": TXT,
                                         "reformulated": "Un sujet déformé par l'agent"})
    corrected = subject_output(TXT, subject={"original": TXT,
                                             "reformulated": "Formulation fidèle et délimitée"})
    llm = StubLLM([as_json(first), as_json(corrected)])
    vllm = StubLLM([as_json(CORRECTION), as_json(VERIFIER_VERIFIED)])
    request = prepare(SubjectRequest(student_id="s5", subject_text=TXT))

    result = orchestrator.analyze_subject(request, settings, llm, vllm)

    assert result.verifier_status == "verified"
    assert result.output.validation.verified is True
    assert result.verifications == 2  # correction demandée puis validée
