"""Passation amont : les sorties RÉELLES de la chaîne alimentent l'agent 10.

Ces tests chargent les FICHIERS réellement produits (quand ils existent) : c'est ce qui a révélé les
défauts de passation des étapes précédentes.
"""

import json
import pathlib

import pytest

from research_results_analysis_agent.pipeline import prerequisites
from research_results_analysis_agent.schemas.input import ResultsAnalysisRequest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHAIN = ROOT / "workspace" / "chaine-live"


def _load(stage: int):
    path = CHAIN / f"stage{stage}.json"
    if not path.exists():
        pytest.skip(f"sortie réelle absente : {path}")
    return json.loads(path.read_text(encoding="utf-8"))["output"]


def test_methodologie_reelle_de_l_etape_9_acceptee():
    """La sortie RÉELLE de l'étape 9 doit être reconnue vérifiée et lue dans sa vraie forme."""
    methodology = _load(9)
    request = ResultsAnalysisRequest(student_id="e", upstream_methodology=methodology)
    assert request.upstream_methodology.is_verified
    assert request.methodology_status() in ("valide", "en_attente_de_validation")
    assert request.methodology_protocol()
    assert request.effective_question()
    pre = prerequisites.check(request)
    assert pre["blockers"] == [] or all("donnée" not in b for b in pre["blockers"])


def test_protocole_reel_lu_dans_ses_formes_reelles():
    methodology = _load(9)
    request = ResultsAnalysisRequest(student_id="e", upstream_methodology=methodology)
    protocol = request.methodology_protocol()
    assert protocol.get("approche")
    assert isinstance(request.techniques_prevues(), list)
    assert isinstance(request.analyses_prevues(), list)


def test_hypotheses_reelles_de_l_etape_7_lues():
    hypotheses = _load(7)
    request = ResultsAnalysisRequest(student_id="e", upstream_hypotheses=hypotheses)
    for formulation in request.effective_hypotheses():
        assert isinstance(formulation, str) and formulation.strip()
        assert "{" not in formulation


def test_objectifs_reels_de_l_etape_6_lus():
    request = ResultsAnalysisRequest(student_id="e", upstream_objectives=_load(6))
    assert request.effective_general_objective()
    assert request.effective_specific_objectives()


def test_chaine_complete_1_a_9_alimente_l_etape_10():
    request = ResultsAnalysisRequest(
        student_id="chaine-etu", session_id="chaine-live", discipline="Sciences de gestion",
        upstream_subject=_load(1), upstream_problem=_load(2), upstream_literature=_load(3),
        upstream_problematic=_load(4), upstream_question=_load(5),
        upstream_objectives=_load(6), upstream_hypotheses=_load(7),
        upstream_methodology_diagnostic=_load(8), upstream_methodology=_load(9))
    assert request.effective_subject()
    assert request.effective_question()
    assert request.effective_general_objective()
    assert request.methodology_protocol()
    for payload in (request.upstream_subject, request.upstream_problem, request.upstream_literature,
                    request.upstream_problematic, request.upstream_question,
                    request.upstream_objectives, request.upstream_hypotheses,
                    request.upstream_methodology_diagnostic, request.upstream_methodology):
        assert payload.is_verified, "une sortie réelle vérifiée doit être reconnue comme telle"


def test_les_deux_cles_de_verification_sont_acceptees():
    """Étapes 1-4 : `validation` ; étapes 5-9 : `verification_result`."""
    ancienne = ResultsAnalysisRequest(student_id="e", upstream_problem={
        "identified_problem": {"statement": "Problème."},
        "validation": {"verified": True, "verifier_status": "verified"}})
    assert ancienne.upstream_problem.is_verified
    recente = ResultsAnalysisRequest(student_id="e", upstream_methodology={
        "protocol": {}, "verification_result": {"verified": True, "verifier_status": "verified"}})
    assert recente.upstream_methodology.is_verified
    non_verifiee = ResultsAnalysisRequest(student_id="e", upstream_methodology={
        "protocol": {}, "verification_result": {"verified": False, "verifier_status": "pending"}})
    assert not non_verifiee.upstream_methodology.is_verified
