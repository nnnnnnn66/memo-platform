"""Audit complet (LLM simulé, aucun réseau) : de bout en bout, y compris les cas d'échec."""

import pytest
from coherence_helpers import (
    StubLLM,
    dossier_complet,
    dossier_fusionne,
    dossier_normatif_non_examinable,
    dossier_reference_orpheline,
)

from research_coherence_verifier.core.errors import PipelineError
from research_coherence_verifier.pipeline import campaign


def test_audit_nominal_d_un_dossier_coherent(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)

    assert result.output.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert result.output.document_status.value == "en_attente_de_validation"
    assert result.output.report.verdict.value == "coherent"
    assert result.output.audit.constats == []
    assert result.output.non_verifiable                 # la portée est déclarée
    assert result.output.report.synthese
    assert result.llm_calls == 3                        # P1 + P2 + contrôleur


def test_la_portee_est_toujours_declaree(settings, request_factory):
    """Exigence centrale du porteur : dire ce que l'agent NE PEUT PAS vérifier."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    elements = {item.element for item in result.output.non_verifiable}
    for attendu in ("véracité des données recueillies", "originalité et plagiat",
                    "qualité rédactionnelle, orthographe, style",
                    "conformité aux règles locales de l'établissement"):
        assert attendu in elements, f"portée incomplète : {attendu} manquant"
    assert all(item.raison.strip() for item in result.output.non_verifiable)


def test_un_fait_bloquant_donne_le_verdict_incoherent(settings, request_factory):
    request = request_factory(**dossier_fusionne())
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    codes = {c.code for c in result.output.audit.constats}
    assert "X3" in codes
    assert result.output.report.verdict.value == "incoherent"


def test_un_fait_majeur_donne_le_verdict_coherent_avec_reserves(settings, request_factory):
    request = request_factory(**dossier_normatif_non_examinable())
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert {c.code for c in result.output.audit.constats} >= {"X7"}
    assert result.output.report.verdict.value == "coherent_avec_reserves"
    assert result.output.report.recommandations          # actionnable


def test_reference_orpheline_bloque(settings, request_factory):
    request = request_factory(**dossier_reference_orpheline())
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert "X9" in {c.code for c in result.output.audit.constats}
    assert result.output.report.verdict.value == "incoherent"


def test_un_constat_du_modele_sans_preuve_est_refuse(settings, request_factory):
    constats = [{"axe": "fidelite", "severite": "majeur", "elements": ["conclusion"],
                 "constat": "La conclusion exagère les résultats.",
                 "preuve": "", "recommandation": "Modérer l'affirmation."}]
    with pytest.raises(PipelineError) as exc:
        campaign.run(request_factory(), settings, StubLLM(constats=constats), allow_network=False)
    assert exc.value.state.value == "OUTPUT_SCHEMA_ERROR"


def test_un_constat_du_modele_sans_recommandation_est_refuse(settings, request_factory):
    constats = [{"axe": "service", "severite": "mineur", "elements": ["objectifs"],
                 "constat": "Un objectif est formulé de façon large.",
                 "preuve": "objectif spécifique n°2", "recommandation": ""}]
    with pytest.raises(PipelineError):
        campaign.run(request_factory(), settings, StubLLM(constats=constats), allow_network=False)


def test_un_fait_infirme_avec_motif_est_reporte_non_supprime(settings, request_factory):
    request = request_factory(**dossier_normatif_non_examinable())
    stub = StubLLM(faits_infirmes=["X7"],
                   motifs=["Le protocole prévoit une analyse de contenu thématique qui permet "
                           "d'examiner une relation déclarée."])
    result = campaign.run(request, settings, stub, allow_network=False)
    assert "X7" not in {c.code for c in result.output.audit.constats}
    assert "X7" in {c.code for c in result.output.audit.constats_infirmes}
    assert result.output.audit.constats_infirmes[0].motif_suite
    assert result.output.report.verdict.value == "coherent"


def test_un_fait_infirme_sans_motif_est_refuse(settings, request_factory):
    stub = StubLLM(faits_infirmes=["X7"], motifs=[])
    with pytest.raises(PipelineError) as exc:
        campaign.run(request_factory(**dossier_normatif_non_examinable()), settings, stub,
                     allow_network=False)
    assert exc.value.state.value == "OUTPUT_SCHEMA_ERROR"


def test_dossier_entierement_non_verifie_est_refuse(settings, request_factory):
    payload = dossier_complet()
    for cle in list(payload):
        if cle.startswith("upstream_") and isinstance(payload[cle], dict):
            payload[cle] = {**payload[cle], "verification_result": {"verified": False}}
    with pytest.raises(PipelineError) as exc:
        campaign.run(request_factory(**payload), settings, StubLLM(), allow_network=False)
    assert exc.value.state.value == "MISSING_INFORMATION"


def test_dossier_incomplet_demande_des_precisions(settings, request_factory):
    from coherence_helpers import dossier_incomplet
    result = campaign.run(request_factory(**dossier_incomplet()), settings, StubLLM(),
                          allow_network=False)
    assert result.output.status.value in ("needs_clarification", "awaiting_human_validation")
    if result.output.status.value == "needs_clarification":
        assert result.output.questions_for_human
        assert any("question" in q.lower() for q in result.output.questions_for_human)


def test_confidence_explicite_son_calcul(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert 0.0 <= result.output.confidence.overall <= 1.0
    assert "calcul" in result.output.confidence.rationale


def test_evidence_comptabilise_les_constats(settings, request_factory):
    request = request_factory(**dossier_reference_orpheline())
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert result.output.evidence.constats >= 1
    assert result.output.evidence.constats_deterministes >= 1
