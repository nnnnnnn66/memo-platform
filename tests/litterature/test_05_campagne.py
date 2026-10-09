"""Campagne complète hors réseau : recherche simulée, texte non téléchargeable, verdict vérifié."""

from litterature_helpers import (
    DEFAULT_RESPONSES,
    FakeApiFetcher,
    FakeDownloader,
    SmartStubLLM,
)

from literature_review_agent.core.config import Settings
from literature_review_agent.pipeline import campaign
from literature_review_agent.schemas.output import CorpusSufficiency, ReviewStatus


def _run(settings, request, llm=None, downloader=None, fetcher=None):
    llm = llm or SmartStubLLM()
    return campaign.run(
        request, settings, llm,
        registry=None,
        fetcher=fetcher or FakeApiFetcher(DEFAULT_RESPONSES),
        downloader=downloader or FakeDownloader(),
    )


def test_campagne_complete_aboutit(settings, request_factory):
    request = request_factory()
    result = _run(settings, request)

    assert result.output.status == ReviewStatus.ready_for_verification
    assert result.output.validation.verified is True
    assert result.verifier_status == "verified"
    assert result.output.corpus.documents_count >= 2
    assert result.output.corpus.documents_count == len(result.output.corpus.documents)
    assert result.output.bibliography.entries_count == len(result.output.corpus.documents)
    assert result.output.diagnosis.matrix_row_id == "test_hypothesis"
    assert result.output.diagnosis.status.value == "proposal_to_validate_with_student"
    assert result.stages["retrieval"]["documents_collected"] >= 2


def test_derniere_reformulation_est_jugee(settings, request_factory):
    """La dernière reformulation demandée par le vérificateur doit être JUGÉE.

    Bug réel (trouvé au test de chaîne) : la boucle s'arrêtait sur `verification_failed` après la
    dernière re-tentative, sans jamais rejouer le vérificateur sur la version corrigée — celle-ci
    pouvait parfaitement passer (vérifié en rejouant le vérificateur seul : verdict `verified`).
    """
    import dataclasses

    from litterature_helpers import VERIFIER_VERIFIED

    def corr(code: str) -> dict:
        return {"agent": "literature_review_verifier", "version": "1.0",
                "verdict": "corrections_requested",
                "controls": [{"code": code, "resultat": "echec", "detail": ""}],
                "corrections": [f"{code}: corriger ce point"], "flags": []}

    settings.limits = dataclasses.replace(settings.limits, max_llm_calls=40)
    llm = SmartStubLLM(verifier=[corr("L9"), corr("L8"), corr("L7"), VERIFIER_VERIFIED])
    result = _run(settings, request_factory(), llm=llm)

    # 4 appels : 3 verdicts de correction (les re-tentatives) puis 1 verdict FINAL, qui juge la
    # dernière reformulation. Sans le correctif, il n'y en avait que 3 et la campagne échouait.
    assert llm.verifier_calls == 4
    assert result.verifier_status == "verified"
    assert result.output.validation.verified is True


def test_sources_citees_existent_dans_le_corpus(settings, request_factory):
    result = _run(settings, request_factory())
    known = set(result.output.documents_by_id())
    for theme in result.output.comparison.themes:
        assert set(theme.doc_ids) <= known


def test_citations_ancrees_sur_les_resumes(settings, request_factory):
    result = _run(settings, request_factory())
    anchored = 0
    for document in result.output.corpus.documents:
        for claim in list(document.findings) + list(document.limits):
            assert claim.quote
            assert len(claim.quote) >= 25
            assert document.extraction_scope.value in ("abstract_only", "full_text")
            anchored += 1
    assert anchored >= 1, "le corpus simulé doit produire au moins une citation ancrée"


def test_aucun_telechargement_possible_est_declare(settings, request_factory):
    """Tous les téléchargements échouent : la revue le déclare au lieu de masquer la limite."""
    downloader = FakeDownloader()          # aucune URL ne répond
    result = _run(settings, request_factory(), downloader=downloader)

    assert result.downloaded_count == 0
    assert result.output.corpus.full_text_downloaded == 0
    assert downloader.attempted, "des tentatives de téléchargement doivent avoir lieu"
    assert any("sans texte intégral" in note for note in result.output.limits_of_this_review)
    # Deux cas distincts et déclarés séparément : un lien d'accès ouvert existe mais le
    # téléchargement échoue (available=True + download_error), ou aucun lien n'existe
    # (available=False). Dans les deux cas downloaded reste faux : aucune lecture n'est simulée.
    for document in result.output.corpus.documents:
        assert document.full_text.downloaded is False
        if document.full_text.available:
            assert document.full_text.download_error
    assert any(d.full_text.available for d in result.output.corpus.documents)
    assert any(d.full_text.download_error for d in result.output.corpus.documents)


def test_pdf_present_mais_non_lisible_est_declare(settings, request_factory):
    """Un fichier reçu qui n'est pas un PDF exploitable ne doit pas faire croire à une lecture."""
    downloader = FakeDownloader(default=b"%PDF-1.4 fichier tronque sans structure")
    result = _run(settings, request_factory(), downloader=downloader)

    assert result.downloaded_count == 0
    for document in result.output.corpus.documents:
        assert document.full_text.downloaded is False


def test_suffisance_du_corpus_declaree(settings, request_factory):
    result = _run(settings, request_factory())
    assert result.output.corpus.corpus_sufficiency in (
        CorpusSufficiency.sufficient, CorpusSufficiency.partial)
    assert result.stages["selection"]["retained"] == result.output.corpus.documents_count


def test_corpus_vide_est_blocked(settings, request_factory):
    """Aucun fournisseur ne répond : statut blocked, explication, aucune invention."""
    fetcher = FakeApiFetcher({"api.openalex.org/works": {"results": []},
                              "api.crossref.org/works": {"message": {"items": []}},
                              "api.archives-ouvertes.fr": {"response": {"docs": []}},
                              "theses.fr": {"theses": []},
                              "ebi.ac.uk": {"resultList": {"result": []}},
                              "doaj.org": {"results": []}})
    result = _run(settings, request_factory(), fetcher=fetcher)

    assert result.output.status == ReviewStatus.blocked
    assert result.output.unknowns or result.output.limits_of_this_review
    assert result.output.corpus.documents == []
    assert result.verifier is None


def test_identifiants_stables_jusqu_a_la_sortie(settings, request_factory):
    """Régression : les doc_id de la sortie doivent correspondre aux documents réellement traités.

    Un renommage tardif cassait la correspondance entre la sortie, les textes téléchargés et les
    affirmations ancrées (R6 signalait alors un texte intégral absent).
    """
    result = _run(settings, request_factory())
    for document in result.output.corpus.documents:
        assert document.doc_id in result.documents, "doc_id absent des documents traités"
        info = result.documents[document.doc_id]["info"]
        assert document.full_text.downloaded == bool(info.get("downloaded"))
        assert document.full_text.available == bool(info.get("available"))
    ids = [document.doc_id for document in result.output.corpus.documents]
    assert len(ids) == len(set(ids))


def test_persistance_des_checkpoints(settings, request_factory):
    saved: dict = {}

    def persist(name, payload):
        saved[name] = payload

    campaign.run(request_factory(), settings, SmartStubLLM(),
                 fetcher=FakeApiFetcher(DEFAULT_RESPONSES), downloader=FakeDownloader(),
                 persist=persist)

    for expected in ("keywords", "corpus", "documents", "analysis", "synthesis", "diagnosis"):
        assert expected in saved, f"checkpoint manquant : {expected}"
