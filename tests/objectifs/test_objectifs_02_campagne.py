"""Campagne complète (LLM simulé) : statuts, vérificateur, honnêteté."""

import pytest

from research_objectives_agent.core.errors import PipelineError
from research_objectives_agent.pipeline import campaign
from objectifs_helpers import StubLLM


def test_campagne_nominale(settings, request_factory):
    llm = StubLLM(verdict="verified")
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    out = result.output

    assert out.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert out.verification_result.verified is True
    assert out.general_objective.startswith("Analyser")
    assert len(out.specific_objectives) == 3
    assert out.evidence.llm_calls == 4          # P1 + P2 + P3 + vérificateur
    assert 0.0 <= out.confidence.overall <= 1.0
    assert out.confidence.rationale


def test_sans_question_needs_clarification(settings, request_factory):
    req = request_factory(main_research_question="")
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "needs_clarification"
    assert result.output.clarification_questions


def test_aucun_auto_verified_avant_verificateur(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(verdict="rejected"),
                          allow_network=False)
    assert result.output.verification_result.verified is False
    assert result.output.status.value == "verification_failed"


def test_objectif_a_presuppose_bloque_la_campagne(settings, request_factory):
    # Le modèle produit un objectif général à présupposé : les contrôles codés refusent la sortie.
    llm = StubLLM(general="Démontrer que le télétravail réduit la productivité.")
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
                return json.dumps({"agent": "objectives_verifier", "version": "1.0",
                                   "verdict": "corrections_requested",
                                   "controls": [], "corrections": ["Précise l'objectif général."],
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
    from objectifs_helpers import upstream_question

    req = request_factory(main_research_question="", upstream_question=upstream_question(verified=False))
    with pytest.raises(PipelineError) as exc:
        campaign.run(req, settings, StubLLM(), allow_network=False)
    assert "vérifiée" in exc.value.detail
