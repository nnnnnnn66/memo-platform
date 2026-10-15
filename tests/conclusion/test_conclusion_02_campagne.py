"""Campagne complète de l'Agent Conclusion (LLM simulé, aucun réseau)."""

from conclusion_helpers import DEFAULT_PLAN, DEFAULT_SYNTHESIS, StubLLM, upstream_results

from research_conclusion_agent.pipeline import campaign


def test_campagne_nominale(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)

    assert result.output.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert result.output.document_status.value == "en_attente_de_validation"
    assert result.output.synthesis.reponse_question.reponse
    assert result.output.synthesis.resultats_essentiels == ["R1", "R2"]
    assert result.output.draft.sections
    assert result.output.references_resultats
    assert result.output.evidence.llm_calls == 4


def test_la_conclusion_ne_produit_aucun_resultat_nouveau(settings, request_factory):
    """Toute affirmation chiffrée renvoie à un calcul de l'étape 10 (traçabilité)."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    ids = request_factory().computed_ids()
    for section in result.output.draft.sections:
        for reference in section.resultats:
            assert reference in ids


def test_sans_resultats_plan_seulement(settings, request_factory):
    """Chemin STOP de la SPEC : sans résultats vérifiés, aucune conclusion n'est rédigée."""
    request = request_factory(upstream_results=upstream_results(plan_seulement=True))
    synthesis = dict(DEFAULT_SYNTHESIS, plan_seulement=True, resultats_essentiels=[],
                     bilan_objectifs=[], bilan_hypotheses=[],
                     elements_manquants=["résultats vérifiés de l'étape 10"],
                     reponse_question={"question": "Dans quelle mesure… ?", "reponse": "",
                                       "etayage": [], "portee": ""})
    result = campaign.run(request, settings, StubLLM(synthesis=synthesis), allow_network=False)
    assert result.output.synthesis.plan_seulement is True
    assert result.output.draft.sections == []
    assert result.output.document_status.value == "brouillon"
    assert result.output.limits_of_this_output


def test_hypothese_non_examinable_conservee(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    statuts = {b.hypothese: b.statut.value for b in result.output.synthesis.bilan_hypotheses}
    assert "non_examinable" in statuts.values()


def test_prerequis_resultats_absents(settings, request_factory):
    """Des résultats ABSENTS ne bloquent plus : la production devient un PLAN déclaré.

    Le test décrivait l'ancien comportement — renvoyer l'étudiante à sa copie. Défaut réel constaté
    en simulation complète : un dossier mené jusqu'au bout restait bloqué à la DERNIÈRE étape sur
    « le statut des résultats est brouillon », alors que les résultats de terrain n'existent pas
    encore et que l'étudiante ne peut donc rien « transmettre ». Consigne du porteur, PRIORITAIRE :
    un agent LIVRE ; il ne pose pas de question. On vérifie donc qu'un plan est produit, DÉCLARÉ
    comme plan (jamais une conclusion inventée), et qu'aucune question n'est rendue à l'étudiante.
    """
    result = campaign.run(request_factory(upstream_results=None), settings, StubLLM(),
                          allow_network=False)
    assert result.output.status.value != "needs_clarification"
    assert not result.output.questions_for_human
    assert result.output.synthesis.plan_seulement is True
    assert any("résultat" in note for note in result.output.limits_of_this_output)


def test_resultats_non_verifies_refuses(settings, request_factory):
    from research_conclusion_agent.core.errors import PipelineError
    try:
        campaign.run(request_factory(upstream_results=upstream_results(verified=False)), settings,
                     StubLLM(), allow_network=False)
    except PipelineError as exc:
        assert exc.state.value == "MISSING_INFORMATION"
    else:
        raise AssertionError("des résultats non vérifiés doivent être refusés")


def test_un_chiffre_invente_fait_echouer_la_campagne(settings, request_factory):
    from research_conclusion_agent.core.errors import PipelineError
    draft = {"sections": [{"titre": "Synthèse",
                           "contenu": "La moyenne atteint 9,4 sur l'échelle.",
                           "fonction": "résumer", "niveau": "constat",
                           "justification": "calculs", "resultats": ["R1"]}],
             "apports_scientifiques": [], "apports_pratiques": [], "limites": [],
             "perspectives": [], "points_a_confirmer": []}
    try:
        campaign.run(request_factory(), settings, StubLLM(draft=draft), allow_network=False)
    except PipelineError as exc:
        assert exc.state.value == "OUTPUT_SCHEMA_ERROR"
    else:
        raise AssertionError("un chiffre non calculé doit être refusé")


def test_bilan_objectifs_present(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert result.output.synthesis.bilan_objectifs
    assert result.output.coherence_controls
