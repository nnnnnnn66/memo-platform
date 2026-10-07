"""Test 31 — les métadonnées d'une source citée viennent de l'API, jamais du modèle."""

from probleme_helpers import StubLLM, VERIFIER_VERIFIED, as_json, phase1_output, problem_output, source_set_with

from research_problem_agent.pipeline import orchestrator, sources_stage
from research_problem_agent.schemas.input import ProblemRequest

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"


def _source_set():
    return source_set_with([{
        "provider": "openalex",
        "source": "Annual Review of Psychology",
        "title": "Job Burnout",
        "url": "https://doi.org/10.1146/annurev.psych.52.1.397",
        "doi": "10.1146/annurev.psych.52.1.397",
        "publication_date": "2001-02-01",
        "source_type": "scientific",
        "snippet": "extrait réel",
    }])


def test_metadonnees_ecrasees_par_la_verite_de_l_api(settings, monkeypatch):
    monkeypatch.setattr(sources_stage, "retrieve", lambda *a, **k: _source_set())
    output = problem_output(SUJET)
    output["sources"] = [{
        "source_id": "S1",
        "source": "Revue approximative",          # le modèle se trompe sur la revue
        "title": "Titre approximatif",
        "url": "https://doi.org/10.1146/annurev.psych.52.1.397",   # URL correcte (vérifiée)
        "doi": "10.1146/annurev.psych.52.1.397",
        "publication_date": "2001",                # date approximative
        "access_date": "2026-10-07",
        "information_used": "effet mesuré",
        "source_type": "scientific",
        "confidence": 0.7,
        "verification_status": "not_verified",     # le modèle sous-déclare
    }]
    output["justifying_elements"] = [{
        "element": "L'étude documente le burnout", "source_id": "S1",
        "provenance": "external", "nature": "fact",
    }]
    llm = StubLLM([as_json(phase1_output()), as_json(output), as_json(VERIFIER_VERIFIED)])

    result = orchestrator.analyze_problem(
        ProblemRequest(student_id="etu-1", subject_text=SUJET), settings, llm)

    source = result.output.sources[0]
    assert source.title == "Job Burnout"                                # vérité de l'API
    assert source.source == "Annual Review of Psychology"
    assert source.publication_date == "2001-02-01"
    assert source.verification_status.value == "verified"               # récupérée = vérifiée
    assert source.confidence == 0.7                                     # jugement du modèle conservé
