"""Ancrage anti-hallucination et anti-fusion, testés au niveau du pipeline et de la validation."""

import pytest
from litterature_helpers import (
    DEFAULT_RESPONSES,
    FakeApiFetcher,
    FakeDownloader,
    SmartStubLLM,
    as_json,
    synthesis,
)

from literature_review_agent.core.errors import ErrorState, PipelineError
from literature_review_agent.pipeline import business_validation, campaign
from literature_review_agent.schemas.common import SubjectReference
from literature_review_agent.schemas.output import (
    Bibliography,
    Corpus,
    ReviewOutput,
    ReviewStatus,
)


class _SynthesisAvecFusion(SmartStubLLM):
    """Simule un modèle qui produit une problématique (interdit à cette étape)."""

    def complete(self, system: str, user: str) -> str:
        directive = system.lower()
        if "synthèse critique" in directive or "comparaison" in directive:
            self.calls += 1
            self.sent.append({"system": system, "user": user})
            payload = synthesis(self._doc_ids(user))
            payload["synthesis"]["state_of_knowledge"] = (
                "La problématique de ce mémoire porte sur l'organisation du travail.")
            return as_json(payload)
        return super().complete(system, user)


def test_citation_inventee_retiree(settings, request_factory):
    """Le modèle invente ses citations : elles sont retirées, jamais conservées."""
    result = campaign.run(request_factory(), settings, SmartStubLLM(with_fake_quote=True),
                          fetcher=FakeApiFetcher(DEFAULT_RESPONSES),
                          downloader=FakeDownloader())

    assert result.dropped_claims >= 1
    assert any("ancrage verbatim" in note for note in result.output.limits_of_this_review)
    for document in result.output.corpus.documents:
        assert document.findings == []


def test_validation_refuse_une_citation_non_ancree():
    """R5 : une affirmation dont la citation est introuvable est une violation bloquante."""
    from literature_review_agent.schemas.analysis import AnchoredClaim, ExtractionScope
    from literature_review_agent.schemas.output import Corpus
    from literature_review_agent.schemas.document import DocumentRecord

    document = DocumentRecord(
        doc_id="D1", authors=["Jane Doe"], title="Titre", year=2021,
        extraction_scope=ExtractionScope.abstract_only,
        findings=[AnchoredClaim(claim="Une hausse de 42 %",
                                quote="L'étude montre une hausse de 42 % de la productivité.")],
    )
    output = ReviewOutput(
        status=ReviewStatus.ready_for_verification,
        subject_reference=SubjectReference(original="Sujet"),
        corpus=Corpus(documents=[document], documents_count=1),
        bibliography=Bibliography(entries=[], entries_count=0),
    )
    from literature_review_agent.schemas.input import CampaignRequest

    request = CampaignRequest(student_id="etu-1", subject_text="Sujet", discipline="Gestion",
                              academic_level="Master 2")
    violations = business_validation.validate_semantics(
        output, request, {"D1": "Texte réel de l'étude, sans cette phrase."},
        {"D1": "Résumé réel de l'étude."})
    assert any("R5" in violation for violation in violations)


def test_scope_full_text_sans_lecture_est_ramene_a_resume(settings, request_factory):
    """R6 : le modèle ne peut pas annoncer « texte intégral » sans texte réellement lu."""
    class _ScopeSurestime(SmartStubLLM):
        def complete(self, system: str, user: str) -> str:
            raw = super().complete(system, user)
            if "noter et analyser un lot" in system.lower():
                import json

                payload = json.loads(raw)
                for document in payload["documents"]:
                    document["extraction_scope"] = "full_text"
                return json.dumps(payload, ensure_ascii=False)
            return raw

    result = campaign.run(request_factory(), settings, _ScopeSurestime(),
                          fetcher=FakeApiFetcher(DEFAULT_RESPONSES), downloader=FakeDownloader())

    assert result.output.status == ReviewStatus.ready_for_verification
    for document in result.output.corpus.documents:
        assert document.extraction_scope.value != "full_text"
    assert any("anti-surévaluation" in note for note in result.output.limits_of_this_review)


def test_fusion_interdite_bloque_la_campagne(settings, request_factory):
    with pytest.raises(PipelineError) as exc:
        campaign.run(request_factory(), settings, _SynthesisAvecFusion(),
                     fetcher=FakeApiFetcher(DEFAULT_RESPONSES), downloader=FakeDownloader())
    assert exc.value.state == ErrorState.OUTPUT_SCHEMA_ERROR
    assert "fusion interdite" in exc.value.detail


@pytest.mark.parametrize("marker", [
    "La problématique retenue est claire.",
    "La question de recherche principale est la suivante.",
    "Les hypothèses de recherche sont les suivantes.",
])
def test_marqueurs_interdits_detectes(marker):
    from literature_review_agent.schemas.output import Comparison, Synthesis, ThemeComparison

    output = ReviewOutput(
        status=ReviewStatus.ready_for_verification,
        subject_reference=SubjectReference(original="Sujet"),
        comparison=Comparison(themes=[ThemeComparison(theme="t", doc_ids=[])]),
        synthesis=Synthesis(state_of_knowledge=marker),
        bibliography=Bibliography(entries=[], entries_count=0),
    )
    from literature_review_agent.schemas.input import CampaignRequest

    request = CampaignRequest(student_id="etu-1", subject_text="Sujet", discipline="Gestion",
                              academic_level="Master 2")
    violations = business_validation.validate_semantics(output, request, {}, {})
    assert any("fusion interdite" in violation for violation in violations)


@pytest.mark.parametrize("text", [
    "La question reste problématique dans la littérature récente.",
    "La problématique de la mesure de la productivité n'est pas résolue par ces travaux.",
    "Cette étude éclaire la question de recherche sans y répondre.",
    "Les auteurs soulignent une situation problématique sur le terrain étudié.",
])
def test_usage_ordinaire_des_mots_metier_non_signale(text):
    """« problématique » et « question de recherche » sont des mots français ordinaires.

    Un test de sous-chaîne brut refusait la campagne entière sur une synthèse par ailleurs vérifiée
    (`R2: fusion interdite détectée (marqueur « problématique »)`). Seul un indice de PRODUCTION ou
    d'appropriation doit déclencher R2.
    """
    from literature_review_agent.pipeline.business_validation import fusion_markers

    assert fusion_markers(text) == []


@pytest.mark.parametrize("text", [
    "**Problématique** : l'organisation du travail à distance.",
    "Notre problématique porte sur l'organisation du travail.",
    "Nous formulons ici la question de recherche principale du mémoire.",
])
def test_production_effective_de_l_element_suivant_signalee(text):
    from literature_review_agent.pipeline.business_validation import fusion_markers

    assert fusion_markers(text)


def test_documents_count_incoherent_detecte():
    from literature_review_agent.schemas.input import CampaignRequest

    output = ReviewOutput(
        status=ReviewStatus.ready_for_verification,
        subject_reference=SubjectReference(original="Sujet"),
        corpus=Corpus(documents=[], documents_count=7),
        bibliography=Bibliography(entries=[], entries_count=0),
    )
    request = CampaignRequest(student_id="etu-1", subject_text="Sujet", discipline="Gestion",
                              academic_level="Master 2")
    violations = business_validation.validate_semantics(output, request, {}, {})
    assert any("documents_count" in violation for violation in violations)
