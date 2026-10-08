"""Campagne complète (LLM simulé) : statuts, vérificateur, honnêteté."""

import pytest

from research_question_agent.core.errors import PipelineError
from research_question_agent.pipeline import campaign
from question_helpers import StubLLM, problematique_note


def test_campagne_nominale(settings, request_factory):
    llm = StubLLM(verdict="verified")
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    out = result.output

    assert out.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert out.verification_result.verified is True
    assert out.research_intention.intention == "expliquer"
    assert out.main_research_question.startswith("Dans quelle mesure")
    assert out.evidence.llm_calls == 4
    # Confiance dérivée des preuves, avec rationale non vide.
    assert 0.0 <= out.confidence.overall <= 1.0
    assert out.confidence.rationale


def test_sans_problematique_needs_clarification(settings, request_factory):
    req = request_factory(validated_problematic="")
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "needs_clarification"
    assert result.output.clarification_questions


def test_aucun_auto_verified_avant_verificateur(settings, request_factory):
    # Le statut de validation n'est jamais posé par l'agent lui-même.
    result = campaign.run(request_factory(), settings, StubLLM(verdict="rejected"),
                          allow_network=False)
    assert result.output.verification_result.verified is False
    assert result.output.status.value == "verification_failed"


def test_verificateur_demande_corrections_puis_accepte(settings, request_factory):
    class CorrectionLLM(StubLLM):
        def complete(self, system, user):
            if "Vérificateur" in system and self._verifier_seen == 0:
                self._verifier_seen += 1
                self.calls += 1
                import json
                return json.dumps({"agent": "question_verifier", "version": "1.0",
                                   "verdict": "corrections_requested",
                                   "controls": [], "corrections": ["Reformule la question."],
                                   "flags": []})
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
    from question_helpers import upstream_problematic
    req = request_factory(upstream_problematic=upstream_problematic(verified=False),
                          validated_problematic="")
    with pytest.raises(PipelineError) as exc:
        campaign.run(req, settings, StubLLM(), allow_network=False)
    assert "vérifiée" in exc.value.detail
