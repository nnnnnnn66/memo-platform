"""Test 9 — Robustesse du vérificateur de la revue de littérature.

Régression constatée en exécution réelle : le modèle est un RAISONNEUR, il partage `max_tokens`
avec ses tokens de raisonnement. Une vérification longue était donc tronquée en plein JSON, ce
qui faisait échouer TOUTE la campagne (le vérificateur n'avait aucune re-tentative).
"""

from types import SimpleNamespace

import pytest

from literature_review_agent.core.errors import ErrorState, PipelineError
from literature_review_agent.pipeline import verifier
from literature_review_agent.schemas.input import CampaignRequest

VERDICT = ('{"agent": "literature_review_verifier", "version": "1.0", "verdict": "verified", '
           '"controls": [{"code": "L1", "resultat": "ok", "detail": ""}], '
           '"corrections": [], "flags": []}')

# Réponse coupée en plein JSON (ne se termine pas par « } »).
TRONQUE = ('{"agent": "literature_review_verifier", "version": "1.0", "verdict": "verified", '
           '"controls": [{"code": "L1", "resultat": "ok", "detail": "ok"}, {"code": "L2",')


class _Stub:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.sent = []

    def complete(self, system, user):
        self.calls += 1
        self.sent.append(user)
        return self.responses.pop(0)


def _call(llm):
    request = CampaignRequest(student_id="s9", subject_text="Télétravail et productivité")
    output = SimpleNamespace(model_dump_json=lambda indent=2: '{"status": "ready_for_verification"}')
    corpus = SimpleNamespace(records=[])
    return verifier.verify(llm, request, output, corpus)


def test_verificateur_reessaye_apres_une_sortie_tronquee():
    llm = _Stub([TRONQUE, VERDICT])

    verdict = _call(llm)

    assert verdict.verdict.value == "verified"
    assert llm.calls == 2
    # La re-tentative doit porter la consigne de concision dans le message.
    assert "CONCIS" in llm.sent[1]


def test_verificateur_echoue_proprement_apres_toutes_les_tentatives():
    llm = _Stub([TRONQUE, TRONQUE, TRONQUE])

    with pytest.raises(PipelineError) as exc:
        _call(llm)

    assert exc.value.state == ErrorState.VERIFICATION_FAILED
    assert llm.calls == 3
