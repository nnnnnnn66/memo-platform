"""Campagne complète : pré-cadrage, production sourcée, vérificateur indépendant."""

import pytest
from problematique_helpers import (CROSSREF_OK, OPENALEX_OK, FakeFetcher, StubLLM,
                                   literature_payload)

from problematization_agent.core.errors import ErrorState, PipelineError
from problematization_agent.pipeline import campaign
from problematization_agent.schemas.output import ProblemStatus

OPENALEX_ENDPOINT = "https://api.openalex.org/works"
CROSSREF_ENDPOINT = "https://api.crossref.org/works"


def test_campagne_complete_verifiee(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)

    assert result.output.status == ProblemStatus.ready_for_verification
    assert result.verifier_status == "verified"
    assert result.output.validation.verified is True
    assert result.output.validation.verifier_status == "verified"
    assert result.output.gap.type.value == "contextuelle"
    assert result.output.gap.gap_check.result.value == "unavailable"
    # Toutes les affirmations conservées sont ancrées dans le texte réel
    assert result.output.evidence.statements_anchored == result.output.evidence.statements_written
    assert result.output.evidence.statements_removed == 0
    # La question et les objectifs restent des propositions de transition
    assert result.output.research_question.status.value == "proposed"
    assert result.output.objectives.status.value == "proposed"


def test_amorce_alignement_coherente_avec_l_amont(settings, request_factory):
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    alignment = result.output.methodological_alignment
    assert alignment.matrix_row_id == "verify_theory"
    assert alignment.logic.value == "deductive"
    assert alignment.approach == "quantitative"
    assert alignment.upstream_coherence.value == "consistent"


def test_amorce_alignement_divergente_declaree(settings, request_factory):
    literature = literature_payload(diagnosis=False)
    literature["diagnosis"] = {"matrix_row_id": "explore_phenomenon", "reasoning_logic": "inductive",
                               "research_type": "exploratory", "approach": "qualitative",
                               "techniques": ["entretiens"]}
    result = campaign.run(request_factory(upstream_literature=literature), settings, StubLLM(),
                          allow_network=False)
    alignment = result.output.methodological_alignment
    assert alignment.upstream_coherence.value == "divergent"
    assert alignment.coherence_note
    assert any("divergente" in note for note in result.output.limits_of_this_note)


def test_revue_non_verifiee_refusee(settings, request_factory):
    request = request_factory(upstream_literature=literature_payload(verified=False))
    with pytest.raises(PipelineError) as exc:
        campaign.run(request, settings, StubLLM(), allow_network=False)
    assert exc.value.state == ErrorState.MISSING_INFORMATION


def test_sans_revue_demande_clarification(settings, request_factory):
    request = request_factory(upstream_literature=None)
    result = campaign.run(request, settings, StubLLM(), allow_network=False)
    assert result.output.status == ProblemStatus.needs_clarification
    assert result.output.clarification_questions
    assert any("revue de littérature" in q for q in result.output.clarification_questions)


def test_revue_vide_demande_clarification(settings, request_factory):
    result = campaign.run(request_factory(upstream_literature=literature_payload(documents=[])),
                          settings, StubLLM(), allow_network=False)
    assert result.output.status == ProblemStatus.needs_clarification


def test_le_probleme_amont_suffit_sans_champ_plat(settings, request_factory):
    """DÉFAUT RÉEL du premier parcours de bout en bout.

    L'orchestrateur fournit le problème par la sortie VÉRIFIÉE de l'étape 2 (`upstream_problem`), et
    NON par un champ plat `research_problem`. Le pré-contrôle exigeant le champ plat, l'agent
    s'arrêtait AVANT tout appel au modèle : réponse en 0 seconde, tous les champs vides, et le
    parcours ne pouvait pas dépasser l'étape 4.

    Ce qui l'a rendu invisible en test : la fabrique de requêtes renseignait TOUJOURS
    `research_problem` et `field_observations` — ce qu'un vrai parcours ne fait jamais.
    """
    request = request_factory(
        research_problem="",
        field_observations="",
        upstream_problem={"agent": "research_problem_agent", "version": "1.0",
                          "status": "awaiting_human_validation",
                          # Une sortie amont n'est utilisable que si son propre vérificateur l'a
                          # validée : c'est la règle que le contrôle d'entrée applique.
                          "validation": {"verified": True, "verifier_status": "verified"},
                          "identified_problem": {"statement": "Les promoteurs immobiliers "
                                                "artificialisent les sols de Bingerville."}})

    result = campaign.run(request, settings, StubLLM(), allow_network=False)

    assert result.output.status != ProblemStatus.needs_clarification
    questions = result.output.clarification_questions or []
    assert not any("problème concret" in question for question in questions), questions


def test_corpus_sans_texte_bloque(settings, request_factory):
    documents = [{"doc_id": "D1", "title": "sans texte ni résumé", "abstract": "",
                  "findings": [], "limits": []}]
    result = campaign.run(request_factory(upstream_literature=literature_payload(documents=documents)),
                          settings, StubLLM(), allow_network=False)
    assert result.output.status == ProblemStatus.blocked
    assert result.output.unknowns


def test_corrections_du_verificateur_relance_la_production(settings, request_factory):
    """Le vérificateur demande une correction une fois, puis valide."""
    stub = StubLLM(corrections_once=True)
    result = campaign.run(request_factory(), settings, stub, allow_network=False)
    assert result.verifications >= 1
    assert result.verifier_status in {"verified", "corrections_requested"}
    # La seconde production a bien été demandée
    assert stub.calls >= 6


def test_bibliographie_triee_sans_prefixe(settings, request_factory):
    """APA 7 : liste alphabétique, jamais de préfixe « [Dx] » dans les références."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    entries = result.output.bibliography.entries
    assert entries
    assert all(not entry.startswith("[") for entry in entries)
    assert entries == sorted(entries, key=campaign._alpha_key)


def test_periode_reprise_du_sujet_et_confiance_justifiee(settings, request_factory):
    """La période explicitement écrite dans le sujet est reprise, et la confiance est motivée."""
    result = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert result.output.scope.period == "2020-2024"
    assert result.output.confidence.rationale
    assert 0.0 <= result.output.confidence.overall <= 1.0


def test_reformulation_amont_reprise_jamais_inventee(settings, request_factory):
    upstream = {
        "agent": "subject_agent",
        "subject": {"original": "sujet initial", "reformulated": "Télétravail et productivité"},
        "validation": {"verified": True, "verifier_status": "verified"},
    }
    avec = campaign.run(request_factory(upstream_subject=upstream), settings, StubLLM(),
                        allow_network=False)
    assert avec.output.subject_reference.reformulated == "Télétravail et productivité"

    # Sans amont, aucune reformulation n'est inventée.
    sans = campaign.run(request_factory(), settings, StubLLM(), allow_network=False)
    assert sans.output.subject_reference.reformulated == ""


def test_echec_partiel_du_gap_check_est_declare(settings, request_factory):
    """Un fournisseur en échec ne doit pas se transformer en « absence prouvée »."""
    fetcher = FakeFetcher({CROSSREF_ENDPOINT: CROSSREF_OK}, raise_for={OPENALEX_ENDPOINT})
    result = campaign.run(request_factory(), settings, StubLLM(), fetcher=fetcher)

    check = result.output.gap.gap_check
    assert check.providers_failed, "l'échec du fournisseur doit être conservé"
    assert any("n'a pas abouti" in note for note in result.output.limits_of_this_note)
    assert any("pas prouvée" in unknown for unknown in result.output.unknowns)
