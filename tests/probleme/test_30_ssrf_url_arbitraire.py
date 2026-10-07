"""Test 30 — anti-SSRF : aucune URL arbitraire, seuls les hôtes déclarés."""

import pytest

from research_problem_agent.core.errors import ErrorState, PipelineError
from research_problem_agent.sources.http import Fetcher
from research_problem_agent.sources.registry import Registry


def _fetcher(settings):
    registry = Registry(settings.providers_file)
    return Fetcher(settings.sources, settings.limits, registry.allowed_hosts())


@pytest.mark.parametrize("url", [
    "https://exfiltrate.example.com/?data=1",
    "https://169.254.169.254/latest/meta-data/",          # métadonnées de cloud
    "https://localhost:8000/admin",
])
def test_hote_non_declare_refuse(settings, url):
    fetcher = _fetcher(settings)

    with pytest.raises(PipelineError) as exc:
        fetcher.fetch(url)

    assert exc.value.state == ErrorState.SECURITY_VIOLATION
    assert fetcher.requests == 0


def test_http_non_chiffre_refuse(settings):
    fetcher = _fetcher(settings)

    with pytest.raises(PipelineError) as exc:
        fetcher.fetch("http://api.openalex.org/works")

    assert exc.value.state == ErrorState.SECURITY_VIOLATION


def test_hotes_actifs_uniquement_dans_la_liste(settings):
    registry = Registry(settings.providers_file)
    hosts = registry.allowed_hosts()

    assert "api.openalex.org" in hosts
    # Un fournisseur désactivé n'ouvre pas d'accès réseau.
    assert "api.worldbank.org" not in hosts
    disabled = [p for p in registry.providers if not p.enabled]
    assert {p.id for p in disabled} >= {"eurostat", "worldbank", "scielo"}
    assert all(p.note for p in disabled), "chaque fournisseur désactivé doit être justifié"
