"""Test 11 — Hallucination : une déduction du modèle ne peut être présentée comme vérifiée."""

from helpers import subject_output
from subject_agent.pipeline import business_validation
from subject_agent.schemas.input import SubjectRequest
from subject_agent.schemas.output import SubjectOutput

TXT = "un sujet"


def _request():
    return SubjectRequest(student_id="x", subject_text=TXT)


def test_model_inference_non_verifiee_rejetee():
    out = subject_output(TXT, evidence=[{
        "source": "", "title": "", "url": "", "publication_date": "", "access_date": "",
        "information_used": "statistique inventée",
        "source_type": "model_inference", "confidence": 0.9,
        "verification_status": "verified",
    }])
    violations = business_validation.validate_business(_request(), SubjectOutput.model_validate(out))
    assert any(v.startswith("R4") for v in violations)


def test_source_externe_sans_source_rejetee():
    out = subject_output(TXT, evidence=[{
        "source": "", "title": "", "url": "", "publication_date": "", "access_date": "",
        "information_used": "affirmation externe",
        "source_type": "external", "confidence": 0.7,
        "verification_status": "not_verified",
    }])
    violations = business_validation.validate_business(_request(), SubjectOutput.model_validate(out))
    assert any(v.startswith("R4") for v in violations)
