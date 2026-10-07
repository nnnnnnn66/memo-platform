"""Gap check déterministe : sources réelles, hôtes en liste blanche, échecs déclarés."""

import pytest
from problematique_helpers import CROSSREF_OK, OPENALEX_OK, FakeFetcher

from problematization_agent.core.errors import ErrorState, PipelineError
from problematization_agent.pipeline import gap_check_stage
from problematization_agent.schemas.gap import Gap, GapCheckResult, GapType
from problematization_agent.sources.http import ApiFetcher

OPENALEX_ENDPOINT = "https://api.openalex.org/works"
CROSSREF_ENDPOINT = "https://api.crossref.org/works"


def _gap():
    return Gap(type=GapType.contextuelle,
               description="aucune étude n'a mesuré le télétravail dans les PME d'Abidjan")


def test_gap_deja_comble_detecte(settings, request_factory):
    fetcher = FakeFetcher({OPENALEX_ENDPOINT: OPENALEX_OK, CROSSREF_ENDPOINT: CROSSREF_OK})
    check = gap_check_stage.run(request_factory(), _gap(), settings, fetcher=fetcher)
    assert check.result == GapCheckResult.already_addressed
    assert check.publications
    assert "openalex" in check.providers_used


def test_gap_non_trouve(settings, request_factory):
    fetcher = FakeFetcher({OPENALEX_ENDPOINT: {"results": [
        {"display_name": "Élevage bovin au Sahel", "publication_date": "2019-01-01"}]},
        CROSSREF_ENDPOINT: CROSSREF_OK})
    check = gap_check_stage.run(request_factory(), _gap(), settings, fetcher=fetcher)
    assert check.result == GapCheckResult.not_found
    assert "ne prouve pas" in check.note


def test_echec_reseau_declare_unavailable(settings, request_factory):
    """Un échec persistant n'est JAMAIS interprété comme « gap confirmé »."""
    fetcher = FakeFetcher({}, raise_for={OPENALEX_ENDPOINT, CROSSREF_ENDPOINT})
    check = gap_check_stage.run(request_factory(), _gap(), settings, fetcher=fetcher)
    assert check.result == GapCheckResult.unavailable
    assert check.providers_failed
    assert "ne peut pas être vérifié" in check.note


def test_hosts_hors_liste_blanche_refuses():
    fetcher = ApiFetcher({}, _Limits(), {"api.openalex.org"})
    with pytest.raises(PipelineError) as exc:
        fetcher.fetch("https://exemple-malveillant.test/api")
    assert exc.value.state == ErrorState.SECURITY_VIOLATION
    with pytest.raises(PipelineError) as exc2:
        fetcher.fetch("http://api.openalex.org/works")
    assert exc2.value.state == ErrorState.SECURITY_VIOLATION


def test_requetes_derivees_du_sujet_et_du_gap(settings, request_factory):
    queries = gap_check_stage.build_queries(request_factory(), _gap(), 4)
    assert queries
    assert all(len(q) < 300 for q in queries)


class _Limits:
    max_external_requests = 5
    source_timeout = 5
