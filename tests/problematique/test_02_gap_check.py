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
    # La 1re requête est en mots-clés joints par OR : sans cela, les fournisseurs à ET
    # (HAL, theses.fr, OpenAIRE, DataCite, DOAJ, Europe PMC) ne renvoient RIEN.
    assert " OR " in queries[0]


# --- robustesse : la défaillance d'un fournisseur n'empêche pas la vérification -----------------

HAL_ENDPOINT = "https://api.archives-ouvertes.fr/search/"
HAL_TITLE = "Télétravail et productivité des développeurs d'Abidjan : mesure locale"


def test_openalex_en_echec_le_gap_reste_verifiable(settings, request_factory):
    """429 OpenAlex (quota IP partagé) : les autres fournisseurs gratuits prennent le relais."""
    fetcher = FakeFetcher(
        {
            HAL_ENDPOINT: {"response": {"docs": [{"title_s": [HAL_TITLE],
                                                  "authFullName_s": ["A. Traoré"],
                                                  "producedDate_s": "2024-05-01"}]}},
            CROSSREF_ENDPOINT: CROSSREF_OK,
        },
        raise_for={OPENALEX_ENDPOINT},
    )
    check = gap_check_stage.run(request_factory(), _gap(), settings, fetcher=fetcher)
    assert check.result == GapCheckResult.already_addressed
    assert any(p.provider == "hal" for p in check.publications)
    assert "hal" in check.providers_used
    # L'échec d'OpenAlex reste DÉCLARÉ, jamais interprété comme « gap confirmé ».
    assert any(f["provider"] == "openalex" for f in check.providers_failed)


def test_registre_fournisseurs_gratuits_et_liste_blanche():
    """Les fournisseurs gratuits sans clé sont déclarés en configuration, et leurs hôtes seuls."""
    from problematization_agent.sources.registry import Registry

    registry = Registry(settings_providers_file())
    ids = {p.id for p in registry.enabled()}
    assert {"openalex", "crossref", "hal", "theses_fr", "openaire",
            "datacite", "doaj", "europepmc"} <= ids
    hosts = registry.allowed_hosts()
    assert {"api.openalex.org", "api.crossref.org", "api.archives-ouvertes.fr",
            "theses.fr", "api.openaire.eu", "api.datacite.org", "doaj.org",
            "www.ebi.ac.uk"} <= hosts
    for provider in registry.enabled():
        adapter = registry.adapter_module(provider)  # l'adaptateur doit exister et s'importer
        assert adapter.PROVIDER_ID == provider.id


def settings_providers_file():
    from problematization_agent.core.config import Settings

    return Settings().providers_file


class _CapturingFetcher:
    """Fetcher qui enregistre les paramètres et en-têtes envoyés (aucun réseau)."""

    def __init__(self):
        self.cfg = {}
        self.calls: list[tuple[str, dict]] = []
        self.headers: list[dict] = []

    def fetch_json(self, url: str, params: dict | None = None, cost: int = 1,
                   headers: dict | None = None) -> dict:
        self.calls.append((url, dict(params or {})))
        self.headers.append(dict(headers or {}))
        return {"results": []}


def test_cle_openalex_envoyee_si_configuree(monkeypatch):
    """La clé OpenAlex (si présente dans l'environnement) lève le quota IP partagé.

    Elle part en EN-TÊTE `Authorization`, jamais dans l'URL : une URL est journalisée et recopiée
    dans les erreurs, un en-tête non. Sans clé : requête anonyme, comportement inchangé.
    """
    from problematization_agent.sources.adapters import openalex as adapter

    fetcher = _CapturingFetcher()
    monkeypatch.setenv("OPENALEX_API_KEY", "cle-de-test")
    adapter.search(fetcher, "teletravail OR productivite", 5)
    assert fetcher.headers[-1].get("Authorization") == "Bearer cle-de-test"
    assert "api_key" not in fetcher.calls[-1][1]
    assert "cle-de-test" not in fetcher.calls[-1][0]  # jamais dans l'URL

    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    adapter.search(fetcher, "teletravail", 5)
    assert "Authorization" not in fetcher.headers[-1]


class _Limits:
    max_external_requests = 5
    source_timeout = 5
