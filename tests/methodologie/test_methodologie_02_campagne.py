"""Campagne complète (LLM simulé) : statuts, diagnostic provisoire, vérificateur."""

import pytest

from methodology_diagnostic_agent.core.errors import PipelineError
from methodology_diagnostic_agent.pipeline import campaign
from methodologie_helpers import DEFAULT_DIAGNOSIS, StubLLM


def test_campagne_nominale(settings, request_factory):
    llm = StubLLM(verdict="verified")
    result = campaign.run(request_factory(), settings, llm, allow_network=False)
    out = result.output

    assert out.status.value == "awaiting_human_validation"
    assert out.diagnostic_status.value == "en_attente_de_validation"
    assert result.verifier_status == "verified"
    assert out.diagnosis.approche.code == "quantitative"
    assert out.diagnosis.strategie.code == "enquete"
    assert out.evidence.llm_calls == 3          # P1 + P2 + vérificateur
    assert out.resume
    assert out.coherence_controls
    assert 0.0 <= out.confidence.overall <= 1.0


def test_diagnostic_provisoire_si_donnees_manquantes(settings, request_factory):
    req = request_factory(available_data="", field_access="", available_resources="")
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    out = result.output
    assert out.provisional is True
    assert out.missing_information
    assert out.diagnostic_status.value == "en_attente_de_validation"


def test_diagnostic_non_provisoire_si_tout_fourni(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert result.output.provisional is False
    assert result.output.missing_information == []


def test_inconnues_declarees_transmises_et_rendent_provisoire(settings, request_factory):
    """Des inconnues déclarées doivent être CONSERVÉES et rendre le diagnostic provisoire.

    Relevé par le vérificateur en campagne réelle : `unknowns` et `missing_information` vides
    alors que l'effectif, les instruments de mesure et l'accès aux documents restaient inconnus,
    et `provisional = false` en contradiction avec un résumé qui annonçait un « diagnostic
    provisoire ». Le champ `unknowns` existait dans le schéma mais rien ne le remplissait.
    """
    inconnues = ["effectif joignable dans les deux entreprises inconnu",
                 "aucun indicateur RH objectif de productivité disponible"]
    diagnosis = {**DEFAULT_DIAGNOSIS, "unknowns": inconnues}
    result = campaign.run(request_factory(), settings,
                          StubLLM(diagnosis=diagnosis), allow_network=False)
    out = result.output
    assert out.unknowns == inconnues           # transmises telles quelles depuis le modèle
    assert out.provisional is True             # des inconnues ⇒ diagnostic provisoire
    # Les deux listes restent DISTINCTES, comme chez les agents 6 et 7 : `unknowns` porte la
    # déclaration du modèle, `missing_information` les manques bloquants déduits du dossier.
    # Les fusionner faisait chuter la confiance à 0.1 (pénalité par élément) et déplaçait le
    # signalement du vérificateur sans le résoudre.
    assert out.missing_information == []
    assert "provisoire" in out.confidence.rationale


def test_aucune_inconnue_declaree_reste_appuye(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert result.output.unknowns == []
    assert result.output.provisional is False


def test_alternatives_overview_recapitule_les_alternatives_existantes(settings, request_factory):
    """Le récapitulatif des alternatives agrège ce qui existe — il ne le fabrique pas.

    Champ du schéma resté vide alors que chaque catégorie portait ses alternatives : relevé par
    le vérificateur en campagne réelle.
    """
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    lignes = result.output.alternatives_overview
    assert lignes                                     # non vide
    assert any("approche" in ligne for ligne in lignes)
    assert any("approche mixte" in ligne for ligne in lignes)   # reprise littérale de l'alternative
    # Aucune catégorie sans alternative n'est inventée.
    assert all("alternative(s) " in ligne for ligne in lignes)


def test_rationale_de_confiance_annonce_les_inconnues(settings, request_factory):
    """La rationale ne peut pas dire « 0 information manquante » si des inconnues sont déclarées."""
    diagnosis = {**DEFAULT_DIAGNOSIS, "unknowns": ["effectif joignable inconnu"]}
    result = campaign.run(request_factory(), settings,
                          StubLLM(diagnosis=diagnosis), allow_network=False)
    assert "1 inconnue(s) déclarée(s)" in result.output.confidence.rationale


def test_rationale_de_confiance_enonce_le_calcul(settings, request_factory):
    """Un `overall` nu est signalé par le vérificateur : la rationale doit énoncer le calcul."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    rationale = result.output.confidence.rationale
    assert "calcul :" in rationale
    assert "base 0.50" in rationale
    assert f"= {result.output.confidence.overall:.2f}" in rationale


def test_sans_question_needs_clarification(settings, request_factory):
    req = request_factory(main_research_question="")
    result = campaign.run(req, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "needs_clarification"
    assert result.output.clarification_questions
    assert result.output.diagnostic_status.value == "provisoire"


def test_aucun_auto_verified_avant_verificateur(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(verdict="rejected"),
                          allow_network=False)
    assert result.output.verification_result.verified is False
    assert result.output.status.value == "verification_failed"
    assert result.output.diagnostic_status.value == "a_reviser"


def test_causalite_non_justifiee_bloque_la_campagne(settings, request_factory):
    diagnosis = {"resume": "r", "diagnosis": {
        "approche": {"code": "quantitative", "proposition": "Approche quantitative",
                     "justification": "j", "conditions": []},
        "logique": {"code": "hypothetico_deductive", "proposition": "Démarche déductive",
                    "justification": "j"},
        "type_recherche": {"code": "explicative", "proposition": "Recherche explicative",
                           "justification": "j"},
        "strategie": {"code": "enquete", "proposition": "Enquête", "justification": "j",
                      "conditions": ["accès"]},
        "collecte": [{"proposition": "Questionnaire", "justification": "j"}],
        "analyse": [{"proposition": "Analyse statistique", "justification": "j"}],
        "articulation": "Le dispositif démontre une causalité.",
        "coherence_question": "c"},
        "feasibility_controls": [], "limits_of_this_output": [], "questions_for_human": []}
    llm = StubLLM(diagnosis=diagnosis)
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
                return json.dumps({"agent": "methodology_verifier", "version": "1.0",
                                   "verdict": "corrections_requested",
                                   "controls": [], "corrections": ["Justifie la stratégie."],
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
    from methodologie_helpers import upstream_hypotheses

    req = request_factory(main_research_question="",
                          upstream_hypotheses=upstream_hypotheses(verified=False))
    with pytest.raises(PipelineError) as exc:
        campaign.run(req, settings, StubLLM(), allow_network=False)
    assert "vérifiée" in exc.value.detail
