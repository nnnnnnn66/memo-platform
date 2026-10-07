"""Test 16 — ancrage des sources : seule une source réellement récupérée est citable."""

from probleme_helpers import source_set_with

from research_problem_agent.pipeline import business_validation
from research_problem_agent.schemas.input import ProblemRequest
from research_problem_agent.schemas.output import ProblemOutput

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def _source_set():
    return source_set_with([{
        "provider": "openalex",
        "source": "Revue X",
        "title": "Télétravail et productivité",
        "url": "https://doi.org/10.1234/exemple",
        "doi": "10.1234/exemple",
        "publication_date": "2021-05-01",
        "source_type": "scientific",
        "snippet": "extrait réel",
    }])


def _output(source_id="S1", url="https://doi.org/10.1234/exemple", source_type="scientific"):
    return ProblemOutput.model_validate({
        "status": "ready_for_verification",
        "subject_reference": {"original": SUJET, "reformulated": ""},
        "identified_problem": {"statement": "Le télétravail dégrade la productivité."},
        "justifying_elements": [
            {"element": "Une étude montre une baisse de productivité",
             "source_id": source_id, "provenance": "external", "nature": "interpretation"},
        ],
        "sources": [{
            "source_id": source_id, "source": "Revue X", "title": "Télétravail et productivité",
            "url": url, "doi": "10.1234/exemple", "publication_date": "2021-05-01",
            "access_date": "2026-10-07", "information_used": "effet mesuré",
            "source_type": source_type, "confidence": 0.7, "verification_status": "verified",
        }],
        "provisional_formulation": "Formulation provisoire du problème.",
    })


def _request():
    return ProblemRequest(student_id="etu-1", subject_text=SUJET)


def test_source_reellement_recuperee_est_conforme():
    violations = business_validation.validate_business(_request(), _output(), _source_set())
    assert violations == []


def test_source_id_inconnu_est_rejete():
    violations = business_validation.validate_business(_request(), _output(source_id="S9"),
                                                       _source_set())
    assert any("source_id inexistant" in v for v in violations)


def test_url_non_correspondante_est_rejetee():
    violations = business_validation.validate_business(
        _request(), _output(url="https://fausse-revue.example/article"), _source_set())
    assert any("URL" in v for v in violations)


def test_type_de_source_incoherent_est_rejete():
    violations = business_validation.validate_business(
        _request(), _output(source_type="governmental"), _source_set())
    assert any("source_type" in v for v in violations)


def test_fait_infere_sans_source_est_rejete():
    output = _output(source_id="")
    output.sources = []
    output.justifying_elements[0].nature = "fact"
    output.justifying_elements[0].provenance = "inferred"
    violations = business_validation.validate_business(_request(), output, _source_set())
    assert any("déduction comme un fait" in v for v in violations)


def test_source_sans_provenance_external_est_rejetee():
    output = _output()
    output.justifying_elements[0].provenance = "provided"
    violations = business_validation.validate_business(_request(), output, _source_set())
    assert any("au lieu de « external »" in v for v in violations)


def test_external_sans_source_id_est_rejete():
    output = _output(source_id="")
    output.sources = []
    output.justifying_elements[0].provenance = "external"
    output.justifying_elements[0].nature = "interpretation"
    violations = business_validation.validate_business(_request(), output, _source_set())
    assert any("external sans source_id" in v for v in violations)
