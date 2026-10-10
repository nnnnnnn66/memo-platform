"""Portillon humain de l'audit (SPEC §12) : l'agent ne valide jamais son propre audit."""

import pytest
from coherence_helpers import StubLLM, dossier_reference_orpheline

from research_coherence_verifier.core.errors import PipelineError
from research_coherence_verifier.pipeline import campaign, decision_stage
from research_coherence_verifier.schemas.decision import DecisionRequest, DecisionValue


def _audit(settings, request_factory, **overrides):
    return campaign.run(request_factory(**overrides), settings, StubLLM(), allow_network=False)


def test_acceptation_pose_valide(settings, request_factory):
    result = _audit(settings, request_factory)
    assert result.output.student_validation.decision is None
    decide = campaign.decide(request_factory(), settings, StubLLM(), result.output,
                             DecisionRequest(decision=DecisionValue.accepted,
                                             student_comment="constats pris en compte"))
    assert decide.output.status.value == "validated"
    assert decide.output.document_status.value == "valide"
    assert decide.output.historique_versions


def test_refus_bloque_le_rapport(settings, request_factory):
    result = _audit(settings, request_factory)
    decide = campaign.decide(request_factory(), settings, StubLLM(), result.output,
                             DecisionRequest(decision=DecisionValue.refused,
                                             student_comment="constat X7 contesté"))
    assert decide.output.status.value == "blocked"
    assert decide.output.document_status.value == "a_reviser"


def test_l_acceptation_exige_le_controle(settings, request_factory):
    result = _audit(settings, request_factory)
    result.output.verification_result.verified = False
    with pytest.raises(PipelineError) as exc:
        decision_stage.apply(result.output, DecisionRequest(decision=DecisionValue.accepted),
                             request_factory())
    assert exc.value.state.value == "MISSING_INFORMATION"


def test_modification_sans_apport_refusee(settings, request_factory):
    result = _audit(settings, request_factory)
    with pytest.raises(PipelineError) as exc:
        campaign.decide(request_factory(), settings, StubLLM(), result.output,
                        DecisionRequest(decision=DecisionValue.modified))
    assert exc.value.state.value == "INVALID_INPUT"


def test_modification_avec_constats_contestes(settings, request_factory):
    result = _audit(settings, request_factory, **dossier_reference_orpheline())
    decide = campaign.decide(
        request_factory(), settings, StubLLM(), result.output,
        DecisionRequest(decision=DecisionValue.modified,
                        modified={"constats_contestes": ["X9 : la référence vient d'une étape "
                                                         "antérieure"]},
                        student_comment="vérification demandée"))
    assert decide.output.constats_retires_ou_reclasses
    assert decide.output.status.value in ("awaiting_human_validation", "verification_failed")


def test_aucune_etape_du_dossier_n_est_modifiee_par_la_decision(settings, request_factory):
    request = request_factory(**dossier_reference_orpheline())
    result = _audit(settings, request_factory, **dossier_reference_orpheline())
    avant = request.upstream_conclusion.references_resultats
    campaign.decide(request, settings, StubLLM(), result.output,
                    DecisionRequest(decision=DecisionValue.modified,
                                    provided_information="Le résultat R99 existe hors dossier."))
    assert request.upstream_conclusion.references_resultats == avant
