"""Test 14 — Robustesse du vérificateur.

Un modèle réel renvoie parfois `corrections`/`flags` sous forme d'objets au lieu de
chaînes. Le vérificateur doit normaliser ces listes sans faire échouer tout le pipeline.
(Régression constatée en exécution réelle, pas reproduite par les tests à LLM simulé.)
"""

from helpers import StubLLM, VERIFIER_VERIFIED, as_json, subject_output
from subject_agent.pipeline import orchestrator
from subject_agent.pipeline.input_controller import prepare
from subject_agent.pipeline.subject_verifier import _to_strings
from subject_agent.schemas.input import SubjectRequest

TXT = "Impact du télétravail sur la productivité des développeurs en Côte d'Ivoire"

VERIFIER_OBJETS = {
    "agent": "subject_verifier",
    "version": "1.0",
    "verdict": "corrections_requested",
    "controls": [{"code": "C2", "resultat": "echec", "detail": "période manquante"}],
    "corrections": [{"code": "C2", "champ": "temporal_scope", "detail": "préciser la période"}],
    "flags": [{"code": "F1", "detail": "à surveiller"}],
}


def test_to_strings_aplatit_les_objets_sans_perte():
    assert _to_strings([{"code": "C2", "champ": "espace", "detail": "préciser"}]) == [
        "C2 — espace — préciser"
    ]
    assert _to_strings(["déjà une chaîne"]) == ["déjà une chaîne"]
    assert _to_strings([]) == []


def test_verificateur_accepte_corrections_en_objets(settings):
    llm = StubLLM([as_json(subject_output(TXT)), as_json(subject_output(TXT))])
    vllm = StubLLM([as_json(VERIFIER_OBJETS), as_json(VERIFIER_VERIFIED)])
    request = prepare(SubjectRequest(student_id="s14", subject_text=TXT))

    result = orchestrator.analyze_subject(request, settings, llm, vllm)

    assert result.verifier_status == "verified"
    assert result.output.validation.verified is True
    assert result.verifications == 2  # correction demandée (objets) puis validée
