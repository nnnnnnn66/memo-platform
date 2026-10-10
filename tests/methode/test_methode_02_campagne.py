"""Campagne complète de l'Agent Méthodologie (LLM simulé, aucun réseau)."""

from methode_helpers import (
    DEFAULT_INSTRUMENTS,
    DEFAULT_PROTOCOL,
    DEFAULT_WRITING,
    StubLLM,
    upstream_diagnostic,
)

from methodology_agent.pipeline import campaign


def test_campagne_nominale(settings, request_factory):
    request = request_factory()
    result = campaign.run(request, settings, StubLLM(), allow_network=False)

    assert result.output.status.value == "awaiting_human_validation"
    assert result.verifier_status == "verified"
    assert result.output.verification_result.verified is True
    assert result.output.document_status.value == "en_attente_de_validation"
    # Le socle de l'étape 8 est REPRIS tel quel.
    assert result.output.protocol.approche == "quantitative"
    assert result.output.protocol.type_recherche == "explicative"
    # La matrice couvre les objectifs de l'étape 6.
    assert result.output.matrice.lignes
    assert all(ligne.statut.value == "couverte" for ligne in result.output.matrice.lignes)
    # Le document est rédigé et le protocole porte les instruments.
    assert result.output.draft.sections
    assert result.output.protocol.instruments
    assert result.output.evidence.llm_calls == 5


def test_la_matrice_couvre_chaque_objectif_meme_oublie(settings, request_factory):
    """Un objectif que le modèle oublie devient une ligne « non couverte », jamais disparu."""
    instruments = dict(DEFAULT_INSTRUMENTS)
    instruments["matrice"] = {"lignes": [DEFAULT_INSTRUMENTS["matrice"]["lignes"][0]]}
    request = request_factory()
    result = campaign.run(request, settings, StubLLM(instruments=instruments), allow_network=False)
    objectifs = [ligne.objectif for ligne in result.output.matrice.lignes]
    assert len(objectifs) >= 3
    statuts = {ligne.objectif: ligne.statut.value for ligne in result.output.matrice.lignes}
    assert "non_couverte" in statuts.values()


def test_socle_de_l_etape_8_non_retranche(settings, request_factory):
    """Les quatre choix du diagnostic sont repris dans le protocole."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    protocol = result.output.protocol
    assert protocol.approche and protocol.logique and protocol.type_recherche and protocol.strategie
    assert result.output.choix_methodologiques_retenus


def test_prerequis_diagnostic_absent(settings, request_factory):
    """Sans diagnostic de l'étape 8, l'agent demande la pièce au lieu d'inventer un socle."""
    request = request_factory(upstream_methodology_diagnostic=None)
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "needs_clarification"
    assert result.output.questions_for_human


def test_prerequis_diagnostic_provisoire(settings, request_factory):
    """Un diagnostic provisoire ne peut pas fonder un protocole définitif."""
    request = request_factory(
        upstream_methodology_diagnostic=upstream_diagnostic(status="provisoire"))
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert result.output.status.value == "needs_clarification"


def test_amont_non_verifie_refuse(settings, request_factory):
    from methodology_agent.core.errors import PipelineError
    request = request_factory(
        upstream_methodology_diagnostic=upstream_diagnostic(verified=False))
    try:
        campaign.run(request, settings, StubLLM(), allow_network=False)
    except PipelineError as exc:
        assert exc.state.value == "MISSING_INFORMATION"
    else:
        raise AssertionError("une sortie amont non vérifiée doit être refusée")


def test_hypotheses_non_pertinentes_ne_sont_pas_ajoutees(settings, request_factory):
    """L'étape 7 a conclu NOT_REQUIRED : le protocole ne doit pas introduire d'hypothèses."""
    protocol = {"protocol": dict(DEFAULT_PROTOCOL["protocol"]),
                "elements_a_confirmer": []}
    protocol["protocol"]["analyses"] = [
        {"nom": "statistiques descriptives", "objet": "décrire la relation", "conditions": [],
         "statut": "prevu"}]
    request = request_factory(upstream_hypotheses={
        "agent": "research_hypotheses_agent", "status": "validated",
        "hypotheses_decision": "HYPOTHESES_NOT_REQUIRED", "research_hypotheses": [],
        "verification_result": {"verified": True, "verifier_status": "verified"}})
    result = campaign.run(request, settings, StubLLM(protocol=protocol), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.hypotheses_examined == []


def test_un_o5_la_campagne_leve_si_non_conforme(settings, request_factory):
    """Une production qui re-tranche le socle (approche vide) est refusée, jamais transmise."""
    from methodology_agent.core.errors import PipelineError
    protocol = {"protocol": dict(DEFAULT_PROTOCOL["protocol"]), "elements_a_confirmer": []}
    protocol["protocol"]["approche"] = ""
    try:
        campaign.run(request_factory(), settings, StubLLM(protocol=protocol), allow_network=False)
    except PipelineError as exc:
        assert exc.state.value == "OUTPUT_SCHEMA_ERROR"
    else:
        raise AssertionError("un protocole sans socle doit lever")


def test_un_document_avec_reserves_declarees_se_presente_a_la_validation(settings,
                                                                        request_factory):
    """Des réserves DÉCLARÉES n'empêchent pas la validation humaine : c'est son rôle de les arbitrer.

    Défaut réel : une règle métier trop stricte refusait une sortie pourtant vérifiée dès qu'elle
    portait un manque déclaré — leçon F5/M4/R2/R7 (un contrôle mal calibré bloque une campagne saine).
    """
    from methode_helpers import DEFAULT_ANALYSIS, DEFAULT_PROTOCOL
    contradiction = ("le titre évoque des « effets » alors que la question parle d'association")
    analysis = dict(DEFAULT_ANALYSIS,
                    contradictions=[contradiction],
                    elements_manquants=["effectif accessible non connu"])
    protocol = {"protocol": dict(DEFAULT_PROTOCOL["protocol"]), "elements_a_confirmer": []}
    # La contradiction est REPRISE dans le protocole (jamais corrigée en silence, règle P9).
    protocol["protocol"]["contradictions_diagnostic"] = [contradiction]
    result = campaign.run(request_factory(), settings,
                          StubLLM(analysis=analysis, protocol=protocol), allow_network=False)
    assert result.output.status.value == "awaiting_human_validation"
    assert result.output.verification_result.verified is True
    assert result.output.contradictions
    assert result.output.missing_information


def test_valide_sans_verification_refuse(settings, request_factory):
    from methodology_agent.pipeline import business_validation
    from methodology_agent.schemas.output import DocumentStatus
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    result.output.document_status = DocumentStatus.valide
    result.output.verification_result.verified = False
    violations = business_validation.validate_semantics(result.output, request_factory())
    assert any(v.startswith("R2") for v in violations)


def test_ecriture_reprise_dans_la_sortie(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    titres = [s.titre for s in result.output.draft.sections]
    assert "Approche et type de recherche" in titres
    assert result.output.draft.sections[0].statut.value == "prevu"
