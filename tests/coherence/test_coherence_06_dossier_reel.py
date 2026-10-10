"""Passation RÉELLE : l'audit du dossier réellement produit par la chaîne 1 → 11.

Ces tests chargent les fichiers réellement produits par `scripts/e2e_chaine.py`. C'est ce qui a révélé
les défauts de passation des étapes précédentes : une clé de vérification différente, un contenu placé
sous une autre clé, un champ lu sous une forme qui n'existe pas.
"""

import json
import pathlib

import pytest

from research_coherence_verifier.schemas.input import CoherenceRequest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHAIN = ROOT / "workspace" / "chaine-live"


def _load(stage: int):
    path = CHAIN / f"stage{stage}.json"
    if not path.exists():
        pytest.skip(f"sortie réelle absente : {path}")
    return json.loads(path.read_text(encoding="utf-8"))["output"]


def _dossier_reel():
    return {
        "student_id": "chaine-etu", "session_id": "chaine-live",
        "discipline": "Sciences de gestion",
        "upstream_subject": _load(1), "upstream_problem": _load(2),
        "upstream_literature": _load(3), "upstream_problematic": _load(4),
        "upstream_question": _load(5), "upstream_objectives": _load(6),
        "upstream_hypotheses": _load(7), "upstream_methodology_diagnostic": _load(8),
        "upstream_methodology": _load(9), "upstream_results": _load(10),
        "upstream_conclusion": _load(11),
    }


def test_les_onze_sorties_reelles_sont_lues():
    request = CoherenceRequest(**_dossier_reel())
    for numero, payload in request.payloads().items():
        assert payload is not None, f"étape {numero} non lue"
        assert payload.is_verified, f"étape {numero} non reconnue vérifiée"
    assert len(request.effective_subject()) > 10
    assert len(request.effective_question()) > 10
    assert request.effective_specific_objectives()
    assert request.upstream_results.computed_ids()


def test_le_dossier_reel_est_complet_et_exploitable():
    from research_coherence_verifier.analysis import coherence_rules
    from research_coherence_verifier.pipeline import prerequisites

    request = CoherenceRequest(**_dossier_reel())
    dossier, constats = coherence_rules.run_facts(request)
    assert len(dossier.etapes_presentes) == 11
    assert dossier.etapes_absentes == []
    assert dossier.exploitable
    assert not prerequisites.check(request)["needs_clarification"]
    # Aucun constat ne doit être FABRIQUÉ sur le dossier réel : tous portent une preuve.
    for constat in constats:
        assert str(constat.preuve).strip(), f"constat {constat.code} sans preuve"
        assert str(constat.recommandation).strip()


def test_audit_du_dossier_reel_sans_modele(settings):
    """Confrontation déterministe du dossier réel : X1–X12, aucun appel de modèle."""
    from research_coherence_verifier.pipeline import facts_stage

    request = CoherenceRequest(**_dossier_reel())
    dossier, constats = facts_stage.faits(request)
    codes = {c.code for c in constats}
    # Le dossier réel de la chaîne 1 → 11 est cohérent : aucune rupture bloquante ne peut apparaître.
    bloqueurs = [c for c in constats if c.severite.value == "bloqueur"]
    assert not bloqueurs, [c.constat for c in bloqueurs]
    assert "X2" not in codes
    print("constats sur le dossier réel :", sorted(codes))


def test_les_deux_cles_de_verification_sont_acceptees():
    ancienne = CoherenceRequest(student_id="e", upstream_problem={
        "identified_problem": {"statement": "Un problème de recherche documenté et distinct du sujet."},
        "validation": {"verified": True, "verifier_status": "verified"}})
    assert ancienne.upstream_problem.is_verified
    recente = CoherenceRequest(student_id="e", upstream_results={
        "computed_results": {"resultats": []},
        "verification_result": {"verified": True, "verifier_status": "verified"}})
    assert recente.upstream_results.is_verified
    non_verifiee = CoherenceRequest(student_id="e", upstream_results={
        "computed_results": {"resultats": []},
        "verification_result": {"verified": False, "verifier_status": "pending"}})
    assert not non_verifiee.upstream_results.is_verified


def test_le_contenu_de_l_etape_3_est_reconnu(settings):
    """Défaut réel : le contrôle de contenu doit accepter une étape dont le contenu vit sous une autre
    clé que celles attendues (l'étape 3 place sa revue dans `synthesis`)."""
    from research_coherence_verifier.analysis import coherence_rules

    request = CoherenceRequest(**_dossier_reel())
    assert coherence_rules._a_du_contenu(request.upstream_literature)
    _, constats = coherence_rules.run_facts(request)
    assert "X12" not in {c.code for c in constats}
