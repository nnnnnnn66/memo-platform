"""Passation amont : les sorties RÉELLES des étapes précédentes alimentent l'agent 9.

Ces tests chargent les FICHIERS réellement produits par la chaîne (quand ils existent) au lieu de
payloads fabriqués : c'est ce qui a révélé les défauts de passation des étapes précédentes.
"""

import json
import pathlib

import pytest

from methodology_agent.schemas.input import MethodologyRequest
from methodology_agent.pipeline import prerequisites

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHAIN = ROOT / "workspace" / "chaine-live"


def _load(stage: int):
    path = CHAIN / f"stage{stage}.json"
    if not path.exists():
        pytest.skip(f"sortie réelle absente : {path}")
    return json.loads(path.read_text(encoding="utf-8"))["output"]


def test_diagnostic_reel_de_l_etape_8_accepte():
    """La sortie RÉELLE de l'agent 8 doit être reconnue vérifiée et lue dans sa vraie forme."""
    diagnostic = _load(8)
    request = MethodologyRequest(student_id="e", upstream_methodology_diagnostic=diagnostic)
    assert request.upstream_methodology_diagnostic.is_verified
    assert request.diagnostic_status() in ("valide", "en_attente_de_validation")
    categories = request.diagnostic_categories()
    assert categories.get("approche")
    assert request.effective_question()
    pre = prerequisites.check(request)
    assert pre["needs_clarification"] is False


def test_objectifs_reels_de_l_etape_6_lus():
    objectives = _load(6)
    request = MethodologyRequest(student_id="e", upstream_objectives=objectives)
    assert request.effective_general_objective()
    assert request.effective_specific_objectives()


def test_hypotheses_reelles_de_l_etape_7_lues():
    hypotheses = _load(7)
    request = MethodologyRequest(student_id="e", upstream_hypotheses=hypotheses)
    # Les hypothèses arrivent sous forme d'objets : la FORMULATION est conservée.
    for formulation in request.effective_hypotheses():
        assert isinstance(formulation, str) and formulation.strip()
        assert "{" not in formulation


def test_chaine_complete_1_a_8_alimente_l_etape_9():
    """Toutes les sorties réelles de la chaîne, versées d'un coup dans l'entrée de l'étape 9."""
    request = MethodologyRequest(
        student_id="chaine-etu", session_id="chaine-live",
        discipline="Sciences de gestion",
        upstream_subject=_load(1), upstream_problem=_load(2), upstream_literature=_load(3),
        upstream_problematic=_load(4), upstream_question=_load(5),
        upstream_objectives=_load(6), upstream_hypotheses=_load(7),
        upstream_methodology_diagnostic=_load(8),
    )
    assert request.effective_subject()
    assert request.effective_problem()
    assert request.effective_problematic()
    assert request.effective_question()
    assert request.effective_general_objective()
    assert request.effective_specific_objectives()
    for payload in (request.upstream_subject, request.upstream_problem, request.upstream_literature,
                    request.upstream_problematic, request.upstream_question,
                    request.upstream_objectives, request.upstream_hypotheses,
                    request.upstream_methodology_diagnostic):
        assert payload.is_verified, "une sortie réelle vérifiée doit être reconnue comme telle"
    assert request.diagnostic_categories()
