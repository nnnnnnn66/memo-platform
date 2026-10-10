"""Passation amont : les sorties RÉELLES de la chaîne alimentent l'agent 11.

Ces tests chargent les FICHIERS réellement produits (quand ils existent) : c'est ce qui a révélé les
défauts de passation des étapes précédentes.
"""

import json
import pathlib

import pytest

from research_conclusion_agent.pipeline import prerequisites
from research_conclusion_agent.schemas.input import ConclusionRequest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHAIN = ROOT / "workspace" / "chaine-live"


def _load(stage: int):
    path = CHAIN / f"stage{stage}.json"
    if not path.exists():
        pytest.skip(f"sortie réelle absente : {path}")
    return json.loads(path.read_text(encoding="utf-8"))["output"]


def test_resultats_reels_de_l_etape_10_acceptes():
    """La sortie RÉELLE de l'étape 10 doit être reconnue vérifiée et lue dans sa vraie forme."""
    results = _load(10)
    request = ConclusionRequest(student_id="e", upstream_results=results)
    assert request.upstream_results.is_verified
    assert request.results_status() in ("valide", "en_attente_de_validation")
    assert request.available_results()          # des identifiants R… existent
    assert request.effective_question()
    pre = prerequisites.check(request)
    assert pre["needs_clarification"] is False


def test_resultats_et_synthese_reels_lus():
    results = _load(10)
    request = ConclusionRequest(student_id="e", upstream_results=results)
    payload = request.upstream_results
    assert payload.computed_ids()
    assert isinstance(payload.resultats_retenus(), list)
    assert isinstance(payload.hypotheses_examinees(), list)
    assert isinstance(payload.conclusion_synthese(), list)


def test_hypotheses_reelles_de_l_etape_7_lues():
    hypotheses = _load(7)
    request = ConclusionRequest(student_id="e", upstream_hypotheses=hypotheses)
    for formulation in request.effective_hypotheses():
        assert isinstance(formulation, str) and formulation.strip()
        assert "{" not in formulation


def test_objectifs_reels_de_l_etape_6_lus():
    request = ConclusionRequest(student_id="e", upstream_objectives=_load(6))
    assert request.effective_general_objective()
    assert request.effective_specific_objectives()


def test_chaine_complete_1_a_10_alimente_l_etape_11():
    request = ConclusionRequest(
        student_id="chaine-etu", session_id="chaine-live", discipline="Sciences de gestion",
        upstream_subject=_load(1), upstream_problem=_load(2), upstream_literature=_load(3),
        upstream_problematic=_load(4), upstream_question=_load(5),
        upstream_objectives=_load(6), upstream_hypotheses=_load(7),
        upstream_methodology_diagnostic=_load(8), upstream_methodology=_load(9),
        upstream_results=_load(10))
    assert request.effective_subject()
    assert request.effective_question()
    assert request.effective_problem()
    assert request.effective_problematic()
    assert request.effective_general_objective()
    assert request.computed_ids()
    for payload in (request.upstream_subject, request.upstream_problem, request.upstream_literature,
                    request.upstream_problematic, request.upstream_question,
                    request.upstream_objectives, request.upstream_hypotheses,
                    request.upstream_methodology_diagnostic, request.upstream_methodology,
                    request.upstream_results):
        assert payload.is_verified, "une sortie réelle vérifiée doit être reconnue comme telle"


def test_les_deux_cles_de_verification_sont_acceptees():
    ancienne = ConclusionRequest(student_id="e", upstream_problem={
        "identified_problem": {"statement": "Problème."},
        "validation": {"verified": True, "verifier_status": "verified"}})
    assert ancienne.upstream_problem.is_verified
    recente = ConclusionRequest(student_id="e", upstream_results={
        "computed_results": {"resultats": []},
        "verification_result": {"verified": True, "verifier_status": "verified"}})
    assert recente.upstream_results.is_verified
    non_verifiee = ConclusionRequest(student_id="e", upstream_results={
        "computed_results": {"resultats": []},
        "verification_result": {"verified": False, "verifier_status": "pending"}})
    assert not non_verifiee.upstream_results.is_verified
