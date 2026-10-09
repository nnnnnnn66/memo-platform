"""Campagne complète (LLM simulé) : décision, statuts, vérificateur, honnêteté."""

import pytest

from research_hypotheses_agent.core.errors import PipelineError
from research_hypotheses_agent.pipeline import campaign
from hypotheses_helpers import StubLLM


def test_campagne_recommandee(settings, request_factory):
    llm = StubLLM(decision="HYPOTHESES_RECOMMENDED", verdict="verified")
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    out = result.output

    assert out.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert out.hypotheses_decision.value == "HYPOTHESES_RECOMMENDED"
    assert len(out.research_hypotheses) == 2
    assert out.evidence.llm_calls == 4          # P1 + P2 + P3 + vérificateur
    assert 0.0 <= out.confidence.overall <= 1.0
    assert out.confidence.rationale


def test_campagne_non_requise_sans_hypotheses(settings, request_factory):
    llm = StubLLM(decision="HYPOTHESES_NOT_REQUIRED", verdict="verified")
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    out = result.output

    assert out.hypotheses_decision.value == "HYPOTHESES_NOT_REQUIRED"
    assert out.research_hypotheses == []
    # P3 n'est PAS appelée : P1 + P2 + vérificateur = 3 appels.
    assert llm.calls == 3
    assert out.status.value == "awaiting_human_validation"


def test_campagne_requiert_clarification(settings, request_factory):
    llm = StubLLM(decision="HYPOTHESES_REQUIRE_CLARIFICATION",
                  clarification_questions=["Quel cadre théorique mobilisez-vous ?"])
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    out = result.output

    assert out.status.value == "needs_clarification"
    assert out.clarification_questions
    assert llm.calls == 2                        # P1 + P2 seulement
    assert result.verifier is None


def test_sans_objectifs_needs_clarification(settings, request_factory):
    req = request_factory(general_objective="", specific_objectives=[])
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "needs_clarification"


def test_aucun_auto_verified_avant_verificateur(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(verdict="rejected"),
                          allow_network=False)
    assert result.output.verification_result.verified is False
    assert result.output.status.value == "verification_failed"


def test_hypothese_a_presuppose_bloque_la_campagne(settings, request_factory):
    formulation = {"research_hypotheses": [
        {"id": "H1", "formulation": "Il est démontré que le télétravail réduit la productivité.",
         "justification": "j", "required_data": ["x"]}],
        "hypothesis_objective_alignment": {"general_to_objectives": "g"}}
    llm = StubLLM(decision="HYPOTHESES_RECOMMENDED", formulation=formulation)
    with pytest.raises(PipelineError) as exc:
        campaign.run(request_factory(), settings, llm, allow_network=False)
    assert exc.value.state.value == "OUTPUT_SCHEMA_ERROR"


def test_verificateur_demande_corrections_puis_accepte(settings, request_factory):
    class CorrectionLLM(StubLLM):
        def complete(self, system, user):
            if "Vérificateur" in system and self._verifier_seen == 0:
                self._verifier_seen += 1
                self.calls += 1
                import json
                return json.dumps({"agent": "hypotheses_verifier", "version": "1.0",
                                   "verdict": "corrections_requested",
                                   "controls": [], "corrections": ["Précise H1."], "flags": []})
            if "Vérificateur" in system:
                self._verifier_seen += 1
            return super().complete(system, user)

    llm = CorrectionLLM()
    llm._verifier_seen = 0
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    assert result.verifier_status == "verified"
    assert result.output.status.value == "awaiting_human_validation"
    assert result.reformulations >= 1


def test_upstream_non_verifie_rejete(settings, request_factory):
    from hypotheses_helpers import upstream_objectives

    req = request_factory(general_objective="", specific_objectives=[],
                          upstream_objectives=upstream_objectives(verified=False))
    with pytest.raises(PipelineError) as exc:
        campaign.run(req, settings, StubLLM(), allow_network=False)
    assert "vérifiée" in exc.value.detail
