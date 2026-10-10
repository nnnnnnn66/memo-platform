"""Campagne complète de l'Agent Résultats et analyse (LLM simulé, aucun réseau)."""

from resultats_helpers import DEFAULT_INVENTORY, DEFAULT_PLAN, StubLLM

from research_results_analysis_agent.pipeline import campaign


def test_campagne_nominale_avec_donnees(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)

    assert result.output.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert result.output.document_status.value == "en_attente_de_validation"
    # Les chiffres viennent du MOTEUR, pas du modèle.
    assert result.output.computed_results.resultats
    assert all(r.id.startswith("R") for r in result.output.computed_results.resultats)
    assert result.output.evidence.calculs == len(result.output.computed_results.resultats)
    assert result.output.evidence.llm_calls == 5
    assert result.output.draft.sections
    assert result.output.synthese_pour_conclusion


def test_moteur_calcule_avant_le_modele(settings, request_factory):
    """Les valeurs publiées existent réellement dans les calculs (anti-invention structurelle)."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    valeurs = result.output.computed_results.valeurs()
    assert "6" in valeurs                     # effectif total
    assert any(v.startswith("6,1") for v in valeurs)


def test_sans_donnees_plan_seulement_jamais_de_resultats(settings, request_factory):
    """Chemin STOP de la SPEC : aucune donnée ⇒ plan d'analyse, jamais de résultats inventés."""
    request = request_factory(datasets=[])
    plan = dict(DEFAULT_PLAN, resultats=[], plan_seulement=True,
                objectifs_couverts=[],
                objectifs_non_couverts=["Analyser la relation entre le télétravail et la "
                                        "productivité."],
                analyses_non_realisees=["aucune donnée fournie"],
                hypotheses=[])
    draft = {"sections": [], "synthese_pour_conclusion": [],
             "elements_a_confirmer": ["recueillir les données de terrain"]}
    result = campaign.run(request, settings,
                          StubLLM(plan=plan, draft=draft), allow_network=False)
    assert result.output.computed_results.resultats == []
    assert result.output.plan.plan_seulement is True
    assert result.output.document_status.value == "brouillon"
    assert result.output.questions_for_human


def test_hypothese_non_pertinente_n_est_pas_examinee(settings, request_factory):
    request = request_factory(upstream_hypotheses={
        "agent": "research_hypotheses_agent", "status": "validated",
        "hypotheses_decision": "HYPOTHESES_NOT_REQUIRED", "research_hypotheses": [],
        "verification_result": {"verified": True, "verifier_status": "verified"}})
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"


def test_prerequis_methodologie_absente(settings, request_factory):
    result = campaign.run(request_factory(upstream_methodology=None), settings, StubLLM(),
                          allow_network=False)
    assert result.output.status.value == "needs_clarification"
    assert result.output.questions_for_human


def test_methodologie_non_verifiee_refusee(settings, request_factory):
    from research_results_analysis_agent.core.errors import PipelineError
    from resultats_helpers import upstream_methodology
    request = request_factory(upstream_methodology=upstream_methodology(verified=False))
    try:
        campaign.run(request, settings, StubLLM(), allow_network=False)
    except PipelineError as exc:
        assert exc.state.value == "MISSING_INFORMATION"
    else:
        raise AssertionError("une méthodologie non vérifiée doit être refusée")


def test_un_chiffre_invente_fait_echouer_la_campagne(settings, request_factory):
    """Anti-invention : un résultat non calculé empêche la production d'être transmise."""
    from research_results_analysis_agent.core.errors import PipelineError
    plan = dict(DEFAULT_PLAN)
    plan["resultats"] = [{"id_resultat": "R99",
                          "observation": "La moyenne atteint 9,4 sur l'échelle.",
                          "objectif": "Décrire", "limites": []}]
    try:
        campaign.run(request_factory(), settings, StubLLM(plan=plan), allow_network=False)
    except PipelineError as exc:
        assert exc.state.value == "OUTPUT_SCHEMA_ERROR"
    else:
        raise AssertionError("un chiffre non calculé doit être refusé")


def test_anomalies_et_manquants_declares_dans_la_sortie(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert result.output.inventory.manquants
    assert result.output.anomalies_et_manquants
    assert any("manquante" in c for c in result.output.coherence_controls
               + result.output.inventory.manquants)
